"""File-backed job state: stages, events and outputs for one assessment run.

Each job lives in data/jobs/{job_id}/ with job.json (state) and events.jsonl
(append-only event log). The API only reads these files, so the pipeline can
run in a worker thread without shared in-memory state.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings

JOB_ID_RE = re.compile(r"^[a-z0-9]{12}$")

STAGE_PENDING = "pending"
STAGE_RUNNING = "running"
STAGE_DONE = "done"
STAGE_SKIPPED = "skipped"
STAGE_FAILED = "failed"


def read_json_retry(path: Path) -> dict:
    """Read a JSON file that another thread may be replacing at this moment."""
    for attempt in range(20):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (PermissionError, json.JSONDecodeError):
            time.sleep(0.02 * (attempt + 1))
    return json.loads(path.read_text(encoding="utf-8"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_valid_job_id(job_id: str) -> bool:
    return bool(JOB_ID_RE.fullmatch(job_id))


def job_dir(job_id: str) -> Path:
    if not is_valid_job_id(job_id):
        raise ValueError(f"invalid job id: {job_id!r}")
    return settings.jobs_dir / job_id


class Job:
    """Mutable job state; every mutation is persisted immediately."""

    def __init__(self, state: dict[str, Any]):
        self.state = state
        self._lock = threading.Lock()

    # -- construction / loading ------------------------------------------
    @classmethod
    def create(cls, name: str, mode: str, stages: list[dict[str, str]], options: dict) -> "Job":
        job_id = uuid.uuid4().hex[:12]
        state = {
            "id": job_id,
            "name": name,
            "mode": mode,
            "created_at": now_iso(),
            "finished_at": None,
            "status": "queued",
            "options": options,
            "aoi": None,
            "stages": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "description": s.get("description", ""),
                    "status": STAGE_PENDING,
                    "started_at": None,
                    "finished_at": None,
                    "summary": None,
                    "metrics": {},
                    "preview": None,
                }
                for s in stages
            ],
            "outputs": {"layers": {}, "rasters": {}, "exports": {}},
            "summary": {},
            "provenance": [],
            "event_counts": {"info": 0, "warning": 0, "error": 0},
        }
        job = cls(state)
        job.dir.mkdir(parents=True, exist_ok=True)
        job.save()
        return job

    @classmethod
    def load(cls, job_id: str) -> "Job":
        path = job_dir(job_id) / "job.json"
        if not path.exists():
            raise FileNotFoundError(job_id)
        return cls(read_json_retry(path))

    # -- properties --------------------------------------------------------
    @property
    def id(self) -> str:
        return self.state["id"]

    @property
    def dir(self) -> Path:
        return job_dir(self.id)

    def path(self, name: str) -> Path:
        return self.dir / name

    # -- persistence ---------------------------------------------------------
    def save(self) -> None:
        tmp = self.dir / "job.json.tmp"
        tmp.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        # On Windows the replace fails while an API request has job.json open.
        for attempt in range(50):
            try:
                tmp.replace(self.dir / "job.json")
                return
            except PermissionError:
                time.sleep(0.02 * (attempt + 1))
        tmp.replace(self.dir / "job.json")

    def _stage(self, stage_id: str) -> dict:
        for s in self.state["stages"]:
            if s["id"] == stage_id:
                return s
        raise KeyError(stage_id)

    # -- lifecycle -------------------------------------------------------------
    def set_status(self, status: str) -> None:
        with self._lock:
            self.state["status"] = status
            if status in ("completed", "failed"):
                self.state["finished_at"] = now_iso()
            self.save()

    def start_stage(self, stage_id: str) -> None:
        with self._lock:
            s = self._stage(stage_id)
            s["status"] = STAGE_RUNNING
            s["started_at"] = now_iso()
            self.state["status"] = "running"
            self.state["current_stage"] = stage_id
            self.save()

    def finish_stage(
        self,
        stage_id: str,
        summary: str,
        metrics: dict | None = None,
        preview: str | None = None,
        status: str = STAGE_DONE,
    ) -> None:
        with self._lock:
            s = self._stage(stage_id)
            s["status"] = status
            s["finished_at"] = now_iso()
            s["summary"] = summary
            s["metrics"] = metrics or {}
            s["preview"] = preview
            self.save()

    def skip_stage(self, stage_id: str, reason: str) -> None:
        self.finish_stage(stage_id, reason, status=STAGE_SKIPPED)

    def fail_stage(self, stage_id: str, reason: str) -> None:
        self.finish_stage(stage_id, reason, status=STAGE_FAILED)

    # -- events ----------------------------------------------------------------
    def event(
        self,
        level: str,
        code: str,
        message: str,
        action: str | None = None,
        stage: str | None = None,
        data: dict | None = None,
    ) -> None:
        """Record a notable event. level: info | warning | error."""
        rec = {
            "time": now_iso(),
            "level": level,
            "code": code,
            "stage": stage or self.state.get("current_stage"),
            "message": message,
            "action": action,
            "data": data or {},
        }
        with self._lock:
            with (self.dir / "events.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            self.state["event_counts"][level] = self.state["event_counts"].get(level, 0) + 1
            self.save()

    def events(self) -> list[dict]:
        path = self.dir / "events.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    # -- outputs -----------------------------------------------------------------
    def set_layer(self, name: str, filename: str, label: str) -> None:
        with self._lock:
            self.state["outputs"]["layers"][name] = {"file": filename, "label": label}
            self.save()

    def set_raster(self, name: str, filename: str, corners: list, label: str, legend: dict | None = None) -> None:
        with self._lock:
            self.state["outputs"]["rasters"][name] = {
                "file": filename,
                "corners": corners,
                "label": label,
                "legend": legend,
            }
            self.save()

    def set_export(self, fmt: str, filename: str, label: str) -> None:
        with self._lock:
            self.state["outputs"]["exports"][fmt] = {"file": filename, "label": label}
            self.save()

    def update(self, key: str, value: Any) -> None:
        with self._lock:
            self.state[key] = value
            self.save()

    def add_provenance(self, record: dict) -> None:
        with self._lock:
            self.state["provenance"].append(record)
            self.save()


def list_jobs() -> list[dict]:
    if not settings.jobs_dir.exists():
        return []
    jobs = []
    for d in settings.jobs_dir.iterdir():
        f = d / "job.json"
        if d.is_dir() and is_valid_job_id(d.name) and f.exists():
            s = read_json_retry(f)
            jobs.append({
                k: s.get(k)
                for k in ("id", "name", "mode", "status", "created_at", "finished_at", "summary", "aoi", "event_counts")
            })
    return sorted(jobs, key=lambda j: j["created_at"], reverse=True)
