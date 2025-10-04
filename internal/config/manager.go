package config

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
	"gopkg.in/yaml.v3"
)

// Manager keeps YAML configs in memory and hot-reloads them when files change.
type Manager struct {
	mu       sync.RWMutex
	configs  map[string]*Config
	dir      string
	watcher  *fsnotify.Watcher
	debounce time.Duration
}

func NewManager(dir string) (*Manager, error) {
	m := &Manager{
		configs:  make(map[string]*Config),
		dir:      dir,
		debounce: 300 * time.Millisecond,
	}

	if err := m.loadAllRecursive(); err != nil {
		return nil, err
	}

	go m.watchLoop()
	return m, nil
}

// loadAllRecursive walks the directory tree and loads all YAML files.
func (m *Manager) loadAllRecursive() error {
	return filepath.WalkDir(m.dir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if d.IsDir() {
			return nil
		}

		ext := filepath.Ext(d.Name())
		if ext != ".yaml" && ext != ".yml" {
			return nil
		}

		if err := m.loadFile(path); err != nil {
			fmt.Printf("❌ failed to load %s: %v\n", path, err)
		}
		return nil
	})
}

func (m *Manager) loadFile(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return fmt.Errorf("invalid YAML in %s: %v", path, err)
	}
	if cfg.Project == "" {
		return fmt.Errorf("missing 'project' in %s", path)
	}

	m.mu.Lock()
	m.configs[cfg.Project] = &cfg
	m.mu.Unlock()
	fmt.Printf("🔄 loaded config: %s (%s)\n", cfg.Project, path)
	return nil
}

func (m *Manager) removeFile(path string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	for name, cfg := range m.configs {
		// If multiple configs share names (bad idea), we remove any matching filename
		if filepath.Base(path) == fmt.Sprintf("%s.yaml", cfg.Project) ||
			filepath.Base(path) == fmt.Sprintf("%s.yml", cfg.Project) {
			delete(m.configs, name)
			fmt.Printf("🗑️ removed config: %s (%s)\n", name, path)
			return
		}
	}
	fmt.Printf("🗑️ removed unknown file: %s\n", path)
}

func (m *Manager) Get(project string) *Config {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.configs[project]
}

func (m *Manager) watchLoop() {
	w, err := fsnotify.NewWatcher()
	if err != nil {
		fmt.Printf("fsnotify error: %v\n", err)
		return
	}
	m.watcher = w
	defer w.Close()

	// Watch all subdirectories recursively
	filepath.WalkDir(m.dir, func(path string, d os.DirEntry, err error) error {
		if err == nil && d.IsDir() {
			_ = w.Add(path)
		}
		return nil
	})

	var lastEvent time.Time
	for {
		select {
		case event, ok := <-w.Events:
			if !ok {
				return
			}
			if time.Since(lastEvent) < m.debounce {
				continue
			}
			lastEvent = time.Now()

			switch {
			case event.Op&(fsnotify.Create|fsnotify.Write|fsnotify.Rename) != 0:
				info, err := os.Stat(event.Name)
				if err == nil && info.IsDir() {
					// Add new folder to watcher
					_ = w.Add(event.Name)
					fmt.Printf("📁 new directory added to watch: %s\n", event.Name)
				} else {
					fmt.Printf("📂 detected change: %s\n", event.Name)
					_ = m.loadFile(event.Name)
				}

			case event.Op&fsnotify.Remove != 0:
				m.removeFile(event.Name)
			}

		case err, ok := <-w.Errors:
			if !ok {
				return
			}
			fmt.Printf("watch error: %v\n", err)
		}
	}
}
