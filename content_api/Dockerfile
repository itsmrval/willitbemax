FROM golang:1.24-alpine AS proto-builder

RUN apk add --no-cache protobuf
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
RUN go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

WORKDIR /app/protobuf

COPY protobuf/*.proto ./
COPY protobuf/go.mod ./

RUN mkdir -p gen/go
RUN protoc --go_out=gen/go --go-grpc_out=gen/go \
    --go_opt=paths=source_relative \
    --go-grpc_opt=paths=source_relative \
    *.proto

FROM golang:1.24-alpine AS app-builder

WORKDIR /app/content_api

COPY --from=proto-builder /app/protobuf /app/protobuf

COPY content_api/go.mod ./
COPY content_api/cmd ./cmd
COPY content_api/internal ./internal

RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server ./cmd/main.go

FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

COPY --from=app-builder /app/server .

EXPOSE 8080

CMD ["./server"]
