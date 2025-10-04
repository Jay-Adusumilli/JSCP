package server

import (
	"encoding/json"
	"fmt"
	"net/http"
)

type WebhookPayload struct {
	Repository struct {
		Name string `json:"name"`
	} `json:"repository"`
	Ref string `json:"ref"`
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

func (s *Server) handleWebhook(w http.ResponseWriter, r *http.Request) {
	var payload WebhookPayload
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		http.Error(w, "invalid payload", http.StatusBadRequest)
		return
	}

	project := payload.Repository.Name
	cfg := s.cfgManager.Get(project)
	if cfg == nil {
		http.Error(w, fmt.Sprintf("config not found for project: %s", project), http.StatusNotFound)
		return
	}

	fmt.Printf("📬 Received webhook for %s (branch: %s)\n", project, payload.Ref)
	fmt.Printf("⚙️ Using config: %+v\n", cfg)

	w.WriteHeader(http.StatusOK)
	w.Write([]byte("webhook received"))
}
