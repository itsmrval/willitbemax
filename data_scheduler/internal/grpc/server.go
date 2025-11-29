package grpc

import (
	"context"

	"github.com/willitbemax/data_scheduler/internal/cache"
	"github.com/willitbemax/data_scheduler/internal/database"
	"github.com/willitbemax/data_scheduler/internal/handlers"
	pb "github.com/willitbemax/protobuf/gen/go"
)

type DataSchedulerServer struct {
	pb.UnimplementedDataSchedulerServiceServer
	seasonsHandler *handlers.SeasonsHandler
}

func NewDataSchedulerServer(db *database.MongoDB, cache *cache.RedisClient) *DataSchedulerServer {
	return &DataSchedulerServer{
		seasonsHandler: handlers.NewSeasonsHandler(db, cache),
	}
}

func (s *DataSchedulerServer) WriteSeasons(ctx context.Context, req *pb.SeasonsData) (*pb.WriteResponse, error) {
	return s.seasonsHandler.WriteSeasons(ctx, req)
}

func (s *DataSchedulerServer) GetSeasons(ctx context.Context, req *pb.SeasonsFilter) (*pb.SeasonsResponse, error) {
	return s.seasonsHandler.GetSeasons(ctx, req)
}
