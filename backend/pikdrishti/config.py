"""Runtime settings, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    gee_project: str = os.environ.get("GEE_PROJECT", "")
    data_dir: Path = Path(os.environ.get("PIKDRISHTI_DATA_DIR", REPO_ROOT / "data"))

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def boundaries_dir(self) -> Path:
        return self.data_dir / "boundaries"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


settings = Settings()
