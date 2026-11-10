-- Runs imported from collections; draw_key makes imports idempotent.
CREATE TABLE releases (
    release_digest TEXT PRIMARY KEY,
    release_id     TEXT NOT NULL,
    first_seen_at  TEXT NOT NULL
);
CREATE TABLE runs (
    draw_key       TEXT PRIMARY KEY,
    release_digest TEXT NOT NULL REFERENCES releases(release_digest),
    evaluator      TEXT NOT NULL,
    scenario_id    TEXT NOT NULL,
    group_id       TEXT NOT NULL,
    kind           TEXT NOT NULL,
    partition      TEXT NOT NULL,
    business       TEXT NOT NULL CHECK (business IN ('SUCCESS', 'FAILURE', 'MISSING')),
    permission     TEXT NOT NULL CHECK (permission IN ('OK', 'UNCERTAIN', 'VIOLATION')),
    trace_digest   TEXT NOT NULL,
    record_json    TEXT NOT NULL
);
CREATE INDEX runs_by_release ON runs(release_digest, group_id);
