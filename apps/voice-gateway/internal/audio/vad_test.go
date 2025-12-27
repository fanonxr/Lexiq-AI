package audio

import (
	"testing"
)

func TestVADDetector_ProcessFrame_Speech(t *testing.T) {
	config := &VADConfig{
		EnergyThreshold: 500.0,
		SilenceFrames:   10,
		FrameSize:       160,
	}
	vad := NewVADDetector(config)

	// Create high-energy audio (should be detected as speech)
	samples := make([]int16, 160) // 20ms at 8kHz
	for i := range samples {
		samples[i] = 5000 // High amplitude
	}

	// Process multiple frames
	for i := 0; i < 5; i++ {
		isSpeaking, speechStarted, _ := vad.ProcessFrame(samples)
		if !isSpeaking {
			t.Errorf("Expected speech detection on frame %d", i)
		}
		if i == 0 && !speechStarted {
			t.Error("Expected speech to start on first frame")
		}
	}
}

func TestVADDetector_ProcessFrame_Silence(t *testing.T) {
	config := &VADConfig{
		EnergyThreshold: 500.0,
		SilenceFrames:   10,
		FrameSize:       160,
	}
	vad := NewVADDetector(config)

	// Create low-energy audio (should be detected as silence)
	samples := make([]int16, 160) // 20ms at 8kHz
	for i := range samples {
		samples[i] = 10 // Low amplitude
	}

	// Process multiple frames (should not detect speech)
	for i := 0; i < 15; i++ {
		isSpeaking, _, _ := vad.ProcessFrame(samples)
		if isSpeaking {
			t.Errorf("Expected silence on frame %d", i)
		}
	}
}

func TestVADDetector_ProcessFrame_SpeechToSilence(t *testing.T) {
	config := &VADConfig{
		EnergyThreshold: 500.0,
		SilenceFrames:   10,
		FrameSize:       160,
	}
	vad := NewVADDetector(config)

	// Create high-energy audio
	highSamples := make([]int16, 160)
	for i := range highSamples {
		highSamples[i] = 5000
	}

	// Create low-energy audio
	lowSamples := make([]int16, 160)
	for i := range lowSamples {
		lowSamples[i] = 10
	}

	// Process speech frames
	for i := 0; i < 5; i++ {
		isSpeaking, _, _ := vad.ProcessFrame(highSamples)
		if !isSpeaking {
			t.Errorf("Expected speech detection on frame %d", i)
		}
	}

	// Process silence frames (should eventually mark as non-speech)
	speechEnded := false
	for i := 0; i < 15; i++ {
		_, _, ended := vad.ProcessFrame(lowSamples)
		if ended {
			speechEnded = true
			break
		}
	}

	// After silenceFrames (10) of silence, should mark speech as ended
	if !speechEnded {
		t.Error("Expected speech to end after silence frames")
	}
}

func TestVADDetector_IsSpeaking(t *testing.T) {
	config := &VADConfig{
		EnergyThreshold: 500.0,
		SilenceFrames:   10,
		FrameSize:       160,
	}
	vad := NewVADDetector(config)

	// Initially should be false
	if vad.IsSpeaking() {
		t.Error("Expected initial speech state to be false")
	}

	// Process high-energy audio
	highSamples := make([]int16, 160)
	for i := range highSamples {
		highSamples[i] = 5000
	}

	vad.ProcessFrame(highSamples)
	if !vad.IsSpeaking() {
		t.Error("Expected speech state to be true after processing high-energy audio")
	}
}

func TestVADDetector_Threshold(t *testing.T) {
	// Test with different thresholds
	lowConfig := &VADConfig{
		EnergyThreshold: 100.0,
		SilenceFrames:   10,
		FrameSize:       160,
	}
	lowThreshold := NewVADDetector(lowConfig)

	highConfig := &VADConfig{
		EnergyThreshold: 5000.0,
		SilenceFrames:   10,
		FrameSize:       160,
	}
	highThreshold := NewVADDetector(highConfig)

	// Create medium-energy audio
	samples := make([]int16, 160)
	for i := range samples {
		samples[i] = 1000
	}

	// Low threshold should detect speech
	isSpeaking, _, _ := lowThreshold.ProcessFrame(samples)
	if !isSpeaking {
		t.Error("Expected low threshold to detect speech")
	}

	// High threshold should not detect speech
	isSpeaking, _, _ = highThreshold.ProcessFrame(samples)
	if isSpeaking {
		t.Error("Expected high threshold to not detect speech")
	}
}

func TestVADDetector_Reset(t *testing.T) {
	config := &VADConfig{
		EnergyThreshold: 500.0,
		SilenceFrames:   10,
		FrameSize:       160,
	}
	vad := NewVADDetector(config)

	// Process speech
	highSamples := make([]int16, 160)
	for i := range highSamples {
		highSamples[i] = 5000
	}
	vad.ProcessFrame(highSamples)

	if !vad.IsSpeaking() {
		t.Fatal("Expected speech to be detected")
	}

	// Reset
	vad.Reset()
	if vad.IsSpeaking() {
		t.Error("Expected speech state to be false after reset")
	}
}

func TestDefaultVADConfig(t *testing.T) {
	config := DefaultVADConfig()
	if config.EnergyThreshold != 500.0 {
		t.Errorf("Expected default EnergyThreshold 500.0, got %f", config.EnergyThreshold)
	}
	if config.SilenceFrames != 10 {
		t.Errorf("Expected default SilenceFrames 10, got %d", config.SilenceFrames)
	}
	if config.FrameSize != 160 {
		t.Errorf("Expected default FrameSize 160, got %d", config.FrameSize)
	}
}

func TestCalculateRMS(t *testing.T) {
	// Test with known values
	samples := []int16{1000, -1000, 2000, -2000}
	rms := CalculateRMS(samples)

	// Expected RMS: sqrt((1000^2 + 1000^2 + 2000^2 + 2000^2) / 4)
	expected := 1581.14 // Approximate
	tolerance := 1.0

	if rms < expected-tolerance || rms > expected+tolerance {
		t.Errorf("Expected RMS around %.2f, got %.2f", expected, rms)
	}
}

func TestDetectSilence(t *testing.T) {
	// High energy samples
	highSamples := []int16{5000, 5000, 5000}
	if DetectSilence(highSamples, 1000.0) {
		t.Error("Expected high energy samples to not be silence")
	}

	// Low energy samples
	lowSamples := []int16{10, 10, 10}
	if !DetectSilence(lowSamples, 1000.0) {
		t.Error("Expected low energy samples to be silence")
	}
}

