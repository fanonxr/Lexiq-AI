package orchestrator

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/keepalive"

	"github.com/lexiqai/voice-gateway/internal/config"
	"github.com/lexiqai/voice-gateway/internal/orchestrator/proto"
	"github.com/lexiqai/voice-gateway/internal/observability"
	"github.com/lexiqai/voice-gateway/internal/resilience"
)

// OrchestratorClient manages the gRPC connection to the Cognitive Orchestrator
type OrchestratorClient struct {
	config        *config.Config
	conn          *grpc.ClientConn
	client        proto.CognitiveOrchestratorClient
	mu            sync.RWMutex
	isConnected   bool
	circuitBreaker *resilience.CircuitBreaker
}

// NewOrchestratorClient creates a new Orchestrator gRPC client
func NewOrchestratorClient(cfg *config.Config) (*OrchestratorClient, error) {
	client := &OrchestratorClient{
		config:      cfg,
		isConnected: false,
	}

	// Connect to Orchestrator
	if err := client.connect(); err != nil {
		return nil, fmt.Errorf("failed to connect to orchestrator: %w", err)
	}

	return client, nil
}

// connect establishes a gRPC connection to the Orchestrator
func (c *OrchestratorClient) connect() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.isConnected && c.conn != nil {
		return nil // Already connected
	}

	// Configure connection options
	var opts []grpc.DialOption

	// TLS configuration
	if c.config.OrchestratorTLSEnabled {
		// TODO: Add TLS credentials for production
		log.Printf("Warning: TLS enabled but not configured, using insecure connection")
		opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))
	} else {
		opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))
	}

	// Keepalive settings for long-lived connections
	opts = append(opts, grpc.WithKeepaliveParams(keepalive.ClientParameters{
		Time:                10 * time.Second,
		Timeout:             3 * time.Second,
		PermitWithoutStream: true,
	}))

	// Connection timeout
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(c.config.OrchestratorTimeout)*time.Second)
	defer cancel()

	// Dial the server
	conn, err := grpc.DialContext(ctx, c.config.OrchestratorURL, opts...)
	if err != nil {
		return fmt.Errorf("failed to dial orchestrator at %s: %w", c.config.OrchestratorURL, err)
	}

	c.conn = conn
	c.client = proto.NewCognitiveOrchestratorClient(conn)
	c.isConnected = true

	log.Printf("Connected to Orchestrator at %s", c.config.OrchestratorURL)
	return nil
}

// ProcessTextStream sends text to the Orchestrator and streams responses back
func (c *OrchestratorClient) ProcessTextStream(
	ctx context.Context,
	conversationID string,
	text string,
	userID string,
	firmID string,
) (<-chan *OrchestratorResponse, error) {

	// Create request
	req := &proto.TextRequest{
		ConversationId: conversationID,
		Text:           text,
		UserId:         userID,
		FirmId:         firmID,
		IncludeRag:     true,
		ToolsEnabled:   true,
		// Model can be left empty to use default
	}

	// Use circuit breaker to protect the call
	var stream proto.CognitiveOrchestrator_ProcessTextClient
	var err error

	err = c.circuitBreaker.Call(func() error {
		// Retry logic with exponential backoff
		retryConfig := &resilience.RetryConfig{
			MaxAttempts:      c.config.RetryMaxAttempts,
			InitialBackoff:   time.Duration(c.config.RetryInitialBackoff) * time.Millisecond,
			MaxBackoff:       5 * time.Second,
			BackoffMultiplier: 2.0,
			Jitter:           true,
		}

		err = resilience.Retry(func() error {
			// Check connection and reconnect if needed
			c.mu.RLock()
			connected := c.isConnected
			c.mu.RUnlock()

			if !connected {
				if reconnectErr := c.connect(); reconnectErr != nil {
					return fmt.Errorf("failed to reconnect: %w", reconnectErr)
				}
			}

			// Make the call
			c.mu.RLock()
			client := c.client
			c.mu.RUnlock()

			if client == nil {
				return fmt.Errorf("orchestrator client is nil")
			}

			var callErr error
			stream, callErr = client.ProcessText(ctx, req)
			return callErr
		}, retryConfig, resilience.IsRetryableNetworkError)

		return err
	})
	
	// Update circuit breaker metrics
	observability.UpdateCircuitBreakerState("orchestrator", int(c.circuitBreaker.GetState()))
	if err != nil {
		observability.IncrementCircuitBreakerFailures("orchestrator")
	}

	if err != nil {
		return nil, fmt.Errorf("failed to call ProcessText: %w", err)
	}

	// Create response channel
	responseChan := make(chan *OrchestratorResponse, 100)

	// Start goroutine to receive streaming responses
	go func() {
		defer close(responseChan)

		for {
			select {
			case <-ctx.Done():
				log.Printf("ProcessText stream context cancelled")
				return
			default:
				// Receive response from stream
				resp, err := stream.Recv()
				if err != nil {
					// Check if error is retryable
					if isRetryableError(err) {
						log.Printf("Retryable error receiving from ProcessText stream: %v", err)
						// Could implement reconnection logic here if needed
					} else {
						log.Printf("Error receiving from ProcessText stream: %v", err)
					}
					return
				}

				// Convert proto response to our response type
				orchestratorResp := &OrchestratorResponse{
					ConversationID: resp.ConversationId,
					IsDone:         resp.IsDone,
					TotalTokens:    resp.TotalTokens,
				}

				// Handle oneof content field
				switch content := resp.Content.(type) {
				case *proto.TextResponse_TextChunk:
					orchestratorResp.TextChunk = content.TextChunk
				case *proto.TextResponse_ToolCall:
					orchestratorResp.ToolCall = &ToolCall{
						ToolName:      content.ToolCall.ToolName,
						ParametersJSON: content.ToolCall.ParametersJson,
						CallID:        content.ToolCall.CallId,
					}
					log.Printf("Orchestrator tool call: %s (call_id: %s)", content.ToolCall.ToolName, content.ToolCall.CallId)
				case *proto.TextResponse_ToolResult:
					orchestratorResp.ToolResult = &ToolResult{
						CallID:       content.ToolResult.CallId,
						ResultJSON:   content.ToolResult.ResultJson,
						Success:      content.ToolResult.Success,
						ErrorMessage: content.ToolResult.ErrorMessage,
					}
					log.Printf("Orchestrator tool result: call_id=%s, success=%v", content.ToolResult.CallId, content.ToolResult.Success)
				case *proto.TextResponse_Error:
					orchestratorResp.Error = &Error{
						Code:        content.Error.Code,
						Message:     content.Error.Message,
						DetailsJSON: content.Error.DetailsJson,
					}
					log.Printf("Orchestrator error: %s - %s", content.Error.Code, content.Error.Message)
				}

				// Send response to channel (non-blocking)
				select {
				case responseChan <- orchestratorResp:
					if orchestratorResp.IsDone {
						log.Printf("ProcessText stream completed for conversation %s", conversationID)
						return
					}
				default:
					log.Printf("Warning: orchestrator response channel full, dropping response")
				}
			}
		}
	}()

	return responseChan, nil
}

// HealthCheck checks if the Orchestrator is healthy
func (c *OrchestratorClient) HealthCheck(ctx context.Context) (bool, error) {
	c.mu.RLock()
	if !c.isConnected || c.client == nil {
		c.mu.RUnlock()
		return false, fmt.Errorf("orchestrator client is not connected")
	}
	client := c.client
	c.mu.RUnlock()

	req := &proto.HealthRequest{}
	resp, err := client.HealthCheck(ctx, req)
	if err != nil {
		return false, fmt.Errorf("health check failed: %w", err)
	}

	return resp.Healthy, nil
}

// Close closes the gRPC connection
func (c *OrchestratorClient) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.conn != nil {
		err := c.conn.Close()
		c.isConnected = false
		c.conn = nil
		c.client = nil
		return err
	}

	return nil
}

// IsConnected returns whether the client is currently connected
func (c *OrchestratorClient) IsConnected() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.isConnected
}

// isRetryableError checks if an error is retryable
func isRetryableError(err error) bool {
	if err == nil {
		return false
	}
	
	// Check for gRPC status codes that are retryable
	errStr := strings.ToLower(err.Error())
	
	// Connection errors
	if strings.Contains(errStr, "connection refused") || 
	   strings.Contains(errStr, "connection reset") ||
	   strings.Contains(errStr, "connection closed") ||
	   strings.Contains(errStr, "transport is closing") ||
	   strings.Contains(errStr, "unavailable") {
		return true
	}
	
	// Timeout errors
	if strings.Contains(errStr, "deadline exceeded") || 
	   strings.Contains(errStr, "context deadline exceeded") {
		return true
	}
	
	// Resource exhaustion (may be temporary)
	if strings.Contains(errStr, "resource exhausted") {
		return true
	}
	
	return false
}
