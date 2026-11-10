-- A verdict is stored with the digest of its exact inputs, so it can be recomputed and checked.
CREATE TABLE verdicts (
    verdict_id         TEXT PRIMARY KEY,
    baseline_release   TEXT NOT NULL REFERENCES releases(release_digest),
    candidate_release  TEXT NOT NULL REFERENCES releases(release_digest),
    protocol_json      TEXT NOT NULL,
    inputs_digest      TEXT NOT NULL,
    verdict            TEXT NOT NULL CHECK (verdict IN ('PROMOTE', 'HOLD', 'INCOMPLETE', 'REJECT')),
    result_json        TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    UNIQUE (baseline_release, candidate_release, protocol_json, inputs_digest)
);
