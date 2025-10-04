package config

// Config represents one YAML file.
type Config struct {
	Repo        string     `yaml:"repo"`
	Version     int        `yaml:"version"`
	Project     string     `yaml:"project"`
	RegistryURL string     `yaml:"registry_url"`
	GithubToken string     `yaml:"github_token"`
	Pipelines   []Pipeline `yaml:"pipelines"`
}

type Pipeline struct {
	Name    string  `yaml:"name"`
	Trigger Trigger `yaml:"trigger"`
	Build   Build   `yaml:"build"`
	Deploy  Deploy  `yaml:"deploy"`
}

type Trigger struct {
	Branch string `yaml:"branch"`
	Event  string `yaml:"event"`
}

type Build struct {
	Context    string `yaml:"context"`
	Dockerfile string `yaml:"dockerfile"`
	Tag        string `yaml:"tag"`
}

type Deploy struct {
	Namespace      string `yaml:"namespace"`
	DeploymentName string `yaml:"deployment_name"`
}
