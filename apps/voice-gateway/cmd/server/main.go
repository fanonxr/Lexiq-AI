package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/lexiqai/voice-gateway/internal/config"
	"github.com/lexiqai/voice-gateway/internal/observability"
	"github.com/lexiqai/voice-gateway/internal/orchestrator"
	"github.com/lexiqai/voice-gateway/internal/stt"
	"github.com/lexiqai/voice-gateway/internal/telephony"
	"github.com/lexiqai/voice-gateway/internal/tts"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func main() {
	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		// Use fmt for fatal errors before logger is initialized
		fmt.Fprintf(os.Stderr, "Failed to load configuration: %v\n", err)
		os.Exit(1)
	}

	// Initialize structured logger
	observability.InitLogger(cfg.LogLevel, cfg.LogPretty)
	logger := observability.GetLogger()

	logger.Info().
		Str("port", cfg.Port).
		Str("orchestrator_url", cfg.OrchestratorURL).
		Str("log_level", cfg.LogLevel).
		Bool("metrics_enabled", cfg.MetricsEnabled).
		Msg("Voice Gateway Service starting")

	// Create HTTP server
	mux := http.NewServeMux()

	// Register Twilio WebSocket handler
	mux.HandleFunc("/streams/twilio", telephony.HandleTwilioWS(cfg))

	// Health check endpoint
	mux.HandleFunc("/health", observability.HealthCheckHandler())

	// Readiness endpoint - create health check functions here to avoid import cycles
	deepgramCheck := func(ctx context.Context) (bool, error) {
		// Simple check: try to create a client (validates config)
		client := stt.NewDeepgramClient(cfg)
		if client == nil {
			return false, fmt.Errorf("failed to create Deepgram client")
		}
		// Note: We don't actually start the client to avoid API costs
		// In production, you might want to make a lightweight health check call
		return true, nil
	}
	
	cartesiaCheck := func(ctx context.Context) (bool, error) {
		// Simple check: try to create a client (validates config)
		client := tts.NewCartesiaClient(cfg)
		if client == nil {
			return false, fmt.Errorf("failed to create Cartesia client")
		}
		// Note: We don't make an actual API call to avoid costs
		return true, nil
	}
	
	orchestratorCheck := func(ctx context.Context) (bool, error) {
		client, err := orchestrator.NewOrchestratorClient(cfg)
		if err != nil {
			return false, err
		}
		defer client.Close()
		return client.HealthCheck(ctx)
	}
	
	mux.HandleFunc("/ready", observability.ReadinessHandler(deepgramCheck, cartesiaCheck, orchestratorCheck))

	// Metrics endpoint (Prometheus)
	if cfg.MetricsEnabled {
		mux.Handle("/metrics", promhttp.Handler())
		logger.Info().Msg("Prometheus metrics enabled at /metrics")
	}

	// Create HTTP server with timeouts
	server := &http.Server{
		Addr:         fmt.Sprintf(":%s", cfg.Port),
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server in a goroutine
	go func() {
		logger.Info().
			Str("port", cfg.Port).
			Str("endpoint", fmt.Sprintf("ws://localhost:%s/streams/twilio", cfg.Port)).
			Msg("Server listening")
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal().Err(err).Msg("Server failed to start")
		}
	}()

	// Wait for interrupt signal to gracefully shutdown the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info().Msg("Shutting down server...")

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		logger.Fatal().Err(err).Msg("Server forced to shutdown")
	}

	logger.Info().Msg("Server exited gracefully")
}

