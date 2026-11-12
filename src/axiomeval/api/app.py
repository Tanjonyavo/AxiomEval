"""FastAPI application: import runs, list releases, compute and read verdicts (S8).

Local use only. A bearer token read from AXIOMEVAL_API_TOKEN protects every
route except /health; requests with unknown fields are rejected (extra=forbid).
"""
import hmac
import os
from dataclasses import asdict
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from axiomeval import __version__
from axiomeval.api.store import Store, StoreError
from axiomeval.ids import digest, stable_id
from axiomeval.stats.paired import Protocol, release_verdict

MAX_BODY_BYTES = 20_000_000


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[dict] = Field(min_length=1, max_length=5000)


class ImportResponse(BaseModel):
    inserted: int
    skipped: int


class VerdictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline_release: str = Field(min_length=64, max_length=64)
    candidate_release: str = Field(min_length=64, max_length=64)
    alpha: float = Field(0.05, gt=0, lt=0.5)
    margin: float = Field(0.10, ge=0, le=1)
    min_groups: int = Field(10, ge=2, le=100_000)
    partitions: list[Literal["train", "validation", "calibration", "test"]] | None = None


class VerdictResponse(BaseModel):
    verdict_id: str
    verdict: Literal["PROMOTE", "HOLD", "INCOMPLETE", "REJECT"]
    reasons: list[str]
    inputs_digest: str
    paired: dict | None
    security: dict


def create_app(store: Store, token: str | None = None) -> FastAPI:
    token = token if token is not None else os.environ.get("AXIOMEVAL_API_TOKEN", "")
    app = FastAPI(title="AxiomEval API", version=__version__)

    def auth(authorization: str = Header(default="")) -> None:
        expected = f"Bearer {token}"
        if not token or not hmac.compare_digest(authorization.encode(), expected.encode()):
            raise HTTPException(status_code=401, detail="missing or invalid token")

    @app.middleware("http")
    async def limit_size(request: Request, call_next):
        size = request.headers.get("content-length")
        if size is not None and (not size.isdigit() or int(size) > MAX_BODY_BYTES):
            return JSONResponse({"detail": "request body too large"}, status_code=413)
        return await call_next(request)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/ready", dependencies=[Depends(auth)])
    def ready() -> dict:
        version = store.schema_version()
        if version is None or not store.integrity_ok():
            raise HTTPException(status_code=503, detail="database not ready")
        return {"status": "ready", "schema_version": version}

    @app.post("/v1/runs:import", response_model=ImportResponse, dependencies=[Depends(auth)])
    def import_runs(body: ImportRequest) -> ImportResponse:
        try:
            return ImportResponse(**store.import_records(body.records))
        except StoreError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/releases", dependencies=[Depends(auth)])
    def releases() -> list[dict]:
        return store.releases()

    @app.post("/v1/verdicts", response_model=VerdictResponse, dependencies=[Depends(auth)])
    def create_verdict(body: VerdictRequest) -> VerdictResponse:
        known = {r["release_digest"] for r in store.releases()}
        unknown = [d for d in (body.baseline_release, body.candidate_release) if d not in known]
        if unknown:
            raise HTTPException(status_code=404, detail="unknown release: " + ", ".join(d[:12] for d in unknown))
        base, cand = store.records(body.baseline_release), store.records(body.candidate_release)
        if body.partitions:
            base = [r for r in base if r["partition"] in body.partitions]
            cand = [r for r in cand if r["partition"] in body.partitions]
        protocol = Protocol(body.alpha, body.margin, body.min_groups)
        try:
            result = release_verdict(base, cand, protocol)
        except (KeyError, TypeError, ValueError) as exc:  # rows stored before import validation existed
            raise HTTPException(status_code=422, detail="stored records cannot be scored") from exc
        inputs = digest({"baseline": sorted(r["draw_key"] for r in base),
                         "candidate": sorted(r["draw_key"] for r in cand)})
        protocol_dict = {**asdict(protocol), "partitions": body.partitions}
        verdict_id = stable_id("VER", [body.baseline_release, body.candidate_release, protocol_dict, inputs])
        payload = {"verdict": result.verdict.value, "reasons": list(result.reasons),
                   "paired": asdict(result.paired) if result.paired else None, "security": result.security}
        verdict_id = store.save_verdict(verdict_id, body.baseline_release, body.candidate_release, protocol_dict,
                                        inputs, result.verdict.value, payload)
        return VerdictResponse(verdict_id=verdict_id, inputs_digest=inputs, **payload)

    @app.get("/v1/verdicts/{verdict_id}", dependencies=[Depends(auth)])
    def read_verdict(verdict_id: str) -> dict:
        found = store.verdict(verdict_id)
        if found is None:
            raise HTTPException(status_code=404, detail="unknown verdict")
        return found

    return app
