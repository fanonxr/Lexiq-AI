package audio

import (
	"sync"
)

// RingBuffer is a thread-safe ring buffer for audio data
type RingBuffer struct {
	buffer []byte
	size   int
	read   int
	write  int
	mu     sync.RWMutex
}

// NewRingBuffer creates a new ring buffer with the specified size
func NewRingBuffer(size int) *RingBuffer {
	return &RingBuffer{
		buffer: make([]byte, size),
		size:   size,
		read:   0,
		write:  0,
	}
}

// Write writes data to the ring buffer
// Returns the number of bytes written (may be less than len(data) if buffer is full)
func (rb *RingBuffer) Write(data []byte) int {
	rb.mu.Lock()
	defer rb.mu.Unlock()

	written := 0
	for i := 0; i < len(data); i++ {
		// Check if buffer is full
		if (rb.write+1)%rb.size == rb.read {
			break // Buffer full
		}

		rb.buffer[rb.write] = data[i]
		rb.write = (rb.write + 1) % rb.size
		written++
	}

	return written
}

// Read reads data from the ring buffer
// Returns the number of bytes read
func (rb *RingBuffer) Read(data []byte) int {
	rb.mu.Lock()
	defer rb.mu.Unlock()

	read := 0
	for i := 0; i < len(data); i++ {
		// Check if buffer is empty
		if rb.read == rb.write {
			break // Buffer empty
		}

		data[i] = rb.buffer[rb.read]
		rb.read = (rb.read + 1) % rb.size
		read++
	}

	return read
}

// Available returns the number of bytes available to read
func (rb *RingBuffer) Available() int {
	rb.mu.RLock()
	defer rb.mu.RUnlock()

	if rb.write >= rb.read {
		return rb.write - rb.read
	}
	return rb.size - rb.read + rb.write
}

// Space returns the number of bytes available to write
func (rb *RingBuffer) Space() int {
	rb.mu.RLock()
	defer rb.mu.RUnlock()

	return rb.size - rb.Available() - 1 // -1 to prevent full/empty ambiguity
}

// Clear clears the buffer
func (rb *RingBuffer) Clear() {
	rb.mu.Lock()
	defer rb.mu.Unlock()

	rb.read = 0
	rb.write = 0
}

// IsEmpty returns true if the buffer is empty
func (rb *RingBuffer) IsEmpty() bool {
	rb.mu.RLock()
	defer rb.mu.RUnlock()
	return rb.read == rb.write
}

// IsFull returns true if the buffer is full
func (rb *RingBuffer) IsFull() bool {
	rb.mu.RLock()
	defer rb.mu.RUnlock()
	return (rb.write+1)%rb.size == rb.read
}

