package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/gin-gonic/gin"
	"github.com/willitbemax/content_api/internal/config"
	grpcclient "github.com/willitbemax/content_api/internal/grpc"
	"github.com/willitbemax/content_api/internal/handlers"
	"github.com/willitbemax/content_api/internal/middleware"
)

func main() {
	cfg := config.Load()
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	grpcClient, err := grpcclient.NewClient(cfg.DataSchedulerURI)
	if err != nil {
		log.Fatalf("Failed to connect to data_scheduler: %v", err)
	}
	defer grpcClient.Close()

	if cfg.LogLevel == "DEBUG" {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()

	router.Use(middleware.CORS())
	router.Use(middleware.ErrorHandler())
	router.Use(middleware.RequestLogger())

	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "healthy",
			"service": "content_api",
		})
	})

	seasonsHandler := handlers.NewSeasonsHandler(grpcClient)
	roundsHandler := handlers.NewRoundsHandler(grpcClient)

	router.GET("/seasons", seasonsHandler.GetSeasons)
	router.GET("/seasons/:year/rounds", roundsHandler.GetRounds)
	router.GET("/seasons/:year/rounds/:round_id", roundsHandler.GetRound)

	log.Printf("Starting content_api HTTP server on port %s", cfg.HTTPPort)

	go func() {
		if err := router.Run(":" + cfg.HTTPPort); err != nil {
			log.Fatalf("Server failed to start: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down content_api...")
}
