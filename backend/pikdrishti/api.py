"""HTTP API and static web app."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, units
from .config import REPO_ROOT, settings
from .jobs import Job, is_valid_job_id, list_jobs
from .pipelines import DAMAGE_STAGES, DROUGHT_STAGES, run_damage_job, run_drought_job

FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")

app = FastAPI(title="Pik-drishti AI", version="0.1.0", dependencies=[Depends(auth.require_user)])
auth.register(app)
executor = ThreadPoolExecutor(max_workers=2)


@app.on_event("startup")
def recover_interrupted_jobs() -> None:
    for j in list_jobs():
        if j["status"] in ("queued", "running"):
            job = Job.load(j["id"])
            job.event("error", "JOB_INTERRUPTED", "The server restarted while this assessment was running",
                      action="Start the assessment again")
            job.set_status("failed")


class DroughtRequest(BaseModel):
    scope: str = "state"   # "state" (all talukas) or a taluka id (its villages)
    year: int = date.today().year


class DamageRequest(BaseModel):
    taluka: str
    event_date: date


def _load(job_id: str) -> Job:
    if not is_valid_job_id(job_id):
        raise HTTPException(404, "Assessment not found")
    try:
        return Job.load(job_id)
    except FileNotFoundError:
        raise HTTPException(404, "Assessment not found") from None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "gee_project_configured": bool(settings.gee_project)}


@app.get("/api/units/talukas")
def talukas() -> JSONResponse:
    return JSONResponse(units.talukas())


@app.get("/api/units/villages/{taluka_id}")
def villages(taluka_id: str) -> JSONResponse:
    try:
        return JSONResponse(units.villages(taluka_id))
    except KeyError:
        raise HTTPException(404, "Taluka not found") from None


@app.post("/api/jobs/drought")
def create_drought(body: DroughtRequest) -> dict:
    if body.scope != "state":
        t = units.taluka(body.scope)
        if t is None:
            raise HTTPException(404, "Taluka not found")
        name = f"Drought {body.year}: {t['properties']['taluka']} villages ({t['properties']['district']})"
    else:
        name = f"Drought {body.year}: Maharashtra talukas"
    if not 2017 <= body.year <= date.today().year:
        raise HTTPException(400, "Year must be between 2017 and this year")
    job = Job.create(name, "drought", DROUGHT_STAGES, {"scope": body.scope, "year": body.year})
    executor.submit(run_drought_job, job)
    return {"id": job.id}


@app.post("/api/jobs/damage")
def create_damage(body: DamageRequest) -> dict:
    t = units.taluka(body.taluka)
    if t is None:
        raise HTTPException(404, "Taluka not found")
    if not date(2019, 6, 1) <= body.event_date <= date.today():
        raise HTTPException(400, "Event date must be between June 2019 and today")
    name = f"Crop damage {body.event_date:%d %b %Y}: {t['properties']['taluka']} ({t['properties']['district']})"
    job = Job.create(name, "damage", DAMAGE_STAGES, {"taluka": body.taluka, "event_date": str(body.event_date)})
    executor.submit(run_damage_job, job)
    return {"id": job.id}


@app.get("/api/jobs")
def jobs() -> list[dict]:
    return list_jobs()


@app.get("/api/jobs/{job_id}")
def job(job_id: str) -> dict:
    j = _load(job_id)
    results = j.path("results.json")
    return {**j.state, "events": j.events(),
            "results": json.loads(results.read_text(encoding="utf-8")) if results.exists() else None}


@app.get("/api/jobs/{job_id}/files/{filename}")
def job_file(job_id: str, filename: str, download: bool = False):
    j = _load(job_id)
    out = j.state["outputs"]
    allowed = {v["file"] for group in out.values() for v in group.values()}
    if not FILENAME_RE.fullmatch(filename) or filename not in allowed or not j.path(filename).is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(j.path(filename), filename=filename if download else None)


_dist = REPO_ROOT / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
