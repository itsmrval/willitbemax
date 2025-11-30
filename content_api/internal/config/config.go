package config

import "os"

type Config struct {
	HTTPPort           string
	DataSchedulerURI   string
	LogLevel           string
}

func Load() *Config {
	return &Config{
		HTTPPort:         getEnv("HTTP_PORT", "8080"),
		DataSchedulerURI: getEnv("DATA_SCHEDULER_URI", "data_scheduler:50051"),
		LogLevel:         getEnv("LOG_LEVEL", "INFO"),
	}
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
