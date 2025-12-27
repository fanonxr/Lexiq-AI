package telephony

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"github.com/lexiqai/voice-gateway/internal/audio"
	"github.com/lexiqai/voice-gateway/internal/config"
	"github.com/lexiqai/voice-gateway/internal/observability"
	"github.com/lexiqai/voice-gateway/internal/orchestrator"
	"github.com/lexiqai/voice-gateway/internal/stt"
	"github.com/lexiqai/voice-gateway/internal/tts"
	"github.com/rs/zerolog"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		// In production, validate origin against Twilio's IP ranges
		// For now, allow all origins (development only)
		return true
	},
	ReadBufferSize:  4096,
	WriteBufferSize: 4096,
}

// TwilioMessage represents a message from Twilio Media Streams
type TwilioMessage struct {
	Event      string       `json:"event"`
	StreamSid  string       `json:"streamSid,omitempty"`
	AccountSid string       `json:"accountSid,omitempty"`
	CallSid    string       `json:"callSid,omitempty"`
	Tracks     []string     `json:"tracks,omitempty"`
	Media      *TwilioMedia `json:"media,omitempty"`
	Start      *TwilioStart `json:"start,omitempty"`
	Stop       *TwilioStop  `json:"stop,omitempty"`
}

// TwilioMedia represents the media payload in a media event
type TwilioMedia struct {
	Track     string `json:"track"`
	Chunk     string `json:"chunk"` // Base64 encoded audio
	Timestamp string `json:"timestamp"`
	Payload   string `json:"payload"` // Alternative field name for chunk
}

// TwilioStart represents the start event payload
type TwilioStart struct {
	AccountSid       string                 `json:"accountSid"`
	CallSid          string                 `json:"callSid"`
	Tracks           []string               `json:"tracks"`
	StreamSid        string                 `json:"streamSid"`
	CustomParameters map[string]interface{} `json:"customParameters,omitempty"`
}

// TwilioStop represents the stop event payload
type TwilioStop struct {
	AccountSid string `json:"accountSid"`
	CallSid    string `json:"callSid"`
	StreamSid  string `json:"streamSid"`
}

// CallSession holds the state of a single phone call
type CallSession struct {
	// Connection
	conn *websocket.Conn

	// Session identifiers
	callSid    string
	streamSid  string
	accountSid string

	// State management
	mu             sync.RWMutex
	isActive       bool
	isTalking      bool
	conversationID string

	// Firm and user identification (from Twilio custom parameters)
	firmID string
	userID string
	callID string // Internal call ID from database

	// Audio channels
	audioIn  chan []byte // Audio from Twilio (decoded PCMU)
	audioOut chan []byte // Audio to Twilio (for TTS playback)

	// Audio buffers
	audioInBuffer  *audio.RingBuffer // Ring buffer for incoming audio
	audioOutBuffer *audio.RingBuffer // Ring buffer for outgoing audio

	// Voice Activity Detection
	vadDetector *audio.VADDetector

	// STT client for speech-to-text transcription
	sttClient stt.STTClient

	// Orchestrator client for AI processing
	orchestratorClient *orchestrator.OrchestratorClient

	// TTS client for text-to-speech synthesis
	ttsClient tts.TTSClient

	// Transcription channel for complete sentences ready for Orchestrator
	transcriptionQueue chan string

	// Orchestrator response channel for text ready for TTS
	orchestratorResponseQueue chan string

	// Configuration
	config *config.Config

	// Observability
	correlationID string
	metrics       *observability.Metrics
	logger        zerolog.Logger

	// Control channels
	done    chan struct{}
	errChan chan error
}

// NewCallSession creates a new call session
func NewCallSession(conn *websocket.Conn, cfg *config.Config) *CallSession {
	// Create Deepgram STT client
	sttClient := stt.NewDeepgramClient(cfg)

	// Create Orchestrator client
	orchClient, err := orchestrator.NewOrchestratorClient(cfg)
	if err != nil {
		log.Printf("Warning: Failed to create Orchestrator client: %v", err)
		// Continue without Orchestrator - will retry later
		orchClient = nil
	}

	// Create Cartesia TTS client
	ttsClient := tts.NewCartesiaClient(cfg)

	// Create VAD detector
	vadConfig := &audio.VADConfig{
		EnergyThreshold: cfg.VADEnergyThreshold,
		SilenceFrames:   cfg.VADSilenceFrames,
		FrameSize:       160, // 20ms at 8kHz
	}
	vadDetector := audio.NewVADDetector(vadConfig)

	// Generate correlation ID for this call
	correlationID := observability.NewCorrelationID()
	callID := generateConversationID()
	
	// Create logger with correlation ID
	logger := observability.WithCorrelationID(correlationID).
		With().
		Str("call_id", callID).
		Logger()

	// Create metrics tracker
	metrics := observability.NewCallMetrics(callID)
	metrics.RecordCallStart()

	return &CallSession{
		conn:              conn,
		audioIn:           make(chan []byte, 100), // Buffered channel for audio chunks
		audioOut:          make(chan []byte, 100), // Buffered channel for TTS audio
		audioInBuffer:     audio.NewRingBuffer(cfg.AudioBufferSize),
		audioOutBuffer:    audio.NewRingBuffer(cfg.AudioBufferSize),
		vadDetector:       vadDetector,
		sttClient:         sttClient,
		orchestratorClient: orchClient,
		ttsClient:          ttsClient,
		transcriptionQueue: make(chan string, 50), // Buffered channel for complete transcriptions
		orchestratorResponseQueue: make(chan string, 50), // Buffered channel for Orchestrator responses
		config:            cfg,
		correlationID:     correlationID,
		metrics:           metrics,
		logger:            logger,
		done:              make(chan struct{}),
		errChan:           make(chan error, 1),
		isActive:          true,
		conversationID:    callID,
	}
}

// HandleTwilioWS is the main entry point for Twilio WebSocket connections
func HandleTwilioWS(cfg *config.Config) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// Upgrade HTTP connection to WebSocket
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("Failed to upgrade connection to WebSocket: %v", err)
			http.Error(w, "Failed to upgrade to WebSocket", http.StatusBadRequest)
			return
		}
		defer conn.Close()

		// Create new call session
		session := NewCallSession(conn, cfg)
		log.Printf("New Twilio WebSocket connection established")

		// Start processing goroutines
		go session.processIncomingMessages()
		go session.processIncomingAudio()
		go session.processOutgoingAudio()
		go session.processOrchestratorRequests()
		go session.processOrchestratorResponses()

		// Wait for session to complete or error
		select {
		case <-session.done:
			log.Printf("Call session ended: %s", session.callSid)
		case err := <-session.errChan:
			log.Printf("Call session error: %v", err)
		}
	}
}

// processIncomingMessages handles all incoming WebSocket messages from Twilio
func (s *CallSession) processIncomingMessages() {
	defer func() {
		// Cleanup STT client when session ends
		if s.sttClient != nil {
			if err := s.sttClient.Close(); err != nil {
				log.Printf("Error closing STT client: %v", err)
			}
		}
		// Cleanup Orchestrator client when session ends
		if s.orchestratorClient != nil {
			if err := s.orchestratorClient.Close(); err != nil {
				log.Printf("Error closing Orchestrator client: %v", err)
			}
		}
		close(s.done)
	}()

	for {
		// Check if session is still active
		s.mu.RLock()
		active := s.isActive
		s.mu.RUnlock()

		if !active {
			return
		}

		// Read message from WebSocket
		_, message, err := s.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				s.logger.Warn().Err(err).Msg("WebSocket read error")
			}
			s.mu.Lock()
			s.isActive = false
			s.mu.Unlock()
			return
		}

		// Parse Twilio message
		var twilioMsg TwilioMessage
		if err := json.Unmarshal(message, &twilioMsg); err != nil {
			s.logger.Error().Err(err).Msg("Failed to parse Twilio message")
			continue
		}

		// Handle different event types
		switch twilioMsg.Event {
		case "connected":
			s.logger.Info().
				Str("stream_sid", twilioMsg.StreamSid).
				Msg("Twilio stream connected")
			s.mu.Lock()
			s.streamSid = twilioMsg.StreamSid
			s.mu.Unlock()

		case "start":
			s.logger.Info().
				Str("call_sid", twilioMsg.CallSid).
				Str("stream_sid", twilioMsg.StreamSid).
				Msg("Call started")
			s.mu.Lock()
			s.callSid = twilioMsg.CallSid
			s.streamSid = twilioMsg.StreamSid
			if twilioMsg.Start != nil {
				s.accountSid = twilioMsg.Start.AccountSid

				// Extract custom parameters
				if params := twilioMsg.Start.CustomParameters; params != nil {
					if firmID, ok := params["firm_id"].(string); ok {
						s.firmID = firmID
					}
					if userID, ok := params["user_id"].(string); ok {
						s.userID = userID
					}
					if callID, ok := params["call_id"].(string); ok {
						s.callID = callID
					}
				}
			}

			// Validate we have required IDs (while holding lock)
			firmID := s.firmID
			userID := s.userID
			callID := s.callID
			s.mu.Unlock()

			if firmID == "" || userID == "" {
				log.Printf("Warning: Missing firm_id or user_id for call %s", twilioMsg.CallSid)
				// Could close connection or use default firm
				// For now, we'll log a warning and continue
			}

			log.Printf("Call context: firm_id=%s, user_id=%s, call_id=%s", firmID, userID, callID)
			
			// Initialize Deepgram streaming connection
			if err := s.sttClient.Start(); err != nil {
				log.Printf("Error starting Deepgram client: %v", err)
				// Continue anyway - we can retry later
			} else {
				log.Printf("Deepgram streaming connection initialized for call %s", twilioMsg.CallSid)
				
				// Start goroutine to process transcriptions
				go s.processTranscriptions()
			}

		case "media":
			// Handle audio media event
			if twilioMsg.Media != nil {
				s.handleMediaEvent(twilioMsg.Media)
			}

		case "stop":
			s.logger.Info().
				Str("call_sid", twilioMsg.CallSid).
				Msg("Call stopped")
			s.mu.Lock()
			s.isActive = false
			s.mu.Unlock()
			
			// Stop Deepgram streaming connection
			if err := s.sttClient.Stop(); err != nil {
				log.Printf("Error stopping Deepgram client: %v", err)
			} else {
				log.Printf("Deepgram streaming connection closed for call %s", twilioMsg.CallSid)
			}
			return

		default:
			log.Printf("Unknown Twilio event: %s", twilioMsg.Event)
		}
	}
}

// handleMediaEvent processes a media event from Twilio
func (s *CallSession) handleMediaEvent(media *TwilioMedia) {
	// Extract base64 encoded audio chunk
	var base64Chunk string
	if media.Chunk != "" {
		base64Chunk = media.Chunk
	} else if media.Payload != "" {
		base64Chunk = media.Payload
	} else {
		log.Printf("Media event missing chunk/payload")
		return
	}

	// Decode base64 to binary
	audioData, err := base64.StdEncoding.DecodeString(base64Chunk)
	if err != nil {
		log.Printf("Failed to decode base64 audio: %v", err)
		return
	}

	// Send decoded audio to processing channel
	select {
	case s.audioIn <- audioData:
		// Successfully queued
	default:
		// Channel is full, log warning but don't block
		log.Printf("Warning: audioIn channel full, dropping audio chunk")
	}
}

// processIncomingAudio processes audio chunks from Twilio and sends them to Deepgram
func (s *CallSession) processIncomingAudio() {
	log.Printf("Starting audio processing goroutine for call %s", s.callSid)

	for {
		select {
		case audioChunk := <-s.audioIn:
			// Record audio bytes
			if s.metrics != nil {
				s.metrics.RecordAudioBytes("in", int64(len(audioChunk)))
			}

			// Check if user is speaking (interrupt TTS if active)
			s.mu.Lock()
			if s.isTalking {
				// User is speaking - stop any active TTS
				if s.ttsClient != nil && s.ttsClient.IsActive() {
					s.logger.Info().Msg("User speaking detected, stopping TTS")
					if err := s.ttsClient.Stop(); err != nil {
						s.logger.Error().Err(err).Msg("Error stopping TTS")
					}
				}
			}
			s.mu.Unlock()

			// Record STT start on first audio chunk
			if s.metrics != nil && !s.isTalking {
				s.metrics.RecordSTTStart()
			}

			// Send audio chunk to Deepgram streaming API
			if err := s.sttClient.SendAudio(audioChunk); err != nil {
				s.logger.Error().Err(err).Msg("Error sending audio to Deepgram")
				if s.metrics != nil {
					s.metrics.RecordError("stt_send_error", "deepgram")
				}
				// Continue processing - don't break the call flow
				// The STT client should handle reconnection internally
			}

		case <-s.done:
			log.Printf("Audio processing goroutine stopping for call %s", s.callSid)
			return
		}
	}
}

// processTranscriptions processes transcription results from Deepgram
// and queues complete sentences for the Orchestrator
func (s *CallSession) processTranscriptions() {
	log.Printf("Starting transcription processing goroutine for call %s", s.callSid)

	transcriptChan := s.sttClient.GetTranscription()
	
	// Buffer for accumulating interim results
	var currentSentence strings.Builder
	var lastFinalText string

	for {
		select {
		case result := <-transcriptChan:
			if result == nil {
				// Channel closed
				log.Printf("Transcription channel closed for call %s", s.callSid)
				return
			}

			if result.IsFinal {
				// Final transcription - queue for Orchestrator
				finalText := result.Text
				
				// Only queue if it's different from the last final text
				// (Deepgram may send duplicates)
				if finalText != "" && finalText != lastFinalText {
					log.Printf("Final transcription ready for Orchestrator: %s", finalText)
					
					// Stop TTS if user is speaking (interrupt handling)
					s.mu.Lock()
					if s.ttsClient != nil && s.ttsClient.IsActive() {
						log.Printf("User speech detected, interrupting TTS")
						if err := s.ttsClient.Stop(); err != nil {
							log.Printf("Error stopping TTS: %v", err)
						}
					}
					s.mu.Unlock()
					
					// Queue for Orchestrator
					select {
					case s.transcriptionQueue <- finalText:
						// Successfully queued
						lastFinalText = finalText
					default:
						log.Printf("Warning: transcription queue full, dropping: %s", finalText)
					}
					
					// Clear current sentence buffer
					currentSentence.Reset()
				}
			} else {
				// Interim result - update current sentence
				// For now, we just log it. In a full implementation,
				// we might want to show interim results in a UI
				if result.Text != "" {
					currentSentence.Reset()
					currentSentence.WriteString(result.Text)
					log.Printf("Interim transcription: %s", result.Text)
				}
			}

		case <-s.done:
			s.logger.Debug().Msg("Transcription processing goroutine stopping")
			return
		}
	}
}

// processOrchestratorRequests processes transcriptions from the queue and sends them to Orchestrator
func (s *CallSession) processOrchestratorRequests() {
	log.Printf("Starting Orchestrator request processing goroutine for call %s", s.callSid)

	for {
		select {
		case transcription := <-s.transcriptionQueue:
			if s.orchestratorClient == nil {
				s.logger.Warn().
					Str("transcription", transcription).
					Msg("Orchestrator client not available, skipping")
				continue
			}

			// Get conversation context
			s.mu.RLock()
			conversationID := s.conversationID
			userID := s.userID
			firmID := s.firmID
			s.mu.RUnlock()

			// Create context for this request
			ctx := context.Background()

			// Send transcription to Orchestrator
			s.logger.Info().
				Str("text", transcription).
				Str("conversation_id", conversationID).
				Msg("Sending transcription to Orchestrator")
			
			// Record Orchestrator start
			if s.metrics != nil {
				s.metrics.RecordOrchestratorStart()
			}
			
			responseChan, err := s.orchestratorClient.ProcessTextStream(ctx, conversationID, transcription, userID, firmID)
			if err != nil {
				s.logger.Error().Err(err).Msg("Error sending transcription to Orchestrator")
				if s.metrics != nil {
					s.metrics.RecordOrchestratorEnd(false)
					s.metrics.RecordError("orchestrator_send_error", "orchestrator")
				}
				continue
			}

			// Process responses in a separate goroutine to avoid blocking
			go func() {
				for response := range responseChan {
					if response.Error != nil {
						s.logger.Error().
							Str("code", response.Error.Code).
							Str("message", response.Error.Message).
							Msg("Orchestrator error")
						if s.metrics != nil {
							s.metrics.RecordError("orchestrator_error", "orchestrator")
						}
						continue
					}

					// Queue text chunks for TTS
					if response.TextChunk != "" {
						select {
						case s.orchestratorResponseQueue <- response.TextChunk:
							s.logger.Debug().
								Str("chunk", response.TextChunk).
								Msg("Queued Orchestrator response for TTS")
						default:
							s.logger.Warn().
								Str("chunk", response.TextChunk).
								Msg("Orchestrator response queue full, dropping")
						}
					}

					// Log tool calls and results for observability
					if response.ToolCall != nil {
						s.logger.Info().
							Str("tool_name", response.ToolCall.ToolName).
							Str("call_id", response.ToolCall.CallID).
							Msg("Orchestrator tool call")
					}
					if response.ToolResult != nil {
						s.logger.Info().
							Str("call_id", response.ToolResult.CallID).
							Bool("success", response.ToolResult.Success).
							Msg("Orchestrator tool result")
					}

					if response.IsDone {
						s.logger.Info().
							Str("conversation_id", conversationID).
							Msg("Orchestrator response stream completed")
						if s.metrics != nil {
							s.metrics.RecordOrchestratorEnd(true)
						}
						break
					}
				}
			}()

		case <-s.done:
			s.logger.Debug().Msg("Orchestrator request processing goroutine stopping")
			return
		}
	}
}

// processOrchestratorResponses processes responses from Orchestrator and sends them to TTS
func (s *CallSession) processOrchestratorResponses() {
	s.logger.Debug().Msg("Starting Orchestrator response processing goroutine")

	// Buffer for accumulating text chunks until we have a complete sentence or pause
	var textBuffer strings.Builder
	var lastChunkTime time.Time
	sentenceTimeout := 500 * time.Millisecond // Wait 500ms for more chunks before synthesizing

	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case textChunk := <-s.orchestratorResponseQueue:
			// Accumulate text chunks
			textBuffer.WriteString(textChunk)
			lastChunkTime = time.Now()
			log.Printf("Accumulated Orchestrator response: %s", textBuffer.String())

		case <-ticker.C:
			// Check if we should synthesize (timeout or buffer size)
			if textBuffer.Len() > 0 && time.Since(lastChunkTime) > sentenceTimeout {
				textToSynthesize := textBuffer.String()
				textBuffer.Reset()

				// Send to TTS
				if s.ttsClient != nil {
					s.logger.Info().
						Str("text", textToSynthesize).
						Msg("Sending text to TTS")
					
					// Record TTS start
					if s.metrics != nil {
						s.metrics.RecordTTSStart()
					}
					
					audioChan, err := s.ttsClient.Synthesize(textToSynthesize)
					if err != nil {
						s.logger.Error().Err(err).Msg("Error synthesizing text with TTS")
						if s.metrics != nil {
							s.metrics.RecordTTSEnd(false)
						}
						continue
					}

					// Stream audio chunks to Twilio
					go func() {
						for audioChunk := range audioChan {
							// Send audio to Twilio via audioOut channel
							select {
							case s.audioOut <- audioChunk.Data:
								// Successfully queued
							default:
								log.Printf("Warning: audioOut channel full, dropping TTS audio")
							}
						}
					}()
				}
			}

		case <-s.done:
			// Synthesize any remaining text before stopping
			if textBuffer.Len() > 0 && s.ttsClient != nil {
				textToSynthesize := textBuffer.String()
				log.Printf("Synthesizing final text before stopping: %s", textToSynthesize)
				audioChan, err := s.ttsClient.Synthesize(textToSynthesize)
				if err == nil {
					go func() {
						for audioChunk := range audioChan {
							select {
							case s.audioOut <- audioChunk.Data:
							default:
							}
						}
					}()
				}
			}
			log.Printf("Orchestrator response processing goroutine stopping for call %s", s.callSid)
			return
		}
	}
}

// processOutgoingAudio handles audio playback to Twilio (TTS output)
func (s *CallSession) processOutgoingAudio() {
	log.Printf("Starting outgoing audio processing goroutine for call %s", s.callSid)

	for {
		select {
		case audioChunk := <-s.audioOut:
			// Write to ring buffer for smooth playback
			written := s.audioOutBuffer.Write(audioChunk)
			if written < len(audioChunk) {
				log.Printf("Warning: audioOut buffer overflow, dropped %d bytes", len(audioChunk)-written)
			}

			// Read from buffer and send to Twilio (helps with smooth playback)
			bufferData := make([]byte, len(audioChunk))
			read := s.audioOutBuffer.Read(bufferData)
			if read > 0 {
				// Send audio to Twilio via WebSocket
				// Audio is already in PCMU format and ready to send
				if err := s.SendAudioToTwilio(bufferData[:read]); err != nil {
					s.logger.Error().Err(err).Msg("Error sending audio to Twilio")
					if s.metrics != nil {
						s.metrics.RecordError("twilio_send_error", "telephony")
					}
					// Continue processing - don't break the call flow
				} else {
					s.logger.Debug().
						Int("bytes", read).
						Msg("Sent TTS audio to Twilio")
				}
			}

		case <-s.done:
			log.Printf("Outgoing audio processing goroutine stopping for call %s", s.callSid)
			return
		}
	}
}

// SendAudioToTwilio sends audio data to Twilio in the correct format
func (s *CallSession) SendAudioToTwilio(audioData []byte) error {
	s.mu.RLock()
	streamSid := s.streamSid
	active := s.isActive
	s.mu.RUnlock()

	if !active {
		return fmt.Errorf("session is not active")
	}

	// Encode audio to base64
	base64Audio := base64.StdEncoding.EncodeToString(audioData)

	// Format as Twilio media message
	mediaMsg := map[string]interface{}{
		"event":     "media",
		"streamSid": streamSid,
		"media": map[string]interface{}{
			"payload": base64Audio,
		},
	}

	// Send via WebSocket
	return s.conn.WriteJSON(mediaMsg)
}

// GetCallSid returns the call SID
func (s *CallSession) GetCallSid() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.callSid
}

// GetConversationID returns the conversation ID
func (s *CallSession) GetConversationID() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.conversationID
}

// GetFirmID returns the firm ID
func (s *CallSession) GetFirmID() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.firmID
}

// GetUserID returns the user ID
func (s *CallSession) GetUserID() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.userID
}

// GetCallID returns the internal call ID
func (s *CallSession) GetCallID() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.callID
}

// IsActive returns whether the session is still active
func (s *CallSession) IsActive() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.isActive
}

// generateConversationID generates a unique conversation ID
func generateConversationID() string {
	return fmt.Sprintf("conv-%s", uuid.New().String())
}
