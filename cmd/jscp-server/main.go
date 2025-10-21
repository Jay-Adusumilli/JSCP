package main

import (
	"JSCP/internal/config"
	"JSCP/internal/server"
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	// --- 1️⃣ Load configs ---
	fmt.Println("📂 Loading configs...")
	cfgManager, err := config.NewManager("./configs")
	if err != nil {
		fmt.Println("❌ Failed to load configs:", err)
		os.Exit(1)
	}

	// --- 2️⃣ Start HTTP server ---
	srv := server.New(cfgManager)
	go func() {
		if err := srv.Start(); err != nil {
			fmt.Println("❌ Server error:", err)
		}
	}()

	fmt.Println("🚀 JSCP Go server running on :8080")
	fmt.Println("   → Health check:  curl http://localhost:8080/healthz")
	fmt.Println("   → Webhook test:  curl -X POST http://localhost:8080/webhook -d '{\"repository\":{\"name\":\"example_project\"},\"ref\":\"refs/heads/test\"}' -H 'Content-Type: application/json'")

	// --- 3️⃣ Graceful shutdown ---
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
	<-sigs

	fmt.Println("🛑 Shutting down gracefully...")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		fmt.Println("⚠️ Server shutdown error:", err)
	} else {
		fmt.Println("✅ Server stopped cleanly.")
	}
}
