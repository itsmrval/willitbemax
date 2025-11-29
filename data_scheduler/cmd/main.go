package main

import (
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"

	"github.com/willitbemax/data_scheduler/internal/cache"
	"github.com/willitbemax/data_scheduler/internal/config"
	"github.com/willitbemax/data_scheduler/internal/database"
	grpcserver "github.com/willitbemax/data_scheduler/internal/grpc"
	pb "github.com/willitbemax/protobuf/gen/go"
	"google.golang.org/grpc"
)

func main() {
	cfg := config.Load()
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	db, err := database.NewMongoDB(cfg.MongoURI)
	if err != nil {
		log.Fatalf("MongoDB connect failed: %v", err)
	}
	defer db.Disconnect()

	redisClient := cache.NewRedisClient(cfg.RedisURI)
	defer redisClient.Close()

	grpcServer := grpc.NewServer()
	dataSchedulerServer := grpcserver.NewDataSchedulerServer(db, redisClient)
	pb.RegisterDataSchedulerServiceServer(grpcServer, dataSchedulerServer)

	listener, err := net.Listen("tcp", fmt.Sprintf(":%s", cfg.GRPCPort))
	if err != nil {
		log.Fatalf("Listen failed: %v", err)
	}

	log.Printf("gRPC server on :%s", cfg.GRPCPort)

	go func() {
		if err := grpcServer.Serve(listener); err != nil {
			log.Fatalf("Serve failed: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down...")
	grpcServer.GracefulStop()
}
