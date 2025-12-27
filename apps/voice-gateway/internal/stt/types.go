package stt

// TranscriptionResult represents a transcription result from Deepgram
type TranscriptionResult struct {
	// Text is the transcribed text
	Text string
	
	// IsFinal indicates if this is a final transcription (true) or interim (false)
	IsFinal bool
	
	// Confidence is the confidence score (0.0 to 1.0) if available
	Confidence float64
	
	// StartTime is the start time of the utterance in seconds
	StartTime float64
	
	// Duration is the duration of the utterance in seconds
	Duration float64
}

// STTClient is the interface for speech-to-text clients
type STTClient interface {
	// Start begins a new transcription session
	Start() error
	
	// SendAudio sends an audio chunk to the STT service
	SendAudio(audioData []byte) error
	
	// GetTranscription returns the next transcription result
	// Returns nil if no transcription is available yet
	GetTranscription() <-chan *TranscriptionResult
	
	// Stop stops the transcription session
	Stop() error
	
	// Close closes the client and cleans up resources
	Close() error
}

