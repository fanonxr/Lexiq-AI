package audio

import (
	"testing"
)

func TestRingBuffer_Write(t *testing.T) {
	rb := NewRingBuffer(10)

	// Write data that fits
	data := []byte{1, 2, 3, 4, 5}
	written := rb.Write(data)
	if written != 5 {
		t.Errorf("Expected to write 5 bytes, got %d", written)
	}
	if rb.Available() != 5 {
		t.Errorf("Expected available 5, got %d", rb.Available())
	}

	// Write more data
	data2 := []byte{6, 7, 8}
	written = rb.Write(data2)
	if written != 3 {
		t.Errorf("Expected to write 3 bytes, got %d", written)
	}
	if rb.Available() != 8 {
		t.Errorf("Expected available 8, got %d", rb.Available())
	}
}

func TestRingBuffer_WriteOverflow(t *testing.T) {
	rb := NewRingBuffer(5)

	// Fill buffer (size-1 to avoid full/empty ambiguity)
	data := []byte{1, 2, 3, 4}
	rb.Write(data)
	if rb.Available() != 4 {
		t.Errorf("Expected available 4, got %d", rb.Available())
	}
	if !rb.IsFull() {
		t.Error("Expected buffer to be full after writing size-1 bytes")
	}

	// Write more (should stop when full - buffer is already full, so 0 bytes written)
	data2 := []byte{5, 6}
	written := rb.Write(data2)
	if written != 0 {
		t.Errorf("Expected to write 0 bytes (buffer already full), got %d", written)
	}
	if rb.Available() != 4 {
		t.Errorf("Expected available 4 after overflow, got %d", rb.Available())
	}
}

func TestRingBuffer_Read(t *testing.T) {
	rb := NewRingBuffer(10)

	// Write data
	data := []byte{1, 2, 3, 4, 5}
	rb.Write(data)

	// Read data
	readBuf := make([]byte, 3)
	read := rb.Read(readBuf)
	if read != 3 {
		t.Errorf("Expected to read 3 bytes, got %d", read)
	}
	if readBuf[0] != 1 || readBuf[1] != 2 || readBuf[2] != 3 {
		t.Errorf("Read incorrect data: %v", readBuf)
	}
	if rb.Available() != 2 {
		t.Errorf("Expected available 2 after read, got %d", rb.Available())
	}
}

func TestRingBuffer_ReadEmpty(t *testing.T) {
	rb := NewRingBuffer(10)

	if !rb.IsEmpty() {
		t.Error("Expected buffer to be empty initially")
	}

	readBuf := make([]byte, 5)
	read := rb.Read(readBuf)
	if read != 0 {
		t.Errorf("Expected to read 0 bytes from empty buffer, got %d", read)
	}
}

func TestRingBuffer_ReadMoreThanAvailable(t *testing.T) {
	rb := NewRingBuffer(10)

	// Write 3 bytes
	data := []byte{1, 2, 3}
	rb.Write(data)

	// Try to read 10 bytes
	readBuf := make([]byte, 10)
	read := rb.Read(readBuf)
	if read != 3 {
		t.Errorf("Expected to read 3 bytes, got %d", read)
	}
	if rb.Available() != 0 {
		t.Errorf("Expected available 0 after reading all, got %d", rb.Available())
	}
	if !rb.IsEmpty() {
		t.Error("Expected buffer to be empty after reading all")
	}
}

func TestRingBuffer_Size(t *testing.T) {
	rb := NewRingBuffer(100)
	// Size is stored in size field (private, but we can test via behavior)
	// Write to capacity-1 to test
	data := make([]byte, 99)
	written := rb.Write(data)
	if written != 99 {
		t.Errorf("Expected to write 99 bytes, got %d", written)
	}
	if !rb.IsFull() {
		t.Error("Expected buffer to be full after writing size-1 bytes")
	}
}

func TestRingBuffer_Reset(t *testing.T) {
	rb := NewRingBuffer(10)

	// Write data
	data := []byte{1, 2, 3, 4, 5}
	rb.Write(data)
	if rb.Available() != 5 {
		t.Errorf("Expected available 5, got %d", rb.Available())
	}

	// Clear
	rb.Clear()
	if rb.Available() != 0 {
		t.Errorf("Expected available 0 after clear, got %d", rb.Available())
	}
	if !rb.IsEmpty() {
		t.Error("Expected buffer to be empty after clear")
	}
	if rb.size != 10 {
		t.Errorf("Expected size 10 after clear, got %d", rb.size)
	}
}

func TestRingBuffer_WrapAround(t *testing.T) {
	rb := NewRingBuffer(5)

	// Fill buffer (size-1 to avoid full/empty ambiguity)
	rb.Write([]byte{1, 2, 3, 4})

	// Read 2 bytes
	readBuf := make([]byte, 2)
	rb.Read(readBuf)

	// Write 2 more bytes (should wrap around)
	rb.Write([]byte{5, 6})
	if rb.Available() != 4 {
		t.Errorf("Expected available 4, got %d", rb.Available())
	}

	// Read all
	readBuf = make([]byte, 4)
	read := rb.Read(readBuf)
	if read != 4 {
		t.Errorf("Expected to read 4 bytes, got %d", read)
	}
	// Should contain 3, 4, 5, 6
	expected := []byte{3, 4, 5, 6}
	for i := 0; i < 4; i++ {
		if readBuf[i] != expected[i] {
			t.Errorf("Expected %d at position %d, got %d", expected[i], i, readBuf[i])
		}
	}
}

