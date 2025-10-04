package server

import (
	"JSCP/internal/config"
	"context"
	"fmt"
	"net/http"
	_ "time"
)

type Server struct {
	httpServer *http.Server
	cfgManager *config.Manager
}

func New(cfgManager *config.Manager) *Server {
	mux := http.NewServeMux()

	s := &Server{
		httpServer: &http.Server{
			Addr:    ":8080",
			Handler: mux,
		},
		cfgManager: cfgManager,
	}

	mux.HandleFunc("/healthz", s.handleHealth)
	mux.HandleFunc("/jscp", s.handleWebhook)

	return s
}

func (s *Server) Start() error {
	fmt.Println("🚀 Starting server on", s.httpServer.Addr)
	return s.httpServer.ListenAndServe()
}

func (s *Server) Shutdown(ctx context.Context) error {
	fmt.Println("🛑 Shutting down server...")
	return s.httpServer.Shutdown(ctx)
}
