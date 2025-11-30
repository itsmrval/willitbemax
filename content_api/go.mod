module github.com/willitbemax/content_api

go 1.24

replace github.com/willitbemax/protobuf => ../protobuf

require (
	github.com/gin-gonic/gin v1.10.0
	github.com/willitbemax/protobuf v0.0.0-00010101000000-000000000000
	google.golang.org/grpc v1.69.2
)
