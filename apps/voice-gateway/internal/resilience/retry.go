package resilience

import (
	"errors"
	"math"
	"time"
)

// RetryConfig holds configuration for retry logic
type RetryConfig struct {
	MaxAttempts      int           // Maximum number of retry attempts
	InitialBackoff   time.Duration // Initial backoff duration
	MaxBackoff       time.Duration // Maximum backoff duration
	BackoffMultiplier float64       // Multiplier for exponential backoff
	Jitter           bool          // Whether to add jitter to backoff
}

// DefaultRetryConfig returns a default retry configuration
func DefaultRetryConfig() *RetryConfig {
	return &RetryConfig{
		MaxAttempts:      3,
		InitialBackoff:   100 * time.Millisecond,
		MaxBackoff:       5 * time.Second,
		BackoffMultiplier: 2.0,
		Jitter:           true,
	}
}

// RetryableFunc is a function that can be retried
type RetryableFunc func() error

// IsRetryableError checks if an error is retryable
type IsRetryableError func(error) bool

// Retry executes a function with retry logic
func Retry(fn RetryableFunc, config *RetryConfig, isRetryable IsRetryableError) error {
	if config == nil {
		config = DefaultRetryConfig()
	}

	var lastErr error
	backoff := config.InitialBackoff

	for attempt := 0; attempt < config.MaxAttempts; attempt++ {
		err := fn()
		if err == nil {
			return nil // Success
		}

		lastErr = err

		// Check if error is retryable
		if isRetryable != nil && !isRetryable(err) {
			return err // Non-retryable error
		}

		// Don't sleep after the last attempt
		if attempt < config.MaxAttempts-1 {
			// Calculate backoff with exponential growth
			sleepDuration := backoff

			// Add jitter if enabled (up to 25% of backoff)
			if config.Jitter {
				jitter := time.Duration(float64(sleepDuration) * 0.25 * (1.0 - 0.5)) // 0-25% jitter
				sleepDuration += jitter
			}

			// Cap at max backoff
			if sleepDuration > config.MaxBackoff {
				sleepDuration = config.MaxBackoff
			}

			time.Sleep(sleepDuration)

			// Increase backoff for next attempt
			backoff = time.Duration(float64(backoff) * config.BackoffMultiplier)
			if backoff > config.MaxBackoff {
				backoff = config.MaxBackoff
			}
		}
	}

	return lastErr
}

// RetryWithExponentialBackoff is a convenience function for retry with exponential backoff
func RetryWithExponentialBackoff(fn RetryableFunc, maxAttempts int, initialBackoff time.Duration) error {
	config := &RetryConfig{
		MaxAttempts:      maxAttempts,
		InitialBackoff:   initialBackoff,
		MaxBackoff:       5 * time.Second,
		BackoffMultiplier: 2.0,
		Jitter:           true,
	}

	return Retry(fn, config, nil)
}

// CalculateBackoff calculates the backoff duration for a given attempt
func CalculateBackoff(attempt int, initialBackoff time.Duration, maxBackoff time.Duration, multiplier float64) time.Duration {
	backoff := time.Duration(float64(initialBackoff) * math.Pow(multiplier, float64(attempt)))
	if backoff > maxBackoff {
		return maxBackoff
	}
	return backoff
}

// IsRetryableNetworkError checks if an error is a retryable network error
func IsRetryableNetworkError(err error) bool {
	if err == nil {
		return false
	}

	errStr := err.Error()
	
	// Connection errors
	if containsAny(errStr, []string{
		"connection refused",
		"connection reset",
		"connection closed",
		"transport is closing",
		"unavailable",
		"network is unreachable",
		"no route to host",
	}) {
		return true
	}

	// Timeout errors
	if containsAny(errStr, []string{
		"deadline exceeded",
		"context deadline exceeded",
		"timeout",
		"i/o timeout",
	}) {
		return true
	}

	// Resource exhaustion (may be temporary)
	if containsAny(errStr, []string{
		"resource exhausted",
		"too many connections",
		"rate limit",
	}) {
		return true
	}

	return false
}

// containsAny checks if a string contains any of the substrings
func containsAny(s string, substrings []string) bool {
	for _, substr := range substrings {
		if len(s) >= len(substr) {
			for i := 0; i <= len(s)-len(substr); i++ {
				if s[i:i+len(substr)] == substr {
					return true
				}
			}
		}
	}
	return false
}

// RetryableError wraps an error to indicate it's retryable
type RetryableError struct {
	Err error
}

func (e *RetryableError) Error() string {
	return e.Err.Error()
}

func (e *RetryableError) Unwrap() error {
	return e.Err
}

// NewRetryableError creates a new retryable error
func NewRetryableError(err error) error {
	if err == nil {
		return nil
	}
	return &RetryableError{Err: err}
}

// IsRetryable checks if an error is a RetryableError
func IsRetryable(err error) bool {
	var retryableErr *RetryableError
	return errors.As(err, &retryableErr)
}

