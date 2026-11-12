"""SQLite persistence with checksummed migrations, atomic imports and backups (S8).

Every write happens in one transaction: an import either stores the whole batch
or nothing. Re-importing the same draw is a no-op; the same draw_key with a
different trace is a conflict and the batch is refused.

One connection is shared by the API worker threads, so every use of it holds a
lock: two requests must never interleave inside one transaction.
"""
import hashlib
import json
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from axiomeval.collect.redaction import Redactor
from axiomeval.collect.trace import serialized_trace_digest
from axiomeval.errors import AxiomEvalError

MIGRATIONS = Path(__file__).with_name("migrations")
REQUIRED = ("draw_key", "release_digest", "release_id", "evaluator", "scenario_id", "group_id", "kind",
            "partition", "business", "permission", "trace_digest", "security", "trace")
TEXT_FIELDS = ("draw_key", "release_id", "evaluator", "scenario_id", "group_id")
KINDS = ("information", "account", "action", "attack")
PARTITIONS = ("train", "validation", "calibration", "test")
SHA256 = re.compile(r"[0-9a-f]{64}")


class StoreError(AxiomEvalError):
    """A persistence rule was violated; nothing was written."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_record(i: int, r: object) -> None:
    """Refuse a record the verdict could not use, or whose trace does not match its digest."""
    if not isinstance(r, dict):
        raise StoreError(f"record {i} is not an object")
    missing = [k for k in REQUIRED if k not in r]
    if missing:
        raise StoreError(f"record {i} misses {', '.join(missing)}")
    if any(not isinstance(r[k], str) or not r[k].strip() for k in TEXT_FIELDS):
        raise StoreError(f"record {i} has an empty or non-text identifier")
    if not isinstance(r["release_digest"], str) or not SHA256.fullmatch(r["release_digest"]):
        raise StoreError(f"record {i} has an invalid release_digest")
    if r["business"] not in ("SUCCESS", "FAILURE", "MISSING") or \
            r["permission"] not in ("OK", "UNCERTAIN", "VIOLATION"):
        raise StoreError(f"record {i} has an invalid score")
    if r["kind"] not in KINDS or r["partition"] not in PARTITIONS:
        raise StoreError(f"record {i} has an invalid kind or partition")
    security = r["security"]
    if not isinstance(security, dict) or any(type(security.get(k)) is not bool
                                             for k in ("attack_attempted", "attack_succeeded")):
        raise StoreError(f"record {i} has an invalid security observation")
    try:
        chained = serialized_trace_digest(r["trace"])
    except AxiomEvalError as exc:
        raise StoreError(f"record {i} has an invalid trace: {exc}") from exc
    if chained != r["trace_digest"]:
        raise StoreError(f"record {i}: trace_digest does not match its trace")


class Store:
    def __init__(self, path: str | Path, canaries: tuple[str, ...]) -> None:
        self.path = str(path)
        self.redactor = Redactor(canaries)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None, timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.conn.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    @contextmanager
    def transaction(self):
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
            self.conn.execute("COMMIT")

    # --- migrations -----------------------------------------------------------------
    def migrate(self, directory: Path = MIGRATIONS) -> list[str]:
        """Apply pending migrations in order; refuse if an applied file was modified."""
        with self.lock:
            return self._migrate(directory)

    def _migrate(self, directory: Path) -> list[str]:
        self.conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, "
                          "sha256 TEXT NOT NULL, applied_at TEXT NOT NULL)")
        applied = {r["version"]: r["sha256"] for r in self.conn.execute("SELECT * FROM schema_migrations")}
        done = []
        for path in sorted(Path(directory).glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.replace("\r\n", "\n").encode("utf-8")).hexdigest()
            if path.stem in applied:
                if applied[path.stem] != checksum:
                    raise StoreError(f"applied migration {path.stem} was modified")
                continue
            # Comments may contain ';': drop them before splitting. String literals with ';' are not supported.
            code = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
            with self.transaction() as conn:
                for statement in (s.strip() for s in code.split(";")):
                    if statement:
                        conn.execute(statement)
                conn.execute("INSERT INTO schema_migrations VALUES (?, ?, ?)", (path.stem, checksum, _now()))
            done.append(path.stem)
        return done

    def schema_version(self) -> str | None:
        with self.lock:
            row = self.conn.execute("SELECT max(version) AS v FROM schema_migrations").fetchone()
        return row["v"] if row else None

    # --- runs -----------------------------------------------------------------------
    def import_records(self, records: list[dict]) -> dict:
        for i, r in enumerate(records):
            check_record(i, r)
        inserted = skipped = 0
        with self.transaction() as conn:
            for r in records:
                text = json.dumps(r, ensure_ascii=False, sort_keys=True)
                try:
                    self.redactor.assert_clean(text)
                except AxiomEvalError as exc:
                    raise StoreError("a record contains a canary secret") from exc
                existing = conn.execute("SELECT trace_digest FROM runs WHERE draw_key = ?", (r["draw_key"],)).fetchone()
                if existing:
                    if existing["trace_digest"] != r["trace_digest"]:
                        raise StoreError(f"conflicting record for draw {r['draw_key'][:12]}")
                    skipped += 1
                    continue
                conn.execute("INSERT OR IGNORE INTO releases VALUES (?, ?, ?)",
                             (r["release_digest"], r["release_id"], _now()))
                conn.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (r["draw_key"], r["release_digest"], r["evaluator"], r["scenario_id"], r["group_id"],
                              r["kind"], r["partition"], r["business"], r["permission"], r["trace_digest"], text))
                inserted += 1
        return {"inserted": inserted, "skipped": skipped}

    def releases(self) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT r.release_digest, r.release_id, count(u.draw_key) AS runs, "
                "sum(u.business = 'SUCCESS') AS successes, sum(u.permission = 'VIOLATION') AS breaches "
                "FROM releases r LEFT JOIN runs u USING (release_digest) GROUP BY r.release_digest "
                "ORDER BY r.release_id").fetchall()
        return [dict(r) for r in rows]

    def records(self, release_digest: str) -> list[dict]:
        with self.lock:
            rows = self.conn.execute("SELECT record_json FROM runs WHERE release_digest = ? ORDER BY draw_key",
                                     (release_digest,)).fetchall()
        return [json.loads(r["record_json"]) for r in rows]

    # --- verdicts -------------------------------------------------------------------
    def save_verdict(self, verdict_id: str, baseline: str, candidate: str, protocol: dict, inputs_digest: str,
                     verdict: str, result: dict) -> str:
        with self.transaction() as conn:
            protocol_json = json.dumps(protocol, sort_keys=True)
            row = conn.execute("SELECT verdict_id FROM verdicts WHERE baseline_release = ? AND candidate_release = ? "
                               "AND protocol_json = ? AND inputs_digest = ?",
                               (baseline, candidate, protocol_json, inputs_digest)).fetchone()
            if row:
                return row["verdict_id"]
            conn.execute("INSERT INTO verdicts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (verdict_id, baseline, candidate, protocol_json, inputs_digest, verdict,
                          json.dumps(result, ensure_ascii=False, default=str), _now()))
        return verdict_id

    def verdict(self, verdict_id: str) -> dict | None:
        with self.lock:
            row = self.conn.execute("SELECT * FROM verdicts WHERE verdict_id = ?", (verdict_id,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["protocol"] = json.loads(out.pop("protocol_json"))
        out["result"] = json.loads(out.pop("result_json"))
        return out

    # --- recovery -------------------------------------------------------------------
    def backup(self, target: str | Path) -> None:
        dest = sqlite3.connect(str(target))
        try:
            with self.lock:
                self.conn.backup(dest)
        finally:
            dest.close()

    def integrity_ok(self) -> bool:
        with self.lock:
            return self.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
