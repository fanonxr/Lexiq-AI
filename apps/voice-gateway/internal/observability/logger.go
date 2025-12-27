package observability

import (
	"os"
	"time"

	"github.com/google/uuid"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

var (
	globalLogger zerolog.Logger
	initialized  bool
)

// InitLogger initializes the global structured logger
func InitLogger(level string, pretty bool) {
	if initialized {
		return
	}

	// Set log level
	logLevel := zerolog.InfoLevel
	switch level {
	case "debug":
		logLevel = zerolog.DebugLevel
	case "info":
		logLevel = zerolog.InfoLevel
	case "warn":
		logLevel = zerolog.WarnLevel
	case "error":
		logLevel = zerolog.ErrorLevel
	case "fatal":
		logLevel = zerolog.FatalLevel
	case "panic":
		logLevel = zerolog.PanicLevel
	default:
		logLevel = zerolog.InfoLevel
	}

	zerolog.SetGlobalLevel(logLevel)

	// Configure output
	if pretty {
		// Pretty console output for development
		output := zerolog.ConsoleWriter{
			Out:        os.Stdout,
			TimeFormat: time.RFC3339,
		}
		globalLogger = zerolog.New(output).With().Timestamp().Logger()
	} else {
		// JSON output for production
		globalLogger = zerolog.New(os.Stdout).With().Timestamp().Logger()
	}

	// Set as global logger
	log.Logger = globalLogger

	initialized = true
}

// GetLogger returns the global logger
func GetLogger() zerolog.Logger {
	if !initialized {
		// Initialize with defaults if not already initialized
		InitLogger("info", false)
	}
	return globalLogger
}

// WithContext creates a logger with context fields
func WithContext(fields map[string]interface{}) zerolog.Logger {
	logger := GetLogger()
	for k, v := range fields {
		logger = logger.With().Interface(k, v).Logger()
	}
	return logger
}

// WithCorrelationID creates a logger with a correlation ID
func WithCorrelationID(correlationID string) zerolog.Logger {
	if correlationID == "" {
		correlationID = uuid.New().String()
	}
	return GetLogger().With().Str("correlation_id", correlationID).Logger()
}

// NewCorrelationID generates a new correlation ID
func NewCorrelationID() string {
	return uuid.New().String()
}

