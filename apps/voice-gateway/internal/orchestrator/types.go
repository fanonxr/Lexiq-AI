package orchestrator

// OrchestratorResponse represents a response from the Orchestrator
type OrchestratorResponse struct {
	TextChunk      string
	ConversationID string
	IsDone         bool
	TotalTokens    int32
	ToolCall       *ToolCall
	ToolResult     *ToolResult
	Error          *Error
}

// ToolCall represents a tool call from the Orchestrator
type ToolCall struct {
	ToolName      string
	ParametersJSON string
	CallID        string
}

// ToolResult represents a tool execution result
type ToolResult struct {
	CallID      string
	ResultJSON  string
	Success     bool
	ErrorMessage string
}

// Error represents an error from the Orchestrator
type Error struct {
	Code        string
	Message     string
	DetailsJSON string
}

