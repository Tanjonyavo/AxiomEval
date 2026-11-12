"""Freeze a comparison protocol and its expected runs before collecting evidence."""

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType

import yaml

from axiomeval.config import UniqueKeyLoader
from axiomeval.corpus.splits import PARTITIONS
from axiomeval.errors import ValidationError
from axiomeval.ids import digest
from axiomeval.stats.paired import Protocol, release_verdict, run_pair

PLAN_VERSION = 2


def load_protocol(path: Path) -> Protocol:
    try:
        config = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ValidationError("invalid comparison configuration YAML") from exc
    if not isinstance(config, dict) or config.keys() != {"alpha", "margin", "min_groups"}:
        raise ValidationError("comparison configuration requires alpha, margin and min_groups")
    return Protocol(**config)


def expected_runs(scenarios, draws: int) -> frozenset[tuple[str, str, int]]:
    if type(draws) is not int or draws < 1:
        raise ValidationError("draws must be a positive integer")
    return frozenset((s.group_id, s.scenario_id, draw) for s in scenarios for draw in range(draws))


def _timestamp(value: str) -> datetime:
    try:
        date = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ValidationError("invalid comparison timestamp") from exc
    if date.utcoffset() is None:
        raise ValidationError("comparison timestamps require a timezone")
    return date


def _check_digest(value: str, field: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValidationError(f"{field} must be a lowercase SHA-256 digest")


@dataclass(frozen=True)
class BoundRelease:
    release_digest: str
    model_digest: str

    def __post_init__(self) -> None:
        _check_digest(self.release_digest, "release digest")
        _check_digest(self.model_digest, "model digest")


@dataclass(frozen=True)
class ComparisonEvidence:
    baseline: BoundRelease
    candidate: BoundRelease
    environment_digest: str
    evaluator: str

    def __post_init__(self) -> None:
        if self.baseline.release_digest == self.candidate.release_digest:
            raise ValidationError("baseline and candidate must be different releases")
        _check_digest(self.environment_digest, "environment digest")
        if not isinstance(self.evaluator, str) or not self.evaluator.strip():
            raise ValidationError("a frozen evaluator version is required")

    def release(self, release_digest: str) -> BoundRelease:
        for release in (self.baseline, self.candidate):
            if release.release_digest == release_digest:
                return release
        raise ValidationError("release is outside the frozen comparison plan")


def _validate_design(pairs, partitions: Mapping[str, str]) -> None:
    if not pairs:
        raise ValidationError("comparison plan must include expected runs")
    if (set(partitions) != {group for group, _, _ in pairs}
            or any(partition not in PARTITIONS for partition in partitions.values())):
        raise ValidationError("frozen partitions must cover exactly the planned groups")


@dataclass(frozen=True)
class FrozenComparison:
    protocol: Protocol
    frozen_at: datetime
    sha256: str
    corpus_digest: str
    pairs: frozenset[tuple[str, str, int]]
    partitions: Mapping[str, str]
    evidence: ComparisonEvidence

    def covers(self, row: dict, release: BoundRelease) -> bool:
        pair = run_pair(row)
        if ("draw" not in row or pair not in self.pairs
                or row.get("comparison_plan_sha256") != self.sha256
                or row.get("corpus_digest") != self.corpus_digest
                or row.get("partition") != self.partitions[pair[0]]
                or row.get("release_digest") != release.release_digest
                or row.get("model_digest") != release.model_digest
                or row.get("environment_digest") != self.evidence.environment_digest
                or row.get("evaluator") != self.evidence.evaluator):
            return False
        try:
            return _timestamp(row.get("started_at")) >= self.frozen_at
        except ValidationError:
            return False

    def verdict(self, baseline: list[dict], candidate: list[dict]):
        covered_baseline = [row for row in baseline if self.covers(row, self.evidence.baseline)]
        covered_candidate = [row for row in candidate if self.covers(row, self.evidence.candidate)]
        reasons = ()
        if len(covered_baseline) != len(baseline) or len(covered_candidate) != len(candidate):
            reasons = ("runs-not-collected-under-frozen-plan",)
        # Only a violation attributable to the frozen candidate can override incomplete evidence.
        return release_verdict(covered_baseline, covered_candidate, self.protocol,
                               expected_pairs=self.pairs, evidence_reasons=reasons)


def freeze_comparison(path: Path, protocol: Protocol, corpus_digest: str,
                      pairs: frozenset[tuple[str, str, int]], partitions: Mapping[str, str],
                      evidence: ComparisonEvidence) -> str:
    _validate_design(pairs, partitions)
    payload = {"version": PLAN_VERSION, "frozen_at": datetime.now(timezone.utc).isoformat(),
               "config_sha256": digest(asdict(protocol)), "corpus_digest": corpus_digest,
               "runs": sorted(pairs), "partitions": dict(partitions), "evidence": asdict(evidence)}
    fingerprint = digest(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump({**payload, "sha256": fingerprint}, stream, indent=2)
            stream.write("\n")
    except FileExistsError as exc:
        raise ValidationError("comparison plan already exists and cannot be overwritten") from exc
    return fingerprint


def load_comparison(path: Path, protocol: Protocol) -> FrozenComparison:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        fingerprint = plan.pop("sha256")
        if digest(plan) != fingerprint:
            raise ValidationError("frozen comparison plan SHA-256 does not match")
        if plan.get("version") != PLAN_VERSION:
            raise ValidationError("unsupported comparison plan version; freeze a new plan for confirmation")
        if plan["config_sha256"] != digest(asdict(protocol)):
            raise ValidationError("comparison configuration changed after freezing (including the margin)")
        frozen_at = _timestamp(plan["frozen_at"])
        pairs = frozenset(run_pair({"group_id": group, "scenario_id": scenario, "draw": draw})
                          for group, scenario, draw in plan["runs"])
        if None in pairs or len(pairs) != len(plan["runs"]):
            raise ValidationError("invalid or duplicate runs in frozen comparison plan")
        partitions = plan["partitions"]
        if not isinstance(partitions, dict):
            raise ValidationError("invalid frozen partitions")
        _validate_design(pairs, partitions)
        binding = plan["evidence"]
        evidence = ComparisonEvidence(BoundRelease(**binding["baseline"]), BoundRelease(**binding["candidate"]),
                                      binding["environment_digest"], binding["evaluator"])
        return FrozenComparison(protocol, frozen_at, fingerprint, plan["corpus_digest"], pairs,
                                MappingProxyType(partitions), evidence)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValidationError("invalid frozen comparison plan") from exc
