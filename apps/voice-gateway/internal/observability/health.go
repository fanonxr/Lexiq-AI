package observability

import (
	"context"
	"encoding/json"
	"net/http"
	"time"
)

// HealthStatus represents the health status of the service
type HealthStatus struct {
	Status      string                 `json:"status"`
	Service     string                 `json:"service"`
	Version     string                 `json:"version"`
	Timestamp   string                 `json:"timestamp"`
	Dependencies map[string]DependencyStatus `json:"dependencies,omitempty"`
}

// DependencyStatus represents the status of a dependency
type DependencyStatus struct {
	Status    string `json:"status"`
	Message   string `json:"message,omitempty"`
	LatencyMs int64  `json:"latency_ms,omitempty"`
}

// HealthCheckHandler handles health check requests
func HealthCheckHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		status := HealthStatus{
			Status:    "healthy",
			Service:   "voice-gateway",
			Version:   "1.0.0",
			Timestamp: time.Now().UTC().Format(time.RFC3339),
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(status)
	}
}

// ReadinessHandler handles readiness check requests
// It accepts health check functions for each dependency to avoid import cycles
type HealthCheckFunc func(ctx context.Context) (bool, error)

func ReadinessHandler(
	deepgramCheck HealthCheckFunc,
	cartesiaCheck HealthCheckFunc,
	orchestratorCheck HealthCheckFunc,
) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		dependencies := make(map[string]DependencyStatus)
		allHealthy := true
		ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
		defer cancel()

		// Check Deepgram STT
		if deepgramCheck != nil {
			start := time.Now()
			healthy, err := deepgramCheck(ctx)
			latency := time.Since(start).Milliseconds()
			
			status := "healthy"
			message := ""
			if err != nil || !healthy {
				status = "unhealthy"
				allHealthy = false
				if err != nil {
					message = err.Error()
				}
			}
			
			dependencies["deepgram"] = DependencyStatus{
				Status:    status,
				Message:   message,
				LatencyMs: latency,
			}
		}

		// Check Cartesia TTS
		if cartesiaCheck != nil {
			start := time.Now()
			healthy, err := cartesiaCheck(ctx)
			latency := time.Since(start).Milliseconds()
			
			status := "healthy"
			message := ""
			if err != nil || !healthy {
				status = "unhealthy"
				allHealthy = false
				if err != nil {
					message = err.Error()
				}
			}
			
			dependencies["cartesia"] = DependencyStatus{
				Status:    status,
				Message:   message,
				LatencyMs: latency,
			}
		}

		// Check Orchestrator
		if orchestratorCheck != nil {
			start := time.Now()
			healthy, err := orchestratorCheck(ctx)
			latency := time.Since(start).Milliseconds()
			
			status := "healthy"
			message := ""
			if err != nil || !healthy {
				status = "unhealthy"
				allHealthy = false
				if err != nil {
					message = err.Error()
				}
			}
			
			dependencies["orchestrator"] = DependencyStatus{
				Status:    status,
				Message:   message,
				LatencyMs: latency,
			}
		}

		status := HealthStatus{
			Status:      "ready",
			Service:     "voice-gateway",
			Version:     "1.0.0",
			Timestamp:   time.Now().UTC().Format(time.RFC3339),
			Dependencies: dependencies,
		}

		if !allHealthy {
			status.Status = "not_ready"
			w.WriteHeader(http.StatusServiceUnavailable)
		} else {
			w.WriteHeader(http.StatusOK)
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(status)
	}
}
