module github.com/willitbemax/data_scheduler

go 1.24

require (
    go.mongodb.org/mongo-driver v1.17.1
    github.com/redis/go-redis/v9 v9.7.0
    google.golang.org/grpc v1.68.1
    google.golang.org/protobuf v1.35.2
)

replace github.com/willitbemax/protobuf => ../protobuf
