package audio

// VADConfig holds configuration for Voice Activity Detection
type VADConfig struct {
	EnergyThreshold float64 // RMS energy threshold for speech detection
	SilenceFrames   int     // Number of consecutive silence frames to mark as end of speech
	FrameSize       int     // Number of samples per frame (typically 160 for 8kHz = 20ms)
}

// DefaultVADConfig returns a default VAD configuration
func DefaultVADConfig() *VADConfig {
	return &VADConfig{
		EnergyThreshold: 500.0, // Adjust based on testing
		SilenceFrames:   10,    // 200ms of silence (10 frames * 20ms)
		FrameSize:       160,   // 20ms at 8kHz (8000 * 0.02 = 160)
	}
}

// VADDetector performs Voice Activity Detection
type VADDetector struct {
	config         *VADConfig
	silenceCounter int
	isSpeaking     bool
}

// NewVADDetector creates a new VAD detector
func NewVADDetector(config *VADConfig) *VADDetector {
	if config == nil {
		config = DefaultVADConfig()
	}
	return &VADDetector{
		config:         config,
		silenceCounter: 0,
		isSpeaking:     false,
	}
}

// ProcessFrame processes an audio frame and returns whether speech is detected
// Returns: (isSpeaking, speechStarted, speechEnded)
func (v *VADDetector) ProcessFrame(samples []int16) (bool, bool, bool) {
	// Calculate RMS energy for this frame
	rms := CalculateRMS(samples)

	// Determine if this frame contains speech
	frameHasSpeech := rms > v.config.EnergyThreshold

	var speechStarted, speechEnded bool

	if frameHasSpeech {
		// Reset silence counter
		v.silenceCounter = 0

		// Check if speech just started
		if !v.isSpeaking {
			speechStarted = true
			v.isSpeaking = true
		}
	} else {
		// Increment silence counter
		v.silenceCounter++

		// Check if we've had enough silence to mark speech as ended
		if v.isSpeaking && v.silenceCounter >= v.config.SilenceFrames {
			speechEnded = true
			v.isSpeaking = false
			v.silenceCounter = 0
		}
	}

	return v.isSpeaking, speechStarted, speechEnded
}

// Reset resets the VAD detector state
func (v *VADDetector) Reset() {
	v.silenceCounter = 0
	v.isSpeaking = false
}

// IsSpeaking returns whether speech is currently detected
func (v *VADDetector) IsSpeaking() bool {
	return v.isSpeaking
}

// CalculateEnergy calculates the energy (RMS) of audio samples
// This is a helper function that can be used independently
func CalculateEnergy(samples []int16) float64 {
	return CalculateRMS(samples)
}

// DetectSilence detects if audio samples represent silence
// Uses a simple energy threshold
func DetectSilence(samples []int16, threshold float64) bool {
	return CalculateRMS(samples) < threshold
}

