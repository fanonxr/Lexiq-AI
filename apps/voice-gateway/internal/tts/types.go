package tts

// AudioChunk represents a chunk of audio data ready for streaming
type AudioChunk struct {
	Data     []byte // Raw audio data (PCMU format for Twilio)
	SampleRate int  // Sample rate in Hz (should be 8000 for Twilio)
	Channels   int  // Number of channels (1 for mono)
}

// TTSClient defines the interface for a Text-to-Speech client
type TTSClient interface {
	// Synthesize converts text to audio and streams it
	Synthesize(text string) (<-chan *AudioChunk, error)
	
	// Stop stops any ongoing synthesis
	Stop() error
	
	// Close closes the client and cleans up resources
	Close() error
	
	// IsActive returns whether the client is currently synthesizing
	IsActive() bool
}

