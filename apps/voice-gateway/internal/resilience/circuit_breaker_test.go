package resilience

import (
	"errors"
	"testing"
	"time"
)

func TestCircuitBreaker_StateClosed(t *testing.T) {
	cb := NewCircuitBreaker("test", 3, 1*time.Second)

	if cb.GetState() != StateClosed {
		t.Errorf("Expected initial state to be Closed, got %d", cb.GetState())
	}

	// Should allow requests
	if !cb.allowRequest() {
		t.Error("Expected to allow request in Closed state")
	}
}

func TestCircuitBreaker_OpenAfterFailures(t *testing.T) {
	cb := NewCircuitBreaker("test", 3, 1*time.Second)

	// Record failures
	cb.RecordResult(false)
	cb.RecordResult(false)
	if cb.GetState() != StateClosed {
		t.Error("Expected state to still be Closed after 2 failures")
	}

	// Third failure should open circuit
	cb.RecordResult(false)
	if cb.GetState() != StateOpen {
		t.Error("Expected state to be Open after 3 failures")
	}

	// Should not allow requests
	if cb.allowRequest() {
		t.Error("Expected to not allow request in Open state")
	}
}

func TestCircuitBreaker_HalfOpen(t *testing.T) {
	cb := NewCircuitBreaker("test", 3, 100*time.Millisecond)

	// Open the circuit
	cb.RecordResult(false)
	cb.RecordResult(false)
	cb.RecordResult(false)

	if cb.GetState() != StateOpen {
		t.Fatal("Expected circuit to be Open")
	}

	// Wait for reset timeout
	time.Sleep(150 * time.Millisecond)

	// Should transition to HalfOpen
	if !cb.allowRequest() {
		t.Error("Expected to allow request after timeout (HalfOpen)")
	}

	// Check state
	state, _, _, _ := cb.GetStats()
	if state != StateHalfOpen {
		t.Errorf("Expected state to be HalfOpen, got %d", state)
	}
}

func TestCircuitBreaker_CloseAfterSuccess(t *testing.T) {
	cb := NewCircuitBreaker("test", 3, 100*time.Millisecond)

	// Open the circuit
	cb.RecordResult(false)
	cb.RecordResult(false)
	cb.RecordResult(false)

	// Wait for reset timeout
	time.Sleep(150 * time.Millisecond)

	// Record successes in HalfOpen state
	for i := 0; i < 3; i++ {
		cb.RecordResult(true)
	}

	if cb.GetState() != StateClosed {
		t.Error("Expected state to be Closed after successes in HalfOpen")
	}
}

func TestCircuitBreaker_OpenAfterFailureInHalfOpen(t *testing.T) {
	cb := NewCircuitBreaker("test", 3, 100*time.Millisecond)

	// Open the circuit
	cb.RecordResult(false)
	cb.RecordResult(false)
	cb.RecordResult(false)

	// Wait for reset timeout
	time.Sleep(150 * time.Millisecond)

	// Record a failure in HalfOpen (should immediately open)
	cb.RecordResult(false)

	if cb.GetState() != StateOpen {
		t.Error("Expected state to be Open after failure in HalfOpen")
	}
}

func TestCircuitBreaker_Call(t *testing.T) {
	cb := NewCircuitBreaker("test", 3, 1*time.Second)

	// Successful call
	err := cb.Call(func() error {
		return nil
	})
	if err != nil {
		t.Errorf("Expected no error, got %v", err)
	}

	// Failed call
	err = cb.Call(func() error {
		return errors.New("test error")
	})
	if err == nil {
		t.Error("Expected error from failed call")
	}
}

func TestCircuitBreaker_CallOpen(t *testing.T) {
	cb := NewCircuitBreaker("test", 1, 1*time.Second)

	// Open the circuit
	cb.RecordResult(false)

	// Call should fail immediately
	err := cb.Call(func() error {
		return nil
	})
	if err == nil {
		t.Error("Expected error when circuit is open")
	}
	if err.Error() != "circuit breaker is open" {
		t.Errorf("Expected 'circuit breaker is open' error, got %v", err)
	}
}

func TestCircuitBreaker_GetStats(t *testing.T) {
	cb := NewCircuitBreaker("test", 3, 1*time.Second)

	// Record some results
	cb.RecordResult(true)
	cb.RecordResult(true)
	cb.RecordResult(false)

	state, requestCount, failureCount, failureRate := cb.GetStats()

	if state != StateClosed {
		t.Errorf("Expected state Closed, got %d", state)
	}
	if requestCount != 3 {
		t.Errorf("Expected 3 requests, got %d", requestCount)
	}
	if failureCount != 1 {
		t.Errorf("Expected 1 failure, got %d", failureCount)
	}
	expectedRate := 100.0 / 3.0 // 33.33%
	if failureRate < 33.0 || failureRate > 34.0 {
		t.Errorf("Expected failure rate around 33.33%%, got %.2f%%", failureRate)
	}
}

func TestCircuitBreaker_Reset(t *testing.T) {
	cb := NewCircuitBreaker("test", 3, 1*time.Second)

	// Open the circuit
	cb.RecordResult(false)
	cb.RecordResult(false)
	cb.RecordResult(false)

	if cb.GetState() != StateOpen {
		t.Fatal("Expected circuit to be Open")
	}

	// Reset
	cb.Reset()

	if cb.GetState() != StateClosed {
		t.Error("Expected state to be Closed after reset")
	}

	state, requestCount, failureCount, _ := cb.GetStats()
	if state != StateClosed || requestCount != 0 || failureCount != 0 {
		t.Error("Expected stats to be reset")
	}
}

