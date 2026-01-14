package audio

import (
	"fmt"
	"math"
)

// ConvertPCMToPCMU converts linear PCM audio to G.711 PCMU (μ-law) format
// Input: PCM audio data (16-bit signed integers, little-endian)
// Output: PCMU (μ-law) encoded audio data
func ConvertPCMToPCMU(pcmData []byte, inputSampleRate, outputSampleRate int) ([]byte, error) {
	if len(pcmData) == 0 {
		return nil, fmt.Errorf("empty PCM data")
	}

	// Step 1: Convert bytes to 16-bit signed integers (little-endian)
	// Assuming PCM is 16-bit signed integers
	if len(pcmData)%2 != 0 {
		return nil, fmt.Errorf("PCM data length must be even (16-bit samples)")
	}

	samples := make([]int16, len(pcmData)/2)
	for i := 0; i < len(samples); i++ {
		// Little-endian 16-bit signed integer
		samples[i] = int16(pcmData[i*2]) | int16(pcmData[i*2+1])<<8
	}

	// Step 2: Resample if needed (24kHz → 8kHz)
	if inputSampleRate != outputSampleRate {
		samples = resample(samples, inputSampleRate, outputSampleRate)
	}

	// Step 3: Convert to μ-law (G.711 PCMU)
	pcmuData := make([]byte, len(samples))
	for i, sample := range samples {
		pcmuData[i] = linearToMulaw(sample)
	}

	return pcmuData, nil
}

// resample performs simple linear interpolation resampling
// This is a basic implementation - for production, consider using a library
// with better quality algorithms (e.g., sinc interpolation)
func resample(samples []int16, inputRate, outputRate int) []int16 {
	if inputRate == outputRate {
		return samples
	}

	ratio := float64(outputRate) / float64(inputRate)
	outputLength := int(float64(len(samples)) * ratio)
	output := make([]int16, outputLength)

	for i := 0; i < outputLength; i++ {
		// Calculate source position
		srcPos := float64(i) / ratio

		// Linear interpolation
		idx0 := int(srcPos)
		idx1 := idx0 + 1
		if idx1 >= len(samples) {
			idx1 = len(samples) - 1
		}

		// Interpolate between two samples
		fraction := srcPos - float64(idx0)
		output[i] = int16(float64(samples[idx0])*(1.0-fraction) + float64(samples[idx1])*fraction)
	}

	return output
}

// linearToMulaw converts a 16-bit linear PCM sample to 8-bit μ-law
// G.711 μ-law encoding algorithm (ITU-T G.711 standard)
func linearToMulaw(sample int16) byte {
	const (
		clip = 8159  // Maximum magnitude to clip input (14-bit range)
		bias = 0x21 // Bias value (33 decimal)
	)

	var sign byte
	magnitude := int32(sample)
	
	// Get sign and make magnitude positive
	if sample < 0 {
		sign = 0x80
		magnitude = -magnitude
	} else {
		sign = 0x00
	}

	// Clip magnitude
	if magnitude > clip {
		magnitude = clip
	}

	// Add bias
	magnitude += bias

	// Find segment (exponent) by finding the highest set bit position
	// Segments: 0=33-63, 1=64-127, 2=128-255, 3=256-511, 4=512-1023, 5=1024-2047, 6=2048-4095, 7=4096-8191
	var segment byte
	temp := magnitude
	if temp >= 0x1000 { // 4096
		segment = 7
	} else if temp >= 0x800 { // 2048
		segment = 6
	} else if temp >= 0x400 { // 1024
		segment = 5
	} else if temp >= 0x200 { // 512
		segment = 4
	} else if temp >= 0x100 { // 256
		segment = 3
	} else if temp >= 0x80 { // 128
		segment = 2
	} else if temp >= 0x40 { // 64
		segment = 1
	} else {
		segment = 0
	}

	// Calculate mantissa (4 bits) - shift by (segment + 1)
	mantissa := byte((magnitude >> (segment + 1)) & 0x0F)

	// Combine sign, segment, and mantissa, then invert all bits
	ulawByte := sign | (segment << 4) | mantissa
	return ^ulawByte
}

// ConvertPCMUToPCM converts G.711 PCMU (μ-law) to linear PCM
// This is useful for debugging or if we need to process incoming audio
func ConvertPCMUToPCM(pcmuData []byte) ([]byte, error) {
	if len(pcmuData) == 0 {
		return nil, fmt.Errorf("empty PCMU data")
	}

	pcmData := make([]byte, len(pcmuData)*2) // 16-bit output

	for i, mulawByte := range pcmuData {
		sample := mulawToLinear(mulawByte)
		// Convert to little-endian 16-bit
		pcmData[i*2] = byte(sample)
		pcmData[i*2+1] = byte(sample >> 8)
	}

	return pcmData, nil
}

// mulawToLinear converts an 8-bit μ-law sample to 16-bit linear PCM
func mulawToLinear(mulawByte byte) int16 {
	// Invert all bits first (μ-law uses inverted representation)
	mulawByte = ^mulawByte

	// Extract sign, segment, and mantissa
	sign := mulawByte & 0x80
	segment := int32((mulawByte >> 4) & 0x07)
	mantissa := int32(mulawByte & 0x0F)

	// Reconstruct linear value using the standard formula
	// step = (mantissa << 1 + 33) << segment
	// magnitude = step - bias
	// Or equivalently: step = (mantissa << (segment + 1)) + (33 << segment)
	// magnitude = step - 33
	step := mantissa << (segment + 1)
	step += int32(33) << segment
	magnitude := step - 33 // bias

	// Apply sign
	if sign != 0 {
		return int16(-magnitude)
	}
	return int16(magnitude)
}

// NormalizeAudio normalizes audio samples to prevent clipping
func NormalizeAudio(samples []int16, maxAmplitude int16) []int16 {
	if len(samples) == 0 {
		return samples
	}

	// Find maximum amplitude
	maxVal := int16(0)
	for _, sample := range samples {
		abs := sample
		if abs < 0 {
			abs = -abs
		}
		if abs > maxVal {
			maxVal = abs
		}
	}

	// If already within range, return as-is
	if maxVal <= maxAmplitude {
		return samples
	}

	// Normalize
	ratio := float64(maxAmplitude) / float64(maxVal)
	normalized := make([]int16, len(samples))
	for i, sample := range samples {
		normalized[i] = int16(float64(sample) * ratio)
	}

	return normalized
}

// CalculateRMS calculates the root mean square (RMS) of audio samples
// Useful for detecting audio levels and silence
func CalculateRMS(samples []int16) float64 {
	if len(samples) == 0 {
		return 0.0
	}

	sum := 0.0
	for _, sample := range samples {
		sum += float64(sample) * float64(sample)
	}

	return math.Sqrt(sum / float64(len(samples)))
}

