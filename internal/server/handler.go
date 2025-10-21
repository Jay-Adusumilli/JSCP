package server

import (
	"JSCP/internal/github"
	"fmt"
	"net/http"
)

const githubSecret = "your_webhook_secret"

func (s *Server) handleWebhook(w http.ResponseWriter, r *http.Request) {
	payload, err := github.ParseWebhook(githubSecret, r)
	if err != nil {
		http.Error(w, err.Error(), http.StatusForbidden)
		return
	}

	project := payload.Repository.Name
	branch := github.ExtractBranch(payload.Ref)

	cfg := s.cfgManager.Get(project)
	if cfg == nil {
		http.Error(w, fmt.Sprintf("config not found for project: %s", project), http.StatusNotFound)
		return
	}

	fmt.Printf("📬 Webhook: project=%s branch=%s sha=%s\n", project, branch, payload.After)

	// Example GitHub status update
	client := github.NewClient(cfg.GithubToken)
	_ = client.SetStatus(
		payload.Repository.Owner.Name,
		payload.Repository.Name,
		payload.After,
		github.CommitStatus{
			State:       "pending",
			Description: "JSCP pipeline started",
			Context:     "JSCP",
		},
	)

	w.WriteHeader(http.StatusOK)
	w.Write([]byte("webhook processed"))
}

// handleHealth responds with a simple "ok" to indicate the server is running.
func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}
