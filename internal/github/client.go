package github

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
)

type Client struct {
	Token string
}

func NewClient(token string) *Client {
	return &Client{Token: token}
}

// CommitStatus represents a GitHub status update payload.
type CommitStatus struct {
	State       string `json:"state"`       // "pending", "success", "failure", "error"
	TargetURL   string `json:"target_url"`  // optional link to logs
	Description string `json:"description"` // short summary
	Context     string `json:"context"`     // e.g. "JSCP"
}

// SetStatus updates the commit status for a repo+SHA.
func (c *Client) SetStatus(owner, repo, sha string, status CommitStatus) error {
	url := fmt.Sprintf("https://api.github.com/repos/%s/%s/statuses/%s", owner, repo, sha)

	data, err := json.Marshal(status)
	if err != nil {
		return err
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(data))
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.Token)
	req.Header.Set("Accept", "application/vnd.github+json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return fmt.Errorf("GitHub API returned %d", resp.StatusCode)
	}

	return nil
}
