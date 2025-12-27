package observability

import (
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// Call metrics
	activeCalls = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "voice_gateway_active_calls",
		Help: "Number of active phone calls",
	})

	totalCalls = promauto.NewCounter(prometheus.CounterOpts{
		Name: "voice_gateway_calls_total",
		Help: "Total number of calls processed",
	})

	callDuration = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "voice_gateway_call_duration_seconds",
		Help:    "Duration of phone calls in seconds",
		Buckets: []float64{1, 5, 10, 30, 60, 120, 300, 600},
	})

	// STT metrics
	sttRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "voice_gateway_stt_requests_total",
		Help: "Total number of STT requests",
	}, []string{"status"})

	sttLatency = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "voice_gateway_stt_latency_seconds",
		Help:    "STT processing latency in seconds",
		Buckets: []float64{0.1, 0.25, 0.5, 1.0, 2.0, 5.0},
	})

	// TTS metrics
	ttsRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "voice_gateway_tts_requests_total",
		Help: "Total number of TTS requests",
	}, []string{"status"})

	ttsLatency = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "voice_gateway_tts_latency_seconds",
		Help:    "TTS processing latency in seconds",
		Buckets: []float64{0.1, 0.25, 0.5, 1.0, 2.0, 5.0},
	})

	// Orchestrator metrics
	orchestratorRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "voice_gateway_orchestrator_requests_total",
		Help: "Total number of Orchestrator requests",
	}, []string{"status"})

	orchestratorLatency = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "voice_gateway_orchestrator_latency_seconds",
		Help:    "Orchestrator processing latency in seconds",
		Buckets: []float64{0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0},
	})

	// Error metrics
	errorsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "voice_gateway_errors_total",
		Help: "Total number of errors",
	}, []string{"type", "component"})

	// Circuit breaker metrics
	circuitBreakerState = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "voice_gateway_circuit_breaker_state",
		Help: "Circuit breaker state (0=closed, 1=open, 2=half-open)",
	}, []string{"service"})

	circuitBreakerFailures = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "voice_gateway_circuit_breaker_failures_total",
		Help: "Total circuit breaker failures",
	}, []string{"service"})

	// Audio metrics
	audioBytesProcessed = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "voice_gateway_audio_bytes_total",
		Help: "Total audio bytes processed",
	}, []string{"direction"}) // direction: "in" or "out"
)

// Metrics tracks metrics for a single call
type Metrics struct {
	callID         string
	startTime      time.Time
	sttStartTime   time.Time
	ttsStartTime   time.Time
	orchestratorStartTime time.Time
	mu             sync.Mutex
}

// NewCallMetrics creates a new metrics tracker for a call
func NewCallMetrics(callID string) *Metrics {
	return &Metrics{
		callID:    callID,
		startTime: time.Now(),
	}
}

// RecordCallStart records the start of a call
func (m *Metrics) RecordCallStart() {
	activeCalls.Inc()
	totalCalls.Inc()
}

// RecordCallEnd records the end of a call
func (m *Metrics) RecordCallEnd() {
	activeCalls.Dec()
	duration := time.Since(m.startTime).Seconds()
	callDuration.Observe(duration)
}

// RecordSTTStart records the start of STT processing
func (m *Metrics) RecordSTTStart() {
	m.mu.Lock()
	m.sttStartTime = time.Now()
	m.mu.Unlock()
}

// RecordSTTEnd records the end of STT processing
func (m *Metrics) RecordSTTEnd(success bool) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.sttStartTime.IsZero() {
		latency := time.Since(m.sttStartTime).Seconds()
		sttLatency.Observe(latency)
	}

	status := "success"
	if !success {
		status = "error"
	}
	sttRequests.WithLabelValues(status).Inc()
}

// RecordTTSStart records the start of TTS processing
func (m *Metrics) RecordTTSStart() {
	m.mu.Lock()
	m.ttsStartTime = time.Now()
	m.mu.Unlock()
}

// RecordTTSEnd records the end of TTS processing
func (m *Metrics) RecordTTSEnd(success bool) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.ttsStartTime.IsZero() {
		latency := time.Since(m.ttsStartTime).Seconds()
		ttsLatency.Observe(latency)
	}

	status := "success"
	if !success {
		status = "error"
	}
	ttsRequests.WithLabelValues(status).Inc()
}

// RecordOrchestratorStart records the start of Orchestrator processing
func (m *Metrics) RecordOrchestratorStart() {
	m.mu.Lock()
	m.orchestratorStartTime = time.Now()
	m.mu.Unlock()
}

// RecordOrchestratorEnd records the end of Orchestrator processing
func (m *Metrics) RecordOrchestratorEnd(success bool) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.orchestratorStartTime.IsZero() {
		latency := time.Since(m.orchestratorStartTime).Seconds()
		orchestratorLatency.Observe(latency)
	}

	status := "success"
	if !success {
		status = "error"
	}
	orchestratorRequests.WithLabelValues(status).Inc()
}

// RecordError records an error
func (m *Metrics) RecordError(errorType, component string) {
	errorsTotal.WithLabelValues(errorType, component).Inc()
}

// RecordAudioBytes records audio bytes processed
func (m *Metrics) RecordAudioBytes(direction string, bytes int64) {
	audioBytesProcessed.WithLabelValues(direction).Add(float64(bytes))
}

// UpdateCircuitBreakerState updates circuit breaker state metric
func UpdateCircuitBreakerState(service string, state int) {
	circuitBreakerState.WithLabelValues(service).Set(float64(state))
}

// IncrementCircuitBreakerFailures increments circuit breaker failure counter
func IncrementCircuitBreakerFailures(service string) {
	circuitBreakerFailures.WithLabelValues(service).Inc()
}

