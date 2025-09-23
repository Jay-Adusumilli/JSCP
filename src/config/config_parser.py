from dataclasses import dataclass, field
from watchdog.events import FileSystemEventHandler
from typing import Any, Dict
import os
import yaml
import logging
import time

from logger.logger import Logs


@dataclass
class Config:
    repo: str = None
    version: int = None
    content: Dict[str, Any] = field(default_factory=dict)

class ConfigManager:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.configs = {}
        self.logger = logging.getLogger(__name__)
        self._load_configs()

    def _load_configs(self):
        for filename in os.listdir(self.folder_path):
            if filename.endswith('.yaml'):
                file_path = os.path.join(self.folder_path, filename)
                with open(file_path, 'r') as file:
                    content = yaml.safe_load(file)
                    repo = content.get('repo', os.path.splitext(filename)[0])
                    version = content.get('version')

                    if repo in self.configs:
                        existing_config = self.configs[repo]
                        if version is not None and existing_config.version is not None:
                            if version > existing_config.version:
                                self.configs[repo] = Config(repo=repo, version=version, content=content)
                            elif version == existing_config.version:
                                self.logger.warning(f"Duplicate config detected for repo '{repo}' with the same version: {version}")
                        else:
                            self.logger.warning(f"Duplicate config detected for repo '{repo}' without version information.")
                    else:
                        self.configs[repo] = Config(repo=repo, version=version, content=content)

    def get_configs(self) -> Dict[str, Config]:
        return self.configs

    def __getitem__(self, repo: str) -> Config:
        return self.configs.get(repo)


class _ConfigReloadHandler(FileSystemEventHandler):
    def __init__(self, reload_fn, debounce_sec: float = 0.3):
        super().__init__()
        self._reload_fn = reload_fn
        self._last = 0.0
        self._debounce = debounce_sec

    def on_any_event(self, event):
        if event.is_directory:
            return
        now = time.monotonic()
        if (now - self._last) < self._debounce:
            return
        self._last = now
        try:
            self._reload_fn()
        except Exception as e:
            Logs.error(f"Auto-reload failed: {e}")
