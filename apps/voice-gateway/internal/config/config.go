package config

import (
	"fmt"
	"os"

	"github.com/joho/godotenv"
	"github.com/kelseyhightower/envconfig"
)

// Config holds all configuration for the voice gateway service
type Config struct {
	// Server configuration
	Port string `envconfig:"PORT" default:"8080"`

	// Public base URL for this service (e.g. https://xxx.ngrok-free.dev when behind ngrok).
	// Used for logging the WebSocket endpoint; Twilio connects to wss://<this-host>/streams/twilio.
	// Optional; if unset, logs ws://localhost:PORT/streams/twilio.
	VoiceGatewayURL string `envconfig:"VOICE_GATEWAY_URL" default:""`

	// Deepgram STT API configuration
	DeepgramAPIKey   string `envconfig:"DEEPGRAM_API_KEY" required:"true"`
	DeepgramModel    string `envconfig:"DEEPGRAM_MODEL" default:"nova-2"` // nova-2, enhanced, base
	DeepgramLanguage string `envconfig:"DEEPGRAM_LANGUAGE" default:"en"`  // Language code (en, es, fr, etc.)

	// Cartesia TTS API configuration
	CartesiaAPIKey  string `envconfig:"CARTESIA_API_KEY" required:"true"`
	CartesiaVoiceID string `envconfig:"CARTESIA_VOICE_ID" default:"sonic-english"` // Voice ID for Cartesia
	CartesiaModelID string `envconfig:"CARTESIA_MODEL_ID" default:"sonic"`         // Model ID (sonic, etc.)

	// Cognitive Orchestrator gRPC endpoint
	OrchestratorURL        string `envconfig:"ORCHESTRATOR_URL" default:"localhost:50051"`
	OrchestratorTLSEnabled bool   `envconfig:"ORCHESTRATOR_TLS_ENABLED" default:"false"`
	OrchestratorTimeout    int    `envconfig:"ORCHESTRATOR_TIMEOUT" default:"30"` // seconds

	// Audio processing configuration
	AudioBufferSize    int     `envconfig:"AUDIO_BUFFER_SIZE" default:"8192"`     // Ring buffer size in bytes
	VADEnergyThreshold float64 `envconfig:"VAD_ENERGY_THRESHOLD" default:"500.0"` // RMS energy threshold for VAD
	VADSilenceFrames   int     `envconfig:"VAD_SILENCE_FRAMES" default:"10"`      // Frames of silence to mark speech end

	// Resilience configuration
	CircuitBreakerMaxFailures  int `envconfig:"CIRCUIT_BREAKER_MAX_FAILURES" default:"5"`   // Failures before opening circuit
	CircuitBreakerResetTimeout int `envconfig:"CIRCUIT_BREAKER_RESET_TIMEOUT" default:"30"` // Seconds before attempting recovery
	RetryMaxAttempts           int `envconfig:"RETRY_MAX_ATTEMPTS" default:"3"`             // Maximum retry attempts
	RetryInitialBackoff        int `envconfig:"RETRY_INITIAL_BACKOFF" default:"100"`        // Initial backoff in milliseconds
	ReconnectMaxAttempts       int `envconfig:"RECONNECT_MAX_ATTEMPTS" default:"5"`         // Maximum reconnection attempts
	ReconnectBackoff           int `envconfig:"RECONNECT_BACKOFF" default:"1000"`           // Reconnection backoff in milliseconds

	// Observability configuration
	LogLevel       string `envconfig:"LOG_LEVEL" default:"info"`       // Log level: debug, info, warn, error
	LogPretty      bool   `envconfig:"LOG_PRETTY" default:"false"`     // Pretty print logs (for development)
	MetricsEnabled bool   `envconfig:"METRICS_ENABLED" default:"true"` // Enable Prometheus metrics
}

// Load reads configuration from environment variables
// It first attempts to load from .env file if it exists, then from environment
func Load() (*Config, error) {
	// Try to load .env file (ignore error if it doesn't exist)
	_ = godotenv.Load()

	var cfg Config
	if err := envconfig.Process("", &cfg); err != nil {
		return nil, fmt.Errorf("failed to load config: %w", err)
	}

	// Validate required fields
	if cfg.DeepgramAPIKey == "" {
		return nil, fmt.Errorf("DEEPGRAM_API_KEY is required")
	}
	if cfg.CartesiaAPIKey == "" {
		return nil, fmt.Errorf("CARTESIA_API_KEY is required")
	}

	return &cfg, nil
}

// LoadFromEnv loads configuration directly from environment variables
// without attempting to load .env file (useful for containerized deployments)
func LoadFromEnv() (*Config, error) {
	var cfg Config
	if err := envconfig.Process("", &cfg); err != nil {
		return nil, fmt.Errorf("failed to load config: %w", err)
	}

	// Validate required fields
	if cfg.DeepgramAPIKey == "" {
		return nil, fmt.Errorf("DEEPGRAM_API_KEY is required")
	}
	if cfg.CartesiaAPIKey == "" {
		return nil, fmt.Errorf("CARTESIA_API_KEY is required")
	}

	return &cfg, nil
}

// GetEnv returns the value of an environment variable or a default value
func GetEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
