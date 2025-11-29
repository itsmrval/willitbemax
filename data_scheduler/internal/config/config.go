package config

import "os"

type Config struct {
	MongoURI string
	RedisURI string
	GRPCPort string
}

func Load() *Config {
	return &Config{
		MongoURI: getEnv("MONGO_URI", "mongodb://admin:password@mongo:27017"),
		RedisURI: getEnv("REDIS_URI", "redis://redis:6379"),
		GRPCPort: getEnv("GRPC_PORT", "50051"),
	}
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
