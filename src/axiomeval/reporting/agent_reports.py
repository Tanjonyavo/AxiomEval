"""JSON and HTML views of real runs; secrets are checked absent before writing."""
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from html import escape
from pathlib import Path

from axiomeval import __version__
from axiomeval.agent_config import AgentConfig
from axiomeval.agent_run import AgentResult
from axiomeval.collect.redaction import Redactor
from axiomeval.ids import new_run_id


def _default(value: object) -> str:
    if isinstance(value, datetime | Path):
        return str(value.isoformat() if isinstance(value, datetime) else value)
    raise TypeError(f"Unsupported report value: {type(value).__name__}")


def payload(config: AgentConfig, result: AgentResult) -> dict:
    records = result.records
    return {
        "schema_version": "0.2", "axiomeval_version": __version__,
        "synthetic": result.provenance.get("synthetic", False),
        "scope": ("Agent local réel, base documentaire et outils sans effet sensible. "
                  "Comptes descriptifs uniquement : aucune affirmation statistique."),
        "overall_verdict": result.overall,
        "provenance": result.provenance,
        "harness_peak_memory_bytes": result.harness_peak_memory_bytes,
        "counts": {
            "runs": len(records),
            "verdicts": dict(Counter(r.decision.verdict for r in records)),
            "business": dict(Counter(r.score.business for r in records)),
            "permission": dict(Counter(r.score.permission for r in records)),
        },
        "runs": [{
            "task_id": r.task_id, "repetition": r.repetition, "run_id": r.run.id,
            "verdict": r.decision.verdict, "reasons": r.decision.reasons,
            "business": r.score.business, "permission": r.score.permission,
            "score_reasons": r.score.reasons, "wall_seconds": r.wall_seconds,
            "prompt_tokens": r.prompt_tokens, "output_tokens": r.output_tokens,
            "trace_digest": r.events[-1].hash if r.events else None,
            "trace": [asdict(e) for e in r.events],
        } for r in records],
        "configuration": {"target": asdict(config.target), "adapter": config.adapter,
                          "repetitions": config.repetitions},
    }


def render_html(data: dict) -> str:
    rows = "".join(
        f"<tr><td>{escape(r['task_id'])}</td><td>{r['repetition']}</td><td>{escape(r['verdict'])}</td>"
        f"<td>{escape(r['business'])}</td><td>{escape(r['permission'])}</td>"
        f"<td>{escape(', '.join(r['score_reasons'] + list(r['reasons'])))}</td>"
        f"<td>{r['wall_seconds']}</td><td>{r['prompt_tokens']} / {r['output_tokens']}</td></tr>"
        for r in data["runs"])
    prov = escape(json.dumps(data["provenance"], ensure_ascii=False, indent=2))
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>AxiomEval — exécution d'un agent réel</title>
<style>body{{font:15px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;color:#142235}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #cad4df;padding:6px;text-align:left}}
th{{background:#eef2f7}}pre{{white-space:pre-wrap;background:#f5f7fa;padding:16px}}</style>
</head><body><h1>AxiomEval — agent réel, lot P02</h1>
<p>{escape(data["scope"])}</p>
<h2>Verdict global (permissions et preuves) : {escape(data["overall_verdict"])}</h2>
<p>La réussite métier est notée à part : un PROMOTE ne signifie pas que la réponse est juste.
Réussite métier : {escape(json.dumps(data["counts"]["business"], ensure_ascii=False))}</p>
<table><tr><th>Tâche</th><th>Rép.</th><th>Verdict</th><th>Métier</th><th>Permission</th>
<th>Raisons</th><th>Durée (s)</th><th>Jetons entrée / sortie</th></tr>{rows}</table>
<h2>Provenance et ressources</h2><pre>{prov}</pre>
<p>Les traces complètes, caviardées et chaînées par empreinte, sont dans report.json.</p>
</body></html>'''


def write_agent_reports(config: AgentConfig, result: AgentResult, output: Path) -> tuple[Path, Path]:
    data = payload(config, result)
    json_text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False, default=_default)
    html_text = render_html(json.loads(json_text))
    redactor = Redactor(config.canaries)
    redactor.assert_clean(json_text)
    redactor.assert_clean(html_text)
    directory = output / new_run_id().replace("RUN-", "AGENT-")
    directory.mkdir(parents=True, exist_ok=False)
    json_path, html_path = directory / "report.json", directory / "report.html"
    json_path.write_text(json_text + "\n", encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")
    return json_path, html_path
