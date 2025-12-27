package resilience

import (
	"errors"
	"sync"
	"time"
)

// CircuitState represents the state of a circuit breaker
type CircuitState int

const (
	StateClosed CircuitState = iota // Normal operation
	StateOpen                       // Circuit is open, requests fail immediately
	StateHalfOpen                   // Testing if service has recovered
)

// CircuitBreaker implements the circuit breaker pattern
type CircuitBreaker struct {
	name          string
	maxFailures   int           // Number of failures before opening circuit
	resetTimeout  time.Duration // Time to wait before attempting half-open
	halfOpenMax   int           // Max requests in half-open state
	halfOpenCount int           // Current requests in half-open state

	mu            sync.RWMutex
	state         CircuitState
	failureCount  int
	lastFailTime  time.Time
	successCount  int
	requestCount  int64
	failureCountTotal int64
}

// NewCircuitBreaker creates a new circuit breaker
func NewCircuitBreaker(name string, maxFailures int, resetTimeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		name:         name,
		maxFailures:  maxFailures,
		resetTimeout: resetTimeout,
		halfOpenMax:  3, // Allow 3 requests in half-open state
		state:        StateClosed,
	}
}

// Call executes a function with circuit breaker protection
func (cb *CircuitBreaker) Call(fn func() error) error {
	// Check if we should allow the request
	if !cb.allowRequest() {
		return errors.New("circuit breaker is open")
	}

	// Execute the function
	err := fn()

	// Record the result
	cb.recordResult(err == nil)

	return err
}

// allowRequest checks if a request should be allowed
func (cb *CircuitBreaker) allowRequest() bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	now := time.Now()

	switch cb.state {
	case StateClosed:
		// Normal operation - allow all requests
		return true

	case StateOpen:
		// Circuit is open - check if we should transition to half-open
		if now.Sub(cb.lastFailTime) >= cb.resetTimeout {
			cb.state = StateHalfOpen
			cb.halfOpenCount = 0
			cb.successCount = 0
			return true // Allow one request to test
		}
		return false

	case StateHalfOpen:
		// Testing recovery - allow limited requests
		if cb.halfOpenCount < cb.halfOpenMax {
			return true
		}
		return false // Too many requests in half-open, wait
	}

	return false
}

// RecordResult records the result of a request (public method for manual recording)
func (cb *CircuitBreaker) RecordResult(success bool) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.requestCount++

	if success {
		cb.recordSuccess()
	} else {
		cb.recordFailure()
	}
}

// recordResult records the result of a request (internal)
func (cb *CircuitBreaker) recordResult(success bool) {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.requestCount++

	if success {
		cb.recordSuccess()
	} else {
		cb.recordFailure()
	}
}

// recordSuccess records a successful request
func (cb *CircuitBreaker) recordSuccess() {
	switch cb.state {
	case StateClosed:
		// Reset failure count on success
		cb.failureCount = 0

	case StateHalfOpen:
		cb.successCount++
		// If we have enough successes, close the circuit
		if cb.successCount >= cb.halfOpenMax {
			cb.state = StateClosed
			cb.failureCount = 0
			cb.halfOpenCount = 0
			cb.successCount = 0
		}
	}
}

// recordFailure records a failed request
func (cb *CircuitBreaker) recordFailure() {
	cb.failureCountTotal++
	cb.lastFailTime = time.Now()

	switch cb.state {
	case StateClosed:
		cb.failureCount++
		// If we exceed max failures, open the circuit
		if cb.failureCount >= cb.maxFailures {
			cb.state = StateOpen
		}

	case StateHalfOpen:
		// Any failure in half-open immediately opens the circuit
		cb.state = StateOpen
		cb.halfOpenCount = 0
		cb.successCount = 0
	}
}

// GetState returns the current state of the circuit breaker
func (cb *CircuitBreaker) GetState() CircuitState {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state
}

// GetStats returns statistics about the circuit breaker
func (cb *CircuitBreaker) GetStats() (state CircuitState, requestCount, failureCount int64, failureRate float64) {
	cb.mu.RLock()
	defer cb.mu.RUnlock()

	state = cb.state
	requestCount = cb.requestCount
	failureCount = cb.failureCountTotal

	if requestCount > 0 {
		failureRate = float64(failureCount) / float64(requestCount) * 100.0
	}

	return
}

// Reset manually resets the circuit breaker to closed state
func (cb *CircuitBreaker) Reset() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.state = StateClosed
	cb.failureCount = 0
	cb.halfOpenCount = 0
	cb.successCount = 0
}

