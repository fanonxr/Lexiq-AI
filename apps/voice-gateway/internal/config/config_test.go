package config

import (
	"os"
	"testing"
)

func TestLoad(t *testing.T) {
	// Set required environment variables
	os.Setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
	os.Setenv("CARTESIA_API_KEY", "test-cartesia-key")
	defer os.Unsetenv("DEEPGRAM_API_KEY")
	defer os.Unsetenv("CARTESIA_API_KEY")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	if cfg.DeepgramAPIKey != "test-deepgram-key" {
		t.Errorf("Expected DeepgramAPIKey 'test-deepgram-key', got '%s'", cfg.DeepgramAPIKey)
	}

	if cfg.CartesiaAPIKey != "test-cartesia-key" {
		t.Errorf("Expected CartesiaAPIKey 'test-cartesia-key', got '%s'", cfg.CartesiaAPIKey)
	}
}

func TestLoad_MissingRequired(t *testing.T) {
	// Clear environment variables
	os.Unsetenv("DEEPGRAM_API_KEY")
	os.Unsetenv("CARTESIA_API_KEY")

	_, err := Load()
	if err == nil {
		t.Error("Expected error when required keys are missing")
	}
}

func TestLoad_Defaults(t *testing.T) {
	os.Setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
	os.Setenv("CARTESIA_API_KEY", "test-cartesia-key")
	defer os.Unsetenv("DEEPGRAM_API_KEY")
	defer os.Unsetenv("CARTESIA_API_KEY")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	// Check defaults
	if cfg.Port != "8080" {
		t.Errorf("Expected default Port '8080', got '%s'", cfg.Port)
	}

	if cfg.DeepgramModel != "nova-2" {
		t.Errorf("Expected default DeepgramModel 'nova-2', got '%s'", cfg.DeepgramModel)
	}

	if cfg.DeepgramLanguage != "en" {
		t.Errorf("Expected default DeepgramLanguage 'en', got '%s'", cfg.DeepgramLanguage)
	}

	if cfg.CartesiaVoiceID != "sonic-english" {
		t.Errorf("Expected default CartesiaVoiceID 'sonic-english', got '%s'", cfg.CartesiaVoiceID)
	}

	if cfg.CartesiaModelID != "sonic" {
		t.Errorf("Expected default CartesiaModelID 'sonic', got '%s'", cfg.CartesiaModelID)
	}

	if cfg.OrchestratorURL != "localhost:50051" {
		t.Errorf("Expected default OrchestratorURL 'localhost:50051', got '%s'", cfg.OrchestratorURL)
	}

	if cfg.AudioBufferSize != 8192 {
		t.Errorf("Expected default AudioBufferSize 8192, got %d", cfg.AudioBufferSize)
	}

	if cfg.VADEnergyThreshold != 500.0 {
		t.Errorf("Expected default VADEnergyThreshold 500.0, got %f", cfg.VADEnergyThreshold)
	}

	if cfg.VADSilenceFrames != 10 {
		t.Errorf("Expected default VADSilenceFrames 10, got %d", cfg.VADSilenceFrames)
	}
}

func TestLoadFromEnv(t *testing.T) {
	os.Setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
	os.Setenv("CARTESIA_API_KEY", "test-cartesia-key")
	defer os.Unsetenv("DEEPGRAM_API_KEY")
	defer os.Unsetenv("CARTESIA_API_KEY")

	cfg, err := LoadFromEnv()
	if err != nil {
		t.Fatalf("LoadFromEnv() failed: %v", err)
	}

	if cfg.DeepgramAPIKey != "test-deepgram-key" {
		t.Errorf("Expected DeepgramAPIKey 'test-deepgram-key', got '%s'", cfg.DeepgramAPIKey)
	}
}

func TestGetEnv(t *testing.T) {
	os.Setenv("TEST_KEY", "test-value")
	defer os.Unsetenv("TEST_KEY")

	value := GetEnv("TEST_KEY", "default")
	if value != "test-value" {
		t.Errorf("Expected 'test-value', got '%s'", value)
	}

	value = GetEnv("NON_EXISTENT_KEY", "default")
	if value != "default" {
		t.Errorf("Expected 'default', got '%s'", value)
	}
}

func TestConfig_ResilienceDefaults(t *testing.T) {
	os.Setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
	os.Setenv("CARTESIA_API_KEY", "test-cartesia-key")
	defer os.Unsetenv("DEEPGRAM_API_KEY")
	defer os.Unsetenv("CARTESIA_API_KEY")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	// Check resilience defaults
	if cfg.CircuitBreakerMaxFailures != 5 {
		t.Errorf("Expected default CircuitBreakerMaxFailures 5, got %d", cfg.CircuitBreakerMaxFailures)
	}

	if cfg.CircuitBreakerResetTimeout != 30 {
		t.Errorf("Expected default CircuitBreakerResetTimeout 30, got %d", cfg.CircuitBreakerResetTimeout)
	}

	if cfg.RetryMaxAttempts != 3 {
		t.Errorf("Expected default RetryMaxAttempts 3, got %d", cfg.RetryMaxAttempts)
	}

	if cfg.RetryInitialBackoff != 100 {
		t.Errorf("Expected default RetryInitialBackoff 100, got %d", cfg.RetryInitialBackoff)
	}

	if cfg.ReconnectMaxAttempts != 5 {
		t.Errorf("Expected default ReconnectMaxAttempts 5, got %d", cfg.ReconnectMaxAttempts)
	}

	if cfg.ReconnectBackoff != 1000 {
		t.Errorf("Expected default ReconnectBackoff 1000, got %d", cfg.ReconnectBackoff)
	}
}

func TestConfig_ObservabilityDefaults(t *testing.T) {
	os.Setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
	os.Setenv("CARTESIA_API_KEY", "test-cartesia-key")
	// Clear LOG_LEVEL to ensure we get the default
	os.Unsetenv("LOG_LEVEL")
	defer os.Unsetenv("DEEPGRAM_API_KEY")
	defer os.Unsetenv("CARTESIA_API_KEY")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}

	// Check observability defaults
	// The default should be "info" (lowercase) as defined in config.go
	if cfg.LogLevel != "info" {
		t.Errorf("Expected default LogLevel 'info', got '%s'", cfg.LogLevel)
	}

	if cfg.LogPretty {
		t.Error("Expected default LogPretty false, got true")
	}

	if !cfg.MetricsEnabled {
		t.Error("Expected default MetricsEnabled true, got false")
	}
}

