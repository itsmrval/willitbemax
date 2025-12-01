package grpc

import (
	"context"
	"fmt"
	"log"
	"time"

	pb "github.com/willitbemax/protobuf/gen/go"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type Client struct {
	conn   *grpc.ClientConn
	client pb.DataSchedulerServiceClient
}

func NewClient(uri string) (*Client, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(
		ctx,
		uri,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to data_scheduler: %w", err)
	}

	client := pb.NewDataSchedulerServiceClient(conn)
	log.Printf("Connected to data_scheduler at %s", uri)

	return &Client{
		conn:   conn,
		client: client,
	}, nil
}

func (c *Client) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

func (c *Client) GetSeasons(ctx context.Context, filter *pb.SeasonsFilter) (*pb.SeasonsResponse, error) {
	return c.client.GetSeasons(ctx, filter)
}
