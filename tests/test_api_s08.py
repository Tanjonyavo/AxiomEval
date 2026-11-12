"""S8: API contract, persistence, migrations, idempotence and recovery (gate G8)."""
import copy
import functools
import sqlite3
import tempfile
import threading
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from axiomeval.api.app import create_app
from axiomeval.api.store import Store, StoreError
from axiomeval.collect.redaction import Redactor
from axiomeval.collect.trace import TraceRecorder
from axiomeval.models import Run

CANARIES = ("AXM-CANARY-7F3A91C2E5", "CANARY_SYSPROMPT_51F0C2")
TOKEN = "test-token-not-a-secret"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
BASE, CAND = "b" * 64, "c" * 64
T0 = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


@functools.lru_cache(maxsize=None)
def chained_trace(tag: str) -> tuple[list, str]:
    """A real hash-chained trace, serialized as a collection writes it; one per tag."""
    recorder = TraceRecorder(Run("target", "scenario", id=f"RUN-{tag}", started_at=T0), lambda: T0,
                             Redactor(CANARIES))
    recorder.add("input", question=f"question {tag}")
    recorder.add("output", answer="réponse")
    return [dict(asdict(e), at=str(e.at)) for e in recorder.events], recorder.events[-1].hash


def rec(i, release=BASE, business="SUCCESS", permission="OK", trace="t"):
    events, last = chained_trace(trace)
    return {"draw_key": f"{release[:1]}-{i:04d}", "release_digest": release, "release_id": "r-" + release[:1],
            "evaluator": "corpus-evaluator-v2", "scenario_id": f"g{i}-v0", "group_id": f"g{i}", "kind": "information",
            "partition": "test", "business": business, "permission": permission, "trace_digest": last,
            "trace": copy.deepcopy(events), "security": {"attack_succeeded": False, "attack_attempted": False}}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "axiomeval.db"
        self.store = Store(self.path, CANARIES)
        self.store.migrate()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_migrations_apply_once_and_detect_tampering(self):
        self.assertEqual(self.store.migrate(), [])
        self.assertEqual(self.store.schema_version(), "0002_verdicts")
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "0001_a.sql").write_text("CREATE TABLE a (x TEXT);", encoding="utf-8")
            fresh = Store(":memory:", CANARIES)
            self.assertEqual(fresh.migrate(folder), ["0001_a"])
            (folder / "0001_a.sql").write_text("CREATE TABLE a (x TEXT, y TEXT);", encoding="utf-8")
            with self.assertRaises(StoreError):
                fresh.migrate(folder)
            fresh.close()

    def test_failed_migration_leaves_no_partial_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "0001_bad.sql").write_text("CREATE TABLE ok (x TEXT); CREATE TABLE broken (;", encoding="utf-8")
            fresh = Store(":memory:", CANARIES)
            with self.assertRaises(sqlite3.Error):
                fresh.migrate(folder)
            names = {r[0] for r in fresh.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("ok", names)
            self.assertIsNone(fresh.schema_version())
            fresh.close()

    def test_import_is_idempotent(self):
        batch = [rec(i) for i in range(5)]
        self.assertEqual(self.store.import_records(batch), {"inserted": 5, "skipped": 0})
        self.assertEqual(self.store.import_records(batch), {"inserted": 0, "skipped": 5})
        self.assertEqual(self.store.releases()[0]["runs"], 5)

    def test_batch_is_atomic(self):
        bad = [rec(0), rec(1), dict(rec(2), business="GREAT")]
        with self.assertRaises(StoreError):
            self.store.import_records(bad)
        conflict = [rec(10), rec(11)]
        self.store.import_records(conflict)
        with self.assertRaises(StoreError):
            self.store.import_records([rec(12), rec(10, trace="other")])
        self.assertEqual(self.store.releases()[0]["runs"], 2)

    def test_trace_must_match_its_digest(self):
        """Audit 2026-11-11, finding 2: a hand-written digest or an edited trace was accepted."""
        forged = dict(rec(0), trace_digest="f" * 64)
        edited = rec(1)
        edited["trace"][1]["data"]["answer"] = "autre réponse"
        reordered = rec(2)
        reordered["trace"].reverse()
        for name, bad in (("forged", forged), ("edited", edited), ("reordered", reordered),
                          ("missing", {k: v for k, v in rec(3).items() if k != "trace"}),
                          ("empty", dict(rec(4), trace=[]))):
            with self.subTest(name), self.assertRaises(StoreError):
                self.store.import_records([bad])
        self.assertEqual(self.store.releases(), [])

    def test_fields_the_verdict_reads_are_validated(self):
        for name, bad in (("security", dict(rec(0), security={})),
                          ("security type", dict(rec(0), security={"attack_attempted": 0, "attack_succeeded": 0})),
                          ("kind", dict(rec(0), kind="other")), ("partition", dict(rec(0), partition="holdout")),
                          ("release", dict(rec(0), release_digest="short")), ("group", dict(rec(0), group_id=""))):
            with self.subTest(name), self.assertRaises(StoreError):
                self.store.import_records([bad])

    def test_concurrent_imports_keep_every_batch(self):
        """Audit 2026-11-11, finding 1: threads sharing the connection lost rows and broke atomicity."""
        errors = []

        def worker(t):
            for b in range(10):
                try:
                    self.store.import_records([dict(rec(1000 * t + 25 * b + i), group_id=f"t{t}")
                                               for i in range(25)])
                except Exception as exc:  # noqa: BLE001 - any error is a failure here
                    errors.append(repr(exc))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(self.store.releases()[0]["runs"], 1000)

    def test_secret_never_stored(self):
        leaking = dict(rec(0), note=f"jeton {CANARIES[0]}")
        with self.assertRaises(StoreError):
            self.store.import_records([leaking])
        self.assertEqual(self.store.releases(), [])

    def test_backup_and_restore(self):
        self.store.import_records([rec(i) for i in range(3)])
        copy = Path(self.temp.name) / "backup.db"
        self.store.backup(copy)
        restored = Store(copy, CANARIES)
        self.assertTrue(restored.integrity_ok())
        self.assertEqual(restored.migrate(), [])
        self.assertEqual(len(restored.records(BASE)), 3)
        restored.close()

    def test_data_survives_reopen(self):
        self.store.import_records([rec(1)])
        self.store.close()
        self.store = Store(self.path, CANARIES)
        self.assertEqual(len(self.store.records(BASE)), 1)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:", CANARIES)
        self.store.migrate()
        self.client = TestClient(create_app(self.store, TOKEN))

    def tearDown(self):
        self.store.close()

    def load(self, n=40):
        records = [rec(i) for i in range(n)] + [rec(i, CAND) for i in range(n)]
        return self.client.post("/v1/runs:import", json={"records": records}, headers=AUTH)

    def test_health_is_public_everything_else_needs_a_token(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        for method, path in (("get", "/ready"), ("get", "/v1/releases"), ("post", "/v1/verdicts")):
            with self.subTest(path=path):
                self.assertEqual(getattr(self.client, method)(path).status_code, 401)
        wrong = {"Authorization": "Bearer nope"}
        self.assertEqual(self.client.get("/v1/releases", headers=wrong).status_code, 401)

    def test_empty_token_configuration_refuses_everyone(self):
        client = TestClient(create_app(self.store, ""))
        self.assertEqual(client.get("/v1/releases", headers={"Authorization": "Bearer "}).status_code, 401)

    def test_ready_reports_schema(self):
        body = self.client.get("/ready", headers=AUTH).json()
        self.assertEqual(body, {"status": "ready", "schema_version": "0002_verdicts"})

    def test_import_contract(self):
        self.assertEqual(self.load().json(), {"inserted": 80, "skipped": 0})
        self.assertEqual(self.load().json(), {"inserted": 0, "skipped": 80})
        for body in ({}, {"records": []}, {"records": [rec(0)], "extra": 1}, {"records": "x"}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/v1/runs:import", json=body, headers=AUTH).status_code, 422)
        missing = {"records": [{"draw_key": "x"}]}
        self.assertEqual(self.client.post("/v1/runs:import", json=missing, headers=AUTH).status_code, 422)
        broken = {"records": [dict(rec(500), security={}, kind="attack")]}
        self.assertEqual(self.client.post("/v1/runs:import", json=broken, headers=AUTH).status_code, 422)

    def test_oversized_body_refused(self):
        response = self.client.post("/v1/runs:import", content=b"{}",
                                    headers={**AUTH, "Content-Length": "999999999", "Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)

    def test_verdict_is_computed_stored_and_idempotent(self):
        records = [rec(i, BASE, business="FAILURE" if i == 0 else "SUCCESS") for i in range(400)]
        records += [rec(i, CAND, business="FAILURE" if i == 1 else "SUCCESS") for i in range(400)]
        self.assertEqual(self.client.post("/v1/runs:import", json={"records": records}, headers=AUTH).status_code, 200)
        body = {"baseline_release": BASE, "candidate_release": CAND, "margin": 0.15}
        first = self.client.post("/v1/verdicts", json=body, headers=AUTH).json()
        second = self.client.post("/v1/verdicts", json=body, headers=AUTH).json()
        self.assertEqual(first["verdict"], "PROMOTE")
        self.assertEqual(first["verdict_id"], second["verdict_id"])
        stored = self.client.get(f"/v1/verdicts/{first['verdict_id']}", headers=AUTH).json()
        self.assertEqual(stored["inputs_digest"], first["inputs_digest"])
        self.assertEqual(self.store.conn.execute("SELECT count(*) FROM verdicts").fetchone()[0], 1)

    def test_verdict_changes_identity_when_evidence_changes(self):
        self.load(20)
        body = {"baseline_release": BASE, "candidate_release": CAND}
        first = self.client.post("/v1/verdicts", json=body, headers=AUTH).json()
        self.client.post("/v1/runs:import", json={"records": [rec(99, CAND, permission="VIOLATION"), rec(99)]},
                         headers=AUTH)
        second = self.client.post("/v1/verdicts", json=body, headers=AUTH).json()
        self.assertEqual((first["verdict"], second["verdict"]), ("HOLD", "REJECT"))
        self.assertNotEqual(first["verdict_id"], second["verdict_id"])

    def test_unknown_release_is_not_found_and_nothing_is_stored(self):
        body = {"baseline_release": BASE, "candidate_release": CAND}
        self.assertEqual(self.client.post("/v1/verdicts", json=body, headers=AUTH).status_code, 404)
        self.assertEqual(self.store.conn.execute("SELECT count(*) FROM verdicts").fetchone()[0], 0)

    def test_release_without_overlapping_groups_is_incomplete(self):
        self.client.post("/v1/runs:import", json={"records": [rec(1), rec(2, CAND)]}, headers=AUTH)
        body = {"baseline_release": BASE, "candidate_release": CAND}
        self.assertEqual(self.client.post("/v1/verdicts", json=body, headers=AUTH).json()["verdict"], "INCOMPLETE")

    def test_invalid_verdict_requests(self):
        for body in ({"baseline_release": "short", "candidate_release": CAND},
                     {"baseline_release": BASE, "candidate_release": CAND, "alpha": 0.9},
                     {"baseline_release": BASE, "candidate_release": CAND, "partitions": ["holdout"]}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/v1/verdicts", json=body, headers=AUTH).status_code, 422)
        self.assertEqual(self.client.get("/v1/verdicts/VER-unknown", headers=AUTH).status_code, 404)

    def test_openapi_contract_lists_the_routes(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        for path in ("/health", "/ready", "/v1/runs:import", "/v1/releases", "/v1/verdicts",
                     "/v1/verdicts/{verdict_id}"):
            self.assertIn(path, paths)


if __name__ == "__main__":
    unittest.main()
