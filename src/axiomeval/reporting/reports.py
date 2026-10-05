"""Two local views of the same evaluated result; all HTML data are escaped."""
import json
from dataclasses import asdict
from datetime import datetime
from html import escape
from pathlib import Path

from axiomeval import __version__
from axiomeval.config import Config
from axiomeval.demo import DemoResult


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported report value: {type(value).__name__}")


def report_payload(config: Config, result: DemoResult) -> dict:
    return {
        "schema_version": "0.1", "axiomeval_version": __version__,
        "synthetic": True,
        "scope": "Week-1 fixture; no real agent, tool execution or authenticated collector",
        "configuration": asdict(config), "result": asdict(result),
    }


def render_html(json_text: str, verdict: str) -> str:
    return f'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>AxiomEval — démonstration S1</title>
<style>body{{font:16px system-ui;max-width:1000px;margin:40px auto;padding:0 24px;background:#f5f7fa;color:#142235}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:24px;border:1px solid #cad4df}}h1{{color:#143b63}}</style>
</head><body><h1>AxiomEval — semaine 1</h1>
<p>Données synthétiques. Aucun agent IA réel ni outil exécuté.</p>
<h2>Verdict : {escape(verdict)}</h2>
<p>Recommandation limitée au contrôle configuré. Une empreinte ne vaut pas signature.</p>
<pre>{escape(json_text)}</pre></body></html>'''


def write_reports(config: Config, result: DemoResult, output: Path) -> tuple[Path, Path]:
    json_text = json.dumps(report_payload(config, result), ensure_ascii=False, indent=2,
                           allow_nan=False, default=_json_default)
    html_text = render_html(json_text, result.decision.verdict)
    directory = output / result.run.id
    directory.mkdir(parents=True, exist_ok=False)
    json_path, html_path = directory / "report.json", directory / "report.html"
    json_path.write_text(json_text + "\n", encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")
    return json_path, html_path
