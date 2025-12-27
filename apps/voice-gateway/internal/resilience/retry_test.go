package resilience

import (
	"errors"
	"testing"
	"time"
)

func TestRetry_Success(t *testing.T) {
	attempts := 0
	err := Retry(func() error {
		attempts++
		return nil
	}, DefaultRetryConfig(), nil)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if attempts != 1 {
		t.Errorf("Expected 1 attempt, got %d", attempts)
	}
}

func TestRetry_FailureThenSuccess(t *testing.T) {
	attempts := 0
	err := Retry(func() error {
		attempts++
		if attempts < 3 {
			return errors.New("temporary error")
		}
		return nil
	}, DefaultRetryConfig(), nil)

	if err != nil {
		t.Errorf("Expected no error after retries, got %v", err)
	}
	if attempts != 3 {
		t.Errorf("Expected 3 attempts, got %d", attempts)
	}
}

func TestRetry_MaxAttempts(t *testing.T) {
	config := &RetryConfig{
		MaxAttempts:      2,
		InitialBackoff:   10 * time.Millisecond,
		MaxBackoff:       100 * time.Millisecond,
		BackoffMultiplier: 2.0,
		Jitter:           false,
	}

	attempts := 0
	err := Retry(func() error {
		attempts++
		return errors.New("persistent error")
	}, config, nil)

	if err == nil {
		t.Error("Expected error after max attempts")
	}
	if attempts != 2 {
		t.Errorf("Expected 2 attempts, got %d", attempts)
	}
}

func TestRetry_NonRetryableError(t *testing.T) {
	config := &RetryConfig{
		MaxAttempts:      3,
		InitialBackoff:  10 * time.Millisecond,
		MaxBackoff:      100 * time.Millisecond,
		BackoffMultiplier: 2.0,
		Jitter:           false,
	}

	attempts := 0
	isRetryable := func(err error) bool {
		return false // All errors are non-retryable
	}

	err := Retry(func() error {
		attempts++
		return errors.New("non-retryable error")
	}, config, isRetryable)

	if err == nil {
		t.Error("Expected error")
	}
	if attempts != 1 {
		t.Errorf("Expected 1 attempt for non-retryable error, got %d", attempts)
	}
}

func TestRetry_RetryableError(t *testing.T) {
	config := &RetryConfig{
		MaxAttempts:      3,
		InitialBackoff:  10 * time.Millisecond,
		MaxBackoff:      100 * time.Millisecond,
		BackoffMultiplier: 2.0,
		Jitter:           false,
	}

	attempts := 0
	isRetryable := func(err error) bool {
		return true // All errors are retryable
	}

	err := Retry(func() error {
		attempts++
		return errors.New("retryable error")
	}, config, isRetryable)

	if err == nil {
		t.Error("Expected error after max attempts")
	}
	if attempts != 3 {
		t.Errorf("Expected 3 attempts for retryable error, got %d", attempts)
	}
}

func TestIsRetryableNetworkError(t *testing.T) {
	tests := []struct {
		name     string
		err      error
		expected bool
	}{
		{"connection refused", errors.New("connection refused"), true},
		{"connection reset", errors.New("connection reset"), true},
		{"unavailable", errors.New("unavailable"), true},
		{"deadline exceeded", errors.New("deadline exceeded"), true},
		{"timeout", errors.New("timeout"), true},
		{"resource exhausted", errors.New("resource exhausted"), true},
		{"rate limit", errors.New("rate limit"), true},
		{"other error", errors.New("other error"), false},
		{"nil error", nil, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := IsRetryableNetworkError(tt.err)
			if result != tt.expected {
				t.Errorf("Expected %v, got %v", tt.expected, result)
			}
		})
	}
}

func TestRetryWithExponentialBackoff(t *testing.T) {
	attempts := 0
	err := RetryWithExponentialBackoff(func() error {
		attempts++
		if attempts < 2 {
			return errors.New("temporary error")
		}
		return nil
	}, 3, 10*time.Millisecond)

	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}
	if attempts != 2 {
		t.Errorf("Expected 2 attempts, got %d", attempts)
	}
}

func TestCalculateBackoff(t *testing.T) {
	tests := []struct {
		attempt        int
		initialBackoff time.Duration
		maxBackoff     time.Duration
		multiplier     float64
		expectedMin    time.Duration
		expectedMax    time.Duration
	}{
		{0, 100 * time.Millisecond, 1 * time.Second, 2.0, 100 * time.Millisecond, 100 * time.Millisecond},
		{1, 100 * time.Millisecond, 1 * time.Second, 2.0, 200 * time.Millisecond, 200 * time.Millisecond},
		{2, 100 * time.Millisecond, 1 * time.Second, 2.0, 400 * time.Millisecond, 400 * time.Millisecond},
		{5, 100 * time.Millisecond, 1 * time.Second, 2.0, 1 * time.Second, 1 * time.Second}, // Capped at max
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			backoff := CalculateBackoff(tt.attempt, tt.initialBackoff, tt.maxBackoff, tt.multiplier)
			if backoff < tt.expectedMin || backoff > tt.expectedMax {
				t.Errorf("Expected backoff between %v and %v, got %v",
					tt.expectedMin, tt.expectedMax, backoff)
			}
		})
	}
}

func TestNewRetryableError(t *testing.T) {
	originalErr := errors.New("original error")
	retryableErr := NewRetryableError(originalErr)

	if retryableErr.Error() != "original error" {
		t.Errorf("Expected error message 'original error', got %s", retryableErr.Error())
	}

	if !IsRetryable(retryableErr) {
		t.Error("Expected error to be retryable")
	}

	if IsRetryable(originalErr) {
		t.Error("Expected original error to not be retryable")
	}
}

