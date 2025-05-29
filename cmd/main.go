package main

import (
	"fmt"
	"io"
	"log"
	"net"
	"strconv"

	"context"

	"log/slog"

	corev3 "github.com/envoyproxy/go-control-plane/envoy/config/core/v3"
	extprocv3 "github.com/envoyproxy/go-control-plane/envoy/service/ext_proc/v3"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/status"
)

type Server struct {
}

func (server *Server) Process(srv extprocv3.ExternalProcessor_ProcessServer) error {
	slog.Info("GRPC CALL RECEIVED AT EXT_PROC SERVICE") // Log this immediately
	ctx := srv.Context()
	sendResponse := func(resp *extprocv3.ProcessingResponse) {
		if err := srv.Send(resp); err != nil {
			slog.Warn(fmt.Sprintf("send error %v", err))
		}
	}
	handleCount := 0

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		req, err := srv.Recv()

		if err == io.EOF {
			return nil
		}
		if err != nil {
			return status.Errorf(codes.Unknown, "cannot receive stream request: %v", err)
		}

		switch value := req.Request.(type) {
		case *extprocv3.ProcessingRequest_RequestHeaders:
			slog.Info(fmt.Sprintf("1) Got request headers %v\n", value))
			for _, h := range value.RequestHeaders.GetHeaders().GetHeaders() {
				if h.Key == "x-handle-count" {
					handleCount, _ = strconv.Atoi(string(h.GetRawValue()))
				}
			}
			handleCount += 1

			headerMutation := &extprocv3.HeaderMutation{
				SetHeaders: []*corev3.HeaderValueOption{
					{Header: &corev3.HeaderValue{
						Key:      "x-handle-count",
						RawValue: []byte(strconv.Itoa(handleCount)),
					}},
				},
			}
			resp := &extprocv3.ProcessingResponse{
				Response: &extprocv3.ProcessingResponse_RequestHeaders{
					RequestHeaders: &extprocv3.HeadersResponse{
						Response: &extprocv3.CommonResponse{
							HeaderMutation: headerMutation,
						},
					},
				},
			}
			sendResponse(resp)
			break
		case *extprocv3.ProcessingRequest_RequestBody:
			slog.Info(fmt.Sprintf("2) Got a request body %v\n", value))
			slog.Info(fmt.Sprintf("Handle count is %d\n", handleCount))
			body := []byte(fmt.Sprintf("handled: %d", handleCount))

			headerMutation := &extprocv3.HeaderMutation{
				SetHeaders: []*corev3.HeaderValueOption{
					{Header: &corev3.HeaderValue{
						Key:      "Content-Length",
						RawValue: []byte(strconv.Itoa(len(body))),
					}},
				},
			}
			var bodyMutation *extprocv3.BodyMutation
			// Don't mutate in router ext proc
			if handleCount > 1 {
				bodyMutation = &extprocv3.BodyMutation{
					Mutation: &extprocv3.BodyMutation_Body{Body: body},
				}
			}
			resp := &extprocv3.ProcessingResponse{
				Response: &extprocv3.ProcessingResponse_RequestBody{
					RequestBody: &extprocv3.BodyResponse{
						Response: &extprocv3.CommonResponse{
							HeaderMutation: headerMutation,
							BodyMutation:   bodyMutation,
						},
					},
				},
			}
			sendResponse(resp)
			break
		case *extprocv3.ProcessingRequest_ResponseHeaders:
			slog.Info(fmt.Sprintf("3) Got response headers %v\n", value))
			resp := &extprocv3.ProcessingResponse{
				Response: &extprocv3.ProcessingResponse_ResponseHeaders{},
			}
			sendResponse(resp)
			break
		case *extprocv3.ProcessingRequest_ResponseBody:
			slog.Info(fmt.Sprintf("4) Got a response body %v\n", value))
			resp := &extprocv3.ProcessingResponse{
				Response: &extprocv3.ProcessingResponse_ResponseBody{},
			}
			sendResponse(resp)
			break
		case *extprocv3.ProcessingRequest_RequestTrailers:
			slog.Info(fmt.Sprintf("5) Got request trailers %v\n", value))
			resp := &extprocv3.ProcessingResponse{
				Response: &extprocv3.ProcessingResponse_RequestTrailers{},
			}
			sendResponse(resp)
			break
		case *extprocv3.ProcessingRequest_ResponseTrailers:
			slog.Info(fmt.Sprintf("6) Got response trailers %v\n", value))
			resp := &extprocv3.ProcessingResponse{
				Response: &extprocv3.ProcessingResponse_ResponseTrailers{},
			}
			sendResponse(resp)
			break
		default:
			slog.Warn(fmt.Sprintf("Unknown Request type %v\n", value))
		}
	}
}

// Check implements [grpc_health_v1.HealthServer].
func (s *Server) Check(context.Context, *grpc_health_v1.HealthCheckRequest) (*grpc_health_v1.HealthCheckResponse, error) {
	return &grpc_health_v1.HealthCheckResponse{Status: grpc_health_v1.HealthCheckResponse_SERVING}, nil
}

// Watch implements [grpc_health_v1.HealthServer].
func (s *Server) Watch(*grpc_health_v1.HealthCheckRequest, grpc_health_v1.Health_WatchServer) error {
	return status.Error(codes.Unimplemented, "Watch is not implemented")
}

// Watch implements [grpc_health_v1.HealthServer].
func (s *Server) List(context.Context, *grpc_health_v1.HealthListRequest) (*grpc_health_v1.HealthListResponse, error) {
	return &grpc_health_v1.HealthListResponse{}, nil
}

func main() {
	grpcAddress := ":18080"
	tcpListener, err := net.Listen("tcp", grpcAddress)
	if err != nil {
		log.Fatal(fmt.Sprintf("Failed to listen on %s: %v", grpcAddress, err))
	}
	opts := []grpc.ServerOption{grpc.MaxConcurrentStreams(1000)}
	grpcServer := grpc.NewServer(opts...)
	server := Server{}
	extprocv3.RegisterExternalProcessorServer(grpcServer, &server)
	grpc_health_v1.RegisterHealthServer(grpcServer, &server)
	slog.Info(fmt.Sprintf("Starting gRPC server on address %s", grpcAddress))
	grpcServer.Serve(tcpListener)
}
