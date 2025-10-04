package github

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
)

// GitHubWebhook represents a normalized GitHub webhook event.
type GitHubWebhook struct {
	EventType     string                 `json:"event_type"`
	RepoName      *string                `json:"repo_name,omitempty"`
	Ref           *string                `json:"ref,omitempty"`
	CommitSHA     *string                `json:"commit_sha,omitempty"`
	Pusher        *string                `json:"pusher,omitempty"`
	Action        *string                `json:"action,omitempty"`
	BuildRelevant bool                   `json:"build_relevant"`
	Raw           map[string]interface{} `json:"raw,omitempty"`
}

// ToMap returns a map representation of the webhook.
func (g *GitHubWebhook) ToMap() map[string]interface{} {
	return map[string]interface{}{
		"event_type":     g.EventType,
		"repo_name":      g.RepoName,
		"ref":            g.Ref,
		"commit_sha":     g.CommitSHA,
		"pusher":         g.Pusher,
		"action":         g.Action,
		"build_relevant": g.BuildRelevant,
		"raw":            g.Raw,
	}
}

// verifySignature verifies the GitHub webhook signature using HMAC SHA256.
func verifySignature(payloadBody []byte, secretToken, signatureHeader string) error {
	mac := hmac.New(sha256.New, []byte(secretToken))
	mac.Write(payloadBody)
	expected := "sha256=" + hex.EncodeToString(mac.Sum(nil))
	if !hmac.Equal([]byte(expected), []byte(signatureHeader)) {
		return errors.New("signature verification failed")
	}
	return nil
}

// detectEventType detects the build-relevant GitHub event type.
func detectEventType(payload map[string]interface{}) string {
	if _, ok := payload["pull_request"]; ok {
		return "pull_request"
	}
	if _, ok := payload["head_commit"]; ok {
		return "push"
	}
	if _, ok := payload["commits"]; ok {
		return "push"
	}
	if _, ok := payload["release"]; ok {
		return "release"
	}
	if _, ok := payload["workflow_run"]; ok {
		return "workflow_run"
	}
	if _, ok := payload["deployment"]; ok {
		return "deployment"
	}
	return "ignored"
}

// ParseGitHubWebhook parses and verifies GitHub webhook events into a normalized GitHubWebhook.
func ParseGitHubWebhook(payload map[string]interface{}, payloadBody []byte, secretToken, signatureHeader string) (*GitHubWebhook, error) {
	if err := verifySignature(payloadBody, secretToken, signatureHeader); err != nil {
		return nil, err
	}

	eventType := detectEventType(payload)
	buildRelevant := eventType != "ignored"

	if !buildRelevant {
		return &GitHubWebhook{
			EventType:     "ignored",
			BuildRelevant: false,
			Raw:           payload,
		}, nil
	}

	var repoName, ref, commitSHA, pusher, action *string
	if repo, ok := payload["repository"].(map[string]interface{}); ok {
		if name, ok := repo["full_name"].(string); ok {
			repoName = &name
		}
	}

	switch eventType {
	case "push":
		if r, ok := payload["ref"].(string); ok {
			ref = &r
		}
		if hc, ok := payload["head_commit"].(map[string]interface{}); ok {
			if id, ok := hc["id"].(string); ok {
				commitSHA = &id
			}
		}
		if commitSHA == nil {
			if after, ok := payload["after"].(string); ok {
				commitSHA = &after
			}
		}
	case "pull_request":
		if pr, ok := payload["pull_request"].(map[string]interface{}); ok {
			if head, ok := pr["head"].(map[string]interface{}); ok {
				if r, ok := head["ref"].(string); ok {
					ref = &r
				}
				if sha, ok := head["sha"].(string); ok {
					commitSHA = &sha
				}
			}
		}
	case "release":
		if release, ok := payload["release"].(map[string]interface{}); ok {
			if t, ok := release["target_commitish"].(string); ok {
				ref = &t
			}
			if tag, ok := release["tag_name"].(string); ok {
				commitSHA = &tag
			}
		}
	case "workflow_run":
		if workflow, ok := payload["workflow_run"].(map[string]interface{}); ok {
			if branch, ok := workflow["head_branch"].(string); ok {
				ref = &branch
			}
			if sha, ok := workflow["head_sha"].(string); ok {
				commitSHA = &sha
			}
		}
	case "deployment":
		if deploy, ok := payload["deployment"].(map[string]interface{}); ok {
			if r, ok := deploy["ref"].(string); ok {
				ref = &r
			}
			if sha, ok := deploy["sha"].(string); ok {
				commitSHA = &sha
			}
		}
	}

	// Actor/pusher extraction
	if p, ok := payload["pusher"].(map[string]interface{}); ok {
		if name, ok := p["name"].(string); ok {
			pusher = &name
		}
	}
	if pusher == nil {
		if sender, ok := payload["sender"].(map[string]interface{}); ok {
			if login, ok := sender["login"].(string); ok {
				pusher = &login
			}
		}
	}
	if pusher == nil {
		if pr, ok := payload["pull_request"].(map[string]interface{}); ok {
			if user, ok := pr["user"].(map[string]interface{}); ok {
				if login, ok := user["login"].(string); ok {
					pusher = &login
				}
			}
		}
	}
	if pusher == nil {
		if release, ok := payload["release"].(map[string]interface{}); ok {
			if author, ok := release["author"].(map[string]interface{}); ok {
				if login, ok := author["login"].(string); ok {
					pusher = &login
				}
			}
		}
	}
	if pusher == nil {
		if deploy, ok := payload["deployment"].(map[string]interface{}); ok {
			if creator, ok := deploy["creator"].(map[string]interface{}); ok {
				if login, ok := creator["login"].(string); ok {
					pusher = &login
				}
			}
		}
	}
	if pusher == nil {
		if workflow, ok := payload["workflow_run"].(map[string]interface{}); ok {
			if actor, ok := workflow["actor"].(map[string]interface{}); ok {
				if login, ok := actor["login"].(string); ok {
					pusher = &login
				}
			}
		}
	}

	if a, ok := payload["action"].(string); ok {
		action = &a
	}

	return &GitHubWebhook{
		EventType:     eventType,
		RepoName:      repoName,
		Ref:           ref,
		CommitSHA:     commitSHA,
		Pusher:        pusher,
		Action:        action,
		BuildRelevant: buildRelevant,
		Raw:           payload,
	}, nil
}
