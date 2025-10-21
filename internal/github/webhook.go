package github

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
)

// WebhookPayload represents a generic push event from GitHub.
type WebhookPayload struct {
	Ref        string `json:"ref"`
	Before     string `json:"before"`
	After      string `json:"after"`
	Repository struct {
		Name  string `json:"name"`
		Owner struct {
			Name string `json:"name"`
		} `json:"owner"`
	} `json:"repository"`
}

// VerifySignature validates the HMAC SHA256 signature from GitHub.
func VerifySignature(secret string, r *http.Request, body []byte) bool {
	sig := r.Header.Get("X-Hub-Signature-256")
	if sig == "" {
		return false
	}
	expected := computeHMAC(secret, body)
	return hmac.Equal([]byte(sig), []byte("sha256="+expected))
}

func computeHMAC(secret string, body []byte) string {
	h := hmac.New(sha256.New, []byte(secret))
	h.Write(body)
	return hex.EncodeToString(h.Sum(nil))
}

// ParseWebhook parses and validates a GitHub webhook request.
func ParseWebhook(secret string, r *http.Request) (*WebhookPayload, error) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		return nil, err
	}

	if secret != "" && !VerifySignature(secret, r, body) {
		return nil, fmt.Errorf("invalid GitHub signature")
	}

	var payload WebhookPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		return nil, fmt.Errorf("invalid JSON payload: %v", err)
	}

	return &payload, nil
}

// ExtractBranch returns the branch name (e.g. "main") from refs/heads/main
func ExtractBranch(ref string) string {
	return strings.TrimPrefix(ref, "refs/heads/")
}
