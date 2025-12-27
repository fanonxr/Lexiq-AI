package tts

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"

	"github.com/lexiqai/voice-gateway/internal/audio"
	"github.com/lexiqai/voice-gateway/internal/config"
)

// CartesiaClient implements TTSClient using Cartesia's TTS API
type CartesiaClient struct {
	config     *config.Config
	apiKey     string
	apiURL     string
	voiceID    string
	httpClient *http.Client
	mu         sync.RWMutex
	isActive   bool
}

// CartesiaRequest represents the request payload for Cartesia TTS API
type CartesiaRequest struct {
	Text            string  `json:"text"`
	VoiceID         string  `json:"voice_id"`
	ModelID         string  `json:"model_id,omitempty"`
	OutputFormat    string  `json:"output_format,omitempty"`
	SampleRate      int     `json:"sample_rate,omitempty"`
	Speed           float64 `json:"speed,omitempty"`
	Stability       float64 `json:"stability,omitempty"`
	SimilarityBoost float64 `json:"similarity_boost,omitempty"`
}

// NewCartesiaClient creates a new Cartesia TTS client
func NewCartesiaClient(cfg *config.Config) *CartesiaClient {
	return &CartesiaClient{
		config:     cfg,
		apiKey:     cfg.CartesiaAPIKey,
		apiURL:     "https://api.cartesia.ai/v1/tts", // Cartesia TTS API endpoint
		voiceID:    cfg.CartesiaVoiceID,              // Voice ID from config
		httpClient: &http.Client{},
		isActive:   false,
	}
}

// Synthesize converts text to audio and streams it
func (c *CartesiaClient) Synthesize(text string) (<-chan *AudioChunk, error) {
	c.mu.Lock()
	if c.isActive {
		c.mu.Unlock()
		return nil, fmt.Errorf("cartesia client is already synthesizing")
	}
	c.isActive = true
	c.mu.Unlock()

	// Create request payload
	reqBody := CartesiaRequest{
		Text:            text,
		VoiceID:         c.voiceID,
		ModelID:         c.config.CartesiaModelID, // Model ID from config (default: sonic)
		OutputFormat:    "pcm",                    // PCM format for easier conversion
		SampleRate:      24000,                    // Cartesia typically outputs at 24kHz
		Speed:           1.0,
		Stability:       0.5,
		SimilarityBoost: 0.75,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		c.mu.Lock()
		c.isActive = false
		c.mu.Unlock()
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	// Create HTTP request
	req, err := http.NewRequest("POST", c.apiURL, bytes.NewBuffer(jsonData))
	if err != nil {
		c.mu.Lock()
		c.isActive = false
		c.mu.Unlock()
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set headers
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-api-key", c.apiKey)

	// Make request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		c.mu.Lock()
		c.isActive = false
		c.mu.Unlock()
		return nil, fmt.Errorf("failed to make request: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		c.mu.Lock()
		c.isActive = false
		c.mu.Unlock()
		return nil, fmt.Errorf("cartesia API returned status %d", resp.StatusCode)
	}

	// Create channel for audio chunks
	audioChan := make(chan *AudioChunk, 10)

	// Read audio data in a goroutine
	go func() {
		defer func() {
			resp.Body.Close()
			close(audioChan)
			c.mu.Lock()
			c.isActive = false
			c.mu.Unlock()
		}()

		// Read audio data (PCM format from Cartesia)
		audioData, err := io.ReadAll(resp.Body)
		if err != nil {
			log.Printf("Error reading Cartesia audio response: %v", err)
			return
		}

		if len(audioData) == 0 {
			log.Printf("Warning: Cartesia returned empty audio data")
			return
		}

		// Convert PCM to PCMU (G.711 μ-law) for Twilio
		// Cartesia outputs PCM at 24kHz, we need PCMU at 8kHz
		pcmuData, err := audio.ConvertPCMToPCMU(audioData, 24000, 8000)
		if err != nil {
			log.Printf("Error converting audio format: %v", err)
			return
		}

		// Send audio chunk
		select {
		case audioChan <- &AudioChunk{
			Data:       pcmuData,
			SampleRate: 8000,
			Channels:   1,
		}:
			log.Printf("Sent %d bytes of TTS audio (converted from %d bytes PCM)", len(pcmuData), len(audioData))
		default:
			log.Printf("Warning: audio channel full, dropping audio chunk")
		}
	}()

	return audioChan, nil
}

// Stop stops any ongoing synthesis
func (c *CartesiaClient) Stop() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if !c.isActive {
		return nil
	}

	c.isActive = false
	log.Printf("Cartesia TTS synthesis stopped")
	return nil
}

// Close closes the client and cleans up resources
func (c *CartesiaClient) Close() error {
	return c.Stop()
}

// IsActive returns whether the client is currently synthesizing
func (c *CartesiaClient) IsActive() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.isActive
}
