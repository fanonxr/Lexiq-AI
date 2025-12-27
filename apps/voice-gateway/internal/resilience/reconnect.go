package resilience

import (
	"context"
	"fmt"
	"log"
	"time"
)

// ReconnectConfig holds configuration for reconnection logic
type ReconnectConfig struct {
	MaxAttempts int           // Maximum number of reconnection attempts
	Backoff     time.Duration // Backoff duration between attempts
	Multiplier  float64       // Backoff multiplier for exponential backoff
	MaxBackoff  time.Duration // Maximum backoff duration
}

// DefaultReconnectConfig returns a default reconnection configuration
func DefaultReconnectConfig() *ReconnectConfig {
	return &ReconnectConfig{
		MaxAttempts: 5,
		Backoff:     1 * time.Second,
		Multiplier:  2.0,
		MaxBackoff:  30 * time.Second,
	}
}

// ReconnectFunc is a function that attempts to reconnect
type ReconnectFunc func() error

// Reconnect attempts to reconnect with exponential backoff
func Reconnect(ctx context.Context, fn ReconnectFunc, config *ReconnectConfig) error {
	if config == nil {
		config = DefaultReconnectConfig()
	}

	backoff := config.Backoff

	for attempt := 0; attempt < config.MaxAttempts; attempt++ {
		// Check if context is cancelled
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		// Attempt to reconnect
		err := fn()
		if err == nil {
			log.Printf("Reconnection successful after %d attempts", attempt+1)
			return nil
		}

		// Don't sleep after the last attempt
		if attempt < config.MaxAttempts-1 {
			log.Printf("Reconnection attempt %d/%d failed: %v, retrying in %v", 
				attempt+1, config.MaxAttempts, err, backoff)

			// Wait before next attempt
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(backoff):
				// Increase backoff for next attempt
				backoff = time.Duration(float64(backoff) * config.Multiplier)
				if backoff > config.MaxBackoff {
					backoff = config.MaxBackoff
				}
			}
		}
	}

	return fmt.Errorf("failed to reconnect after %d attempts", config.MaxAttempts)
}

// ReconnectWithContext attempts to reconnect with context cancellation support
func ReconnectWithContext(ctx context.Context, fn ReconnectFunc, config *ReconnectConfig) error {
	return Reconnect(ctx, fn, config)
}

