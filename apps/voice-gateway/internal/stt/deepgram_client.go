package stt

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	websocketv1api "github.com/deepgram/deepgram-go-sdk/v3/pkg/api/listen/v1/websocket"
	msginterfaces "github.com/deepgram/deepgram-go-sdk/v3/pkg/api/listen/v1/websocket/interfaces"
	interfaces "github.com/deepgram/deepgram-go-sdk/v3/pkg/client/interfaces"
	listenClient "github.com/deepgram/deepgram-go-sdk/v3/pkg/client/listen"

	"github.com/lexiqai/voice-gateway/internal/config"
	"github.com/lexiqai/voice-gateway/internal/observability"
	"github.com/lexiqai/voice-gateway/internal/resilience"
)

// messageCallbackHandler implements the LiveMessageCallback interface
// It embeds the default handler and overrides only the methods we need to customize
type messageCallbackHandler struct {
	*websocketv1api.DefaultCallbackHandler // Embed default handler for methods we don't override
	handler                                func(*msginterfaces.MessageResponse)
	errorHandler                           func(*msginterfaces.ErrorResponse) error
}

// Message overrides the default handler to send transcriptions to our channel
func (m *messageCallbackHandler) Message(message *msginterfaces.MessageResponse) error {
	m.handler(message)
	return nil
}

// Error overrides the default handler to use our custom error handling
func (m *messageCallbackHandler) Error(errorResponse *msginterfaces.ErrorResponse) error {
	if m.errorHandler != nil {
		return m.errorHandler(errorResponse)
	}
	// Fall back to default handler behavior
	return m.DefaultCallbackHandler.Error(errorResponse)
}

// DeepgramClient implements STTClient using Deepgram's streaming API
type DeepgramClient struct {
	config         *config.Config
	client       *listenClient.WSCallback
	transcript   chan *TranscriptionResult
	mu           sync.RWMutex
	isActive     bool
	ctx          context.Context
	cancel       context.CancelFunc
	circuitBreaker *resilience.CircuitBreaker
}

// NewDeepgramClient creates a new Deepgram streaming client
func NewDeepgramClient(cfg *config.Config) *DeepgramClient {
	ctx, cancel := context.WithCancel(context.Background())
	
	// Create circuit breaker
	circuitBreaker := resilience.NewCircuitBreaker(
		"deepgram",
		cfg.CircuitBreakerMaxFailures,
		time.Duration(cfg.CircuitBreakerResetTimeout)*time.Second,
	)
	
	return &DeepgramClient{
		config:         cfg,
		transcript:     make(chan *TranscriptionResult, 100),
		ctx:            ctx,
		cancel:         cancel,
		isActive:       false,
		circuitBreaker: circuitBreaker,
	}
}

// Start begins a new Deepgram streaming transcription session
func (d *DeepgramClient) Start() error {
	d.mu.Lock()
	defer d.mu.Unlock()

	if d.isActive {
		return fmt.Errorf("deepgram client is already active")
	}

	// Create Deepgram transcription options (v3 API)
	tOptions := &interfaces.LiveTranscriptionOptions{
		Model:          d.config.DeepgramModel,
		Language:       d.config.DeepgramLanguage,
		Punctuate:      true,
		InterimResults: true,
		UtteranceEndMs: "1000",  // End utterance after 1 second of silence (string in v3)
		VadEvents:      true,    // Enable voice activity detection events
		Encoding:       "mulaw", // G.711 PCMU (μ-law)
		Channels:       1,       // Mono
		SampleRate:     8000,    // 8kHz (Twilio standard)
	}

	// Create callback struct that implements LiveMessageCallback interface
	// We embed the default handler and only override Message and Error methods
	callback := &messageCallbackHandler{
		DefaultCallbackHandler: websocketv1api.NewDefaultCallbackHandler(),
		handler:                d.handleDeepgramMessage,
		errorHandler: func(errorResponse *msginterfaces.ErrorResponse) error {
			log.Printf("Deepgram error: %+v", errorResponse)
			
			// Record failure in circuit breaker
			d.circuitBreaker.RecordResult(false)
			observability.UpdateCircuitBreakerState("deepgram", int(d.circuitBreaker.GetState()))
			observability.IncrementCircuitBreakerFailures("deepgram")
			
			// Try to reconnect if not cancelled
			select {
			case <-d.ctx.Done():
				return nil
			default:
				// Connection lost, mark as inactive
				d.mu.Lock()
				d.isActive = false
				d.mu.Unlock()
				
				// Attempt reconnection in background
				go d.attemptReconnect()
			}
			return nil
		},
	}

	// Create Deepgram WebSocket client using callback (v3 API)
	// Using nil for cOptions to use defaults
	client, err := listenClient.NewWSUsingCallback(
		d.ctx,
		d.config.DeepgramAPIKey,
		nil, // ClientOptions - nil uses defaults
		tOptions,
		callback,
	)

	if err != nil {
		return fmt.Errorf("failed to create Deepgram client: %w", err)
	}

	d.client = client
	d.isActive = true
	
	// Record success in circuit breaker
	d.circuitBreaker.RecordResult(true)
	observability.UpdateCircuitBreakerState("deepgram", int(d.circuitBreaker.GetState()))

	// Start the connection (WebSocket client starts automatically on creation)
	// No explicit Start() call needed for WSCallback

	log.Printf("Deepgram streaming client started (model: %s, language: %s)", d.config.DeepgramModel, d.config.DeepgramLanguage)
	return nil
}

// handleDeepgramMessage processes messages from Deepgram
func (d *DeepgramClient) handleDeepgramMessage(msg *msginterfaces.MessageResponse) {
	if msg == nil {
		return
	}

	// Handle different message types based on Type field (string)
	// MessageResponse is used for transcription results
	switch msg.Type {
	case "Metadata":
		// Metadata messages are handled separately, log for now
		log.Printf("Deepgram metadata: %+v", msg.Metadata)

	case "SpeechStarted":
		log.Printf("Deepgram: Speech started")

	case "UtteranceEnd":
		log.Printf("Deepgram: Utterance ended")

	case "Results", "Message":
		// Process transcription results
		// MessageResponse has Channel directly (not Results.Channels)
		if len(msg.Channel.Alternatives) == 0 {
			return
		}

		// Get the best alternative (first one)
		alt := msg.Channel.Alternatives[0]
		if alt.Transcript == "" {
			return
		}

		// Determine if this is a final result
		isFinal := msg.IsFinal

		// Extract confidence if available
		confidence := 0.0
		if alt.Confidence > 0 {
			confidence = alt.Confidence
		}

		// Extract timing information
		startTime := msg.Start
		duration := msg.Duration
		if len(alt.Words) > 0 && duration == 0 {
			// Fallback: calculate duration from words if not provided
			startTime = alt.Words[0].Start
			lastWord := alt.Words[len(alt.Words)-1]
			duration = lastWord.End - startTime
		}

		// Create transcription result
		result := &TranscriptionResult{
			Text:       alt.Transcript,
			IsFinal:    isFinal,
			Confidence: confidence,
			StartTime:  startTime,
			Duration:   duration,
		}

		// Send to transcript channel (non-blocking)
		select {
		case d.transcript <- result:
			if isFinal {
				log.Printf("Deepgram final transcription: %s (confidence: %.2f)", alt.Transcript, confidence)
			} else {
				log.Printf("Deepgram interim transcription: %s", alt.Transcript)
			}
		default:
			log.Printf("Warning: transcript channel full, dropping transcription")
		}

	default:
		log.Printf("Deepgram: Received unknown message type: %s", msg.Type)
	}
}

// SendAudio sends an audio chunk to Deepgram
func (d *DeepgramClient) SendAudio(audioData []byte) error {
	// Use circuit breaker to protect the call
	err := d.circuitBreaker.Call(func() error {
		d.mu.RLock()
		active := d.isActive
		client := d.client
		d.mu.RUnlock()

		if !active || client == nil {
			return fmt.Errorf("deepgram client is not active")
		}

		// Send audio data to Deepgram
		// WSCallback uses Write method for sending audio (returns bytes written and error)
		_, err := client.Write(audioData)
		if err != nil {
			// Attempt reconnection in background on error
			go d.attemptReconnect()
			return fmt.Errorf("failed to send audio to Deepgram: %w", err)
		}

		return nil
	})
	
	// Update circuit breaker metrics
	observability.UpdateCircuitBreakerState("deepgram", int(d.circuitBreaker.GetState()))
	if err != nil {
		observability.IncrementCircuitBreakerFailures("deepgram")
	}
	
	return err
}

// attemptReconnect attempts to reconnect to Deepgram
func (d *DeepgramClient) attemptReconnect() {
	// Check if already active or context cancelled
	select {
	case <-d.ctx.Done():
		return
	default:
	}

	d.mu.RLock()
	alreadyActive := d.isActive
	d.mu.RUnlock()

	if alreadyActive {
		return // Already reconnected
	}

	// Use reconnection logic
	reconnectConfig := &resilience.ReconnectConfig{
		MaxAttempts: d.config.ReconnectMaxAttempts,
		Backoff:     time.Duration(d.config.ReconnectBackoff) * time.Millisecond,
		Multiplier:  2.0,
		MaxBackoff:  30 * time.Second,
	}

	err := resilience.Reconnect(d.ctx, func() error {
		return d.Start()
	}, reconnectConfig)

	if err != nil {
		log.Printf("Failed to reconnect Deepgram client: %v", err)
	} else {
		log.Printf("Successfully reconnected Deepgram client")
	}
}

// GetTranscription returns a channel that receives transcription results
func (d *DeepgramClient) GetTranscription() <-chan *TranscriptionResult {
	return d.transcript
}

// Stop stops the Deepgram streaming session
func (d *DeepgramClient) Stop() error {
	d.mu.Lock()
	defer d.mu.Unlock()

	if !d.isActive {
		return nil // Already stopped
	}

	// Send finish message to Deepgram
	// WSCallback Finish() doesn't return an error
	d.client.Finish()

	d.isActive = false
	log.Printf("Deepgram streaming client stopped")
	return nil
}

// Close closes the client and cleans up resources
func (d *DeepgramClient) Close() error {
	d.cancel() // Cancel context to stop any reconnection attempts

	if err := d.Stop(); err != nil {
		return err
	}

	// Close transcript channel after a short delay to allow any pending reads
	go func() {
		time.Sleep(100 * time.Millisecond)
		close(d.transcript)
	}()

	return nil
}

// IsActive returns whether the client is currently active
func (d *DeepgramClient) IsActive() bool {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.isActive
}
