package main

import (
	"JSCP/internal/config"
	"fmt"
	"time"
)

func main() {
	manager, err := config.NewManager("./configs")
	if err != nil {
		panic(err)
	}

	for {
		cfg := manager.Get("example_project")
		if cfg != nil {
			fmt.Printf("Currently loaded pipelines: %v\n", cfg.Pipelines[0].Name)
		}
		time.Sleep(5 * time.Second)
	}
}
