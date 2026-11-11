"""Build the teaching collection from the real repository.

- Code volumes: every relevant file, exact content at HEAD, numbered lines,
  with the explanation of each line range placed right after it.
- Coverage index: significant lines (not blank, not comment-only) covered by
  an explanation range, per file. Nothing is claimed beyond what is measured.
- Other volumes: Markdown sources in docs/pedagogie/sources rendered to HTML.

PDF printing is done by print.mjs (Playwright/Chromium).
Usage: python tools/pedagogie/build.py
"""
import html
import re
import subprocess
from pathlib import Path

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename, TextLexer

ROOT = Path(__file__).resolve().parents[2]
PED = ROOT / "docs" / "pedagogie"
EXPL = PED / "explications"
OUT = PED / "build"
INCLUDE = ["src/**/*.py", "src/**/*.sql", "tests/**/*.py", "labs/*.py", "configs/**/*.yaml",
           "fixtures/corpus/*.json", "fixtures/security/templates.json", ".github/workflows/*.yml", "pyproject.toml"]
WEEK = [  # first matching prefix wins
    ("src/axiomeval/policy", "S06"), ("tests/test_policy_s06", "S06"),
    ("src/axiomeval/corpus", "S03-S04"), ("src/axiomeval/collection", "S03-S04"), ("fixtures/corpus", "S03-S04"),
    ("configs/releases", "S03-S04"), (".github", "S04"), ("tests/test_corpus", "S04-S05"),
    ("src/axiomeval/stats", "S05"), ("labs/", "S05"),
    ("src/axiomeval/security", "S07"), ("fixtures/security", "S07"), ("tests/test_security", "S07"),
    ("src/axiomeval/api", "S08"), ("tests/test_api", "S08"), ("src/axiomeval/cli_corpus", "S04-S09"),
    ("src/axiomeval/ml", "S09"), ("tests/test_ml", "S09"),
    ("src/axiomeval/collect", "S02-S03"), ("src/axiomeval/agent", "S02-S03"), ("tests/test_agent", "S02-S03"),
    ("src/axiomeval/reporting/agent", "S02-S03"), ("configs/agent", "S02"), ("tests/test_comparaison", "S05"),
]
VOLUMES = [("01", "Socle, agent réel et traces (S01-S03)", ("S01", "S02-S03", "S02")),
           ("02", "Corpus, statistiques et autorisation (S03-S06)", ("S03-S04", "S04", "S04-S05", "S05", "S06")),
           ("03", "Sécurité, API, ML et outils (S07-S09)", ("S07", "S08", "S04-S09", "S09"))]


def head() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def files() -> list[Path]:
    found = set()
    for pattern in INCLUDE:
        found.update(p for p in ROOT.glob(pattern) if p.is_file() and "__pycache__" not in p.parts)
    return sorted(found, key=lambda p: p.relative_to(ROOT).as_posix())


def week_of(rel: str) -> str:
    return next((w for prefix, w in WEEK if rel.startswith(prefix)), "S01")


def significant(line: str, suffix: str) -> bool:
    s = line.strip()
    if not s:
        return False
    comment = {".py": "#", ".yaml": "#", ".yml": "#", ".toml": "#", ".sql": "--"}.get(suffix)
    return not (comment and s.startswith(comment))


def explanations(rel: str) -> list[tuple[int, int, str]]:
    path = EXPL / (rel.replace("/", "__") + ".md")
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^## L(\d+)(?:-L?(\d+))?\s*$", text, flags=re.M)
    out = []
    for i in range(1, len(parts), 3):
        start = int(parts[i])
        end = int(parts[i + 1]) if parts[i + 1] else start
        out.append((start, end, parts[i + 2].strip()))
    return sorted(out)


def file_intro(rel: str) -> str:
    path = EXPL / (rel.replace("/", "__") + ".md")
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    intro = re.split(r"^## L\d+", text, maxsplit=1, flags=re.M)[0]
    return re.sub(r"^# .*$", "", intro, count=1, flags=re.M).strip()


def render_file(path: Path, commit: str) -> tuple[str, dict]:
    rel = path.relative_to(ROOT).as_posix()
    lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    try:
        lexer = get_lexer_for_filename(path.name)
    except Exception:
        lexer = TextLexer()
    fmt = HtmlFormatter(nowrap=True)
    ranges = explanations(rel)
    covered = set()
    for start, end, _ in ranges:
        covered.update(range(start, end + 1))
    sig = [i for i, line in enumerate(lines, 1) if significant(line, path.suffix)]
    stats = {"file": rel, "lines": len(lines), "significant": len(sig),
             "explained": sum(1 for i in sig if i in covered), "week": week_of(rel)}
    out = [f'<section class="file" id="{html.escape(rel)}"><h2>{html.escape(rel)}</h2>',
           f'<p class="meta">Commit de référence <code>{commit}</code> · {len(lines)} lignes · '
           f'{stats["explained"]}/{stats["significant"]} lignes significatives expliquées</p>']
    intro = file_intro(rel)
    if intro:
        out.append(f'<div class="intro">{md(intro)}</div>')
    cursor = 1
    blocks = ranges or []
    def code(a, b):
        rows = []
        for n in range(a, b + 1):
            src = highlight(lines[n - 1], lexer, fmt).rstrip("\n") if lines[n - 1] else ""
            rows.append(f'<tr><td class="ln">{n}</td><td class="src"><pre>{src}</pre></td></tr>')
        return '<table class="code">' + "".join(rows) + "</table>"
    for start, end, text in blocks:
        start, end = max(start, 1), min(end, len(lines))
        if start > cursor:
            out.append(code(cursor, start - 1))
        out.append(code(start, end))
        out.append(f'<div class="expl"><p class="range">Lignes {start}–{end}</p>'
                   f'{md(text)}</div>')
        cursor = end + 1
    if cursor <= len(lines):
        out.append(code(cursor, len(lines)))
    out.append("</section>")
    return "\n".join(out), stats


CSS = """
@page { size: Letter; margin: 0.6in 0.6in 0.7in; }
body { font-family: Calibri, 'Segoe UI', Arial, sans-serif; font-size: 10.5pt; color: #1d2433; line-height: 1.35; }
h1 { color: #1f4e79; font-size: 22pt; } h2 { color: #1f4e79; border-bottom: 1px solid #1f4e79; font-size: 14pt; margin-top: 18px; break-after: avoid; }
h3 { color: #1f4e79; font-size: 12pt; break-after: avoid; }
.file { break-before: page; } .meta { color: #4a5568; font-size: 9pt; }
table.code { border-collapse: collapse; width: 100%; font-family: Consolas, 'Courier New', monospace; font-size: 8.4pt; background: #f7f9fb; }
table.code td { padding: 0 4px; vertical-align: top; } td.ln { color: #8a94a3; text-align: right; width: 34px; border-right: 1px solid #d5dce4; user-select: none; }
td.src pre { margin: 0; white-space: pre-wrap; word-break: break-all; font-family: inherit; }
.expl { border-left: 4px solid #1f4e79; background: #eef3f8; padding: 4px 10px; margin: 4px 0 10px; break-inside: avoid; font-size: 10pt; }
.expl .range { font-weight: bold; color: #1f4e79; margin: 2px 0; } .intro { background: #fbfaf5; border: 1px solid #e6dfc8; padding: 6px 10px; }
table { border-collapse: collapse; } th, td { border: 1px solid #c9d3de; padding: 3px 6px; font-size: 9.5pt; } th { background: #eef2f7; }
code { font-family: Consolas, monospace; font-size: 9pt; } pre { white-space: pre-wrap; }
.toc a { text-decoration: none; color: #1d2433; }
.part { break-before: page; } .partlabel { color: #4a5568; font-size: 9pt; text-transform: uppercase; letter-spacing: 0.5px; }
.partnote { border-left: 4px solid #b45309; background: #fdf6ec; padding: 6px 10px; }
.alltoc, .alltoc ol { list-style: none; } .repodoc { break-before: page; } .repodoc:first-child { break-before: auto; } .alltoc > li { margin-top: 6px; } .alltoc ol { font-size: 9.5pt; } .warn { border-left: 4px solid #b45309; background: #fdf6ec; padding: 6px 10px; }
""" + HtmlFormatter().get_style_defs(".src")

KATEX = ('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">'
         '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>'
         '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>'
         '<script>document.addEventListener("DOMContentLoaded",()=>renderMathInElement(document.body,'
         '{delimiters:[{left:"$$",right:"$$",display:true},{left:"\\\\(",right:"\\\\)",display:false}]}));</script>')


MATH = re.compile(r"\$\$.+?\$\$|\\\(.+?\\\)", re.S)


def md(text: str) -> str:
    """Markdown to HTML without letting Markdown eat the LaTeX delimiters or underscores."""
    spans = []

    def keep(match):
        spans.append(html.escape(match.group(0)))
        return f"@@MATH{len(spans) - 1}@@"
    converted = markdown.markdown(MATH.sub(keep, text), extensions=["tables", "fenced_code", "toc"])
    return re.sub(r"@@MATH(\d+)@@", lambda m: spans[int(m.group(1))], converted)


def page(title: str, body: str) -> str:
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f'<style>{CSS}</style>{KATEX}</head><body>{body}</body></html>')


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    commit = head()
    all_stats, rendered, volumes, sources = [], {}, {}, {}
    for path in files():
        section, stats = render_file(path, commit)
        all_stats.append(stats)
        rendered[stats["file"]] = (stats["week"], section)
    for number, title, weeks in VOLUMES:
        chosen = [(f, s) for f, (w, s) in rendered.items() if w in weeks]
        toc = "".join(f'<li><a href="#{html.escape(f)}">{html.escape(f)}</a></li>' for f, _ in chosen)
        body = (f"<h1>AxiomEval — Code expliqué, volume {number}</h1><p>{html.escape(title)}. Code exact du dépôt "
                f"au commit <code>{commit}</code>, numéroté ; chaque explication suit les lignes qu'elle commente.</p>"
                f'<h2>Fichiers</h2><ol class="toc">{toc}</ol>' + "".join(s for _, s in chosen))
        (OUT / f"AxiomEval_Code_Explique_Volume_{number}.html").write_text(page(f"Code expliqué {number}", body),
                                                                           encoding="utf-8")
        volumes[number] = body
    write_index(all_stats, commit)
    for src in sorted((PED / "sources").glob("*.md")):
        body = md(src.read_text(encoding="utf-8"))
        sources[src.stem] = body
        (OUT / (src.stem + ".html")).write_text(page(src.stem, body), encoding="utf-8")
    write_all_in_one(sources, volumes, commit)


# Reading order of the single PDF. Each entry: (kind, key, title, note). A source written before later work
# says so in its note, so an old "not implemented" is never read as the current state. A "repo" entry
# gathers documents of the repository itself, so the PDF covers everything published on GitHub.
OLD = ("Rédigé le {date} (commit <code>{sha}</code>), avant le corpus v3, S10 et les releases r7–r8. Là où il dit "
       "S10 « non implémentée » ou S09 « partielle », c'est dépassé : l'état actuel est dans la partie 1 "
       "(guide complet) et dans <code>docs/progression/ETAT_MISSION.md</code>.")
REPO_NOTE = "Documents du dépôt, reproduits tels qu'ils sont sur GitHub ; chacun indique son dernier commit."
GITHUB = "https://github.com/Tanjonyavo/AxiomEval/blob/main/"
ALL_IN_ONE = [
    ("guide", "AxiomEval_Guide_v3_S10_et_Pistes", "Guide complet de compréhension",
     "À lire en premier. Version la plus récente ({date}, commit <code>{sha}</code>) : tout le projet, puis le "
     "corpus v3, S10, r7, r8, les pistes pour continuer et les exercices."),
    ("repo", ("RESULTATS.md", "README.md"), "Résultats vérifiables et présentation", REPO_NOTE),
    ("repo", ("docs/security/THREAT_MODEL.md", "docs/security/FINDINGS.md",
              "docs/security/RAPPORT_SECURITE_CORPUS_PRINCIPAL.md", "docs/security/RAPPORT_SECURITE_CORPUS_REGRESSION.md",
              "docs/security/RAPPORT_SECURITE_CORPUS_V2.md"), "Sécurité : menaces, failles et rapports", REPO_NOTE),
    ("repo", ("docs/experiments/S09_BASELINES.md", "docs/experiments/S09_BASELINES_V2.md",
              "docs/experiments/V3_TRAJECTOIRES.md", "docs/experiments/S10_SEQUENCES_V3.md"),
     "Expériences S09 et S10", REPO_NOTE),
    ("repo", ("docs/data/DATA_CARD.md", "docs/data/DATA_CARD_SECURITY.md", "docs/data/DATA_CARD_V2.md",
              "docs/data/DATA_CARD_V3.md", "fixtures/corpus-v3/kb/*.md"), "Données : data cards et base documentaire",
     REPO_NOTE + " La base documentaire est celle du corpus v3 ; les corpus plus anciens en utilisent une partie."),
    ("repo", ("docs/architecture.md", "docs/decisions.md", "labs/README.md", "docs/semaine-01/audit.md",
              "docs/semaine-01/validation.md", "docs/semaine-02/fiche-offre.md", "docs/semaine-06/adaptateur-et-traces.md"),
     "Architecture, décisions et premières semaines", REPO_NOTE),
    ("repo", ("docs/audit/AUDIT_INITIAL_S24.md", "docs/progression/RAPPORT_FINAL_S24.md",
              "docs/progression/ETAT_MISSION.md", "docs/progression/COMMITS_S07_S24.md"),
     "Audit, progression et point de reprise", REPO_NOTE),
    ("old", "AxiomEval_Manuel_Integral_S01_S26", "Manuel intégral S01–S26", OLD),
    ("old", "AxiomEval_Mathematiques_IA_S01_S26", "Mathématiques de l'IA", OLD),
    ("old", "AxiomEval_Exercices_Corriges_S01_S26", "Exercices corrigés S04–S09", OLD),
    ("old", "AxiomEval_Preparation_Entrevues_IA", "Préparation aux entrevues", OLD),
    ("old", "PARCOURS_MAITRISE_PERSONNEL", "Parcours de maîtrise", OLD),
    ("code", "01", "Code expliqué — volume 01", None),
    ("code", "02", "Code expliqué — volume 02", None),
    ("code", "03", "Code expliqué — volume 03", None),
    ("index", "INDEX_CODE_EXPLIQUE", "Index de couverture du code expliqué",
     "Mesuré par <code>tools/pedagogie/build.py</code> au même commit que les volumes de code."),
]


def last_change(path: Path) -> tuple[str, str]:
    out = subprocess.run(["git", "log", "-1", "--format=%h %ad", "--date=short", "--", str(path)], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return (out[0], out[1]) if len(out) == 2 else ("non committé", "non daté")


def prefixed(body: str, prefix: str) -> str:
    """Make ids unique across parts: two documents may both have a heading called « Glossaire »."""
    body = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{prefix}-{m.group(1)}"', body)
    return re.sub(r'href="#([^"]+)"', lambda m: f'href="#{prefix}-{m.group(1)}"', body)


def headings(body: str, level: int) -> list[tuple[str, str]]:
    pattern = rf'<h{level} id="([^"]+)">(.*?)</h{level}>'
    return [(i, re.sub(r"<[^>]+>", "", t)) for i, t in re.findall(pattern, body, flags=re.S)]


def github_links(body: str, rel: str) -> str:
    """A relative link in a repository document points to GitHub, since the PDF has no file tree."""
    base = Path(rel).parent

    def fix(m):
        target = m.group(1)
        if re.match(r"[a-z]+:|#", target):
            return m.group(0)
        parts = []
        for piece in (base / target).as_posix().split("/"):
            if piece == "..":
                if parts:
                    parts.pop()
            elif piece not in ("", "."):
                parts.append(piece)
        return f'href="{GITHUB}{"/".join(parts)}"'
    return re.sub(r'href="([^"]+)"', fix, body)


def repo_docs(patterns: tuple[str, ...]) -> list[Path]:
    found = []
    for pattern in patterns:
        found += sorted(ROOT.glob(pattern)) if "*" in pattern else [ROOT / pattern]
    return found


def write_all_in_one(sources: dict, volumes: dict, commit: str) -> None:
    parts, toc, kinds = [], [], {}
    for n, (kind, key, title, note) in enumerate(ALL_IN_ONE, 1):
        prefix = f"p{n}"
        kinds.setdefault(kind, []).append(n)
        if kind == "code":
            body = prefixed(volumes[key], prefix)
            subs = re.findall(r'<section class="file" id="([^"]+)"><h2>(.*?)</h2>', body)
        elif kind == "repo":
            docs, subs = [], []
            for i, path in enumerate(repo_docs(key)):
                rel = path.relative_to(ROOT).as_posix()
                sha, date = last_change(path)
                anchor = f"{prefix}-doc{i}"
                text = github_links(md(path.read_text(encoding="utf-8")), rel)
                docs.append(f'<section class="repodoc" id="{anchor}"><p class="meta"><code>{html.escape(rel)}</code> '
                            f'· dernier commit <code>{sha}</code> ({date}) · <a href="{GITHUB}{rel}">voir sur GitHub</a>'
                            f'</p>{prefixed(text, anchor)}</section>')
                subs.append((anchor, html.escape(rel)))
            body = "".join(docs)
        else:
            path = PED / "sources" / f"{key}.md"
            path = path if path.exists() else PED / f"{key}.md"
            body = prefixed(sources.get(key) or md(path.read_text(encoding="utf-8")), prefix)
            subs = headings(body, 2)
            sha, date = last_change(path)
            note = note.format(sha=sha, date=date)
        banner = f'<p class="partnote">{note}</p>' if note else ""
        parts.append(f'<section class="part" id="{prefix}"><p class="partlabel">Partie {n} — '
                     f'{html.escape(title)}</p>{banner}{body}</section>')
        items = "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in subs)
        toc.append(f'<li><a href="#{prefix}"><b>Partie {n} — {html.escape(title)}</b></a><ol>{items}</ol></li>')

    def span(kind: str) -> str:
        ns = kinds.get(kind, [])
        return f"Partie {ns[0]}" if len(ns) == 1 else f"Parties {ns[0]} à {ns[-1]}"
    cover = (f'<h1>AxiomEval — tout en un</h1><p>Tout ce qui est publié sur GitHub '
             f'(<a href="https://github.com/Tanjonyavo/AxiomEval">github.com/Tanjonyavo/AxiomEval</a>) dans un seul '
             f'fichier : guide, résultats, documents du dépôt, manuels et code expliqué ligne à ligne. Code exact au '
             f'commit <code>{commit}</code>. Chaque ligne du sommaire est un lien vers sa page.</p>'
             f'<div class="warn"><p><b>Ordre de lecture conseillé.</b> {span("guide")} d\'abord : elle explique tout '
             f'le projet et donne l\'état actuel. {span("repo")} : les documents du dépôt (résultats vérifiables, '
             f'sécurité, expériences, données, architecture, progression). {span("old")} : manuels plus anciens, '
             f'gardés tels quels, chacun avec sa date ; quand ils contredisent la partie 1, la partie 1 a raison. '
             f'{span("code")} : le code ligne à ligne, à consulter quand un passage renvoie à un fichier. '
             f'{span("index")} : quelles lignes sont expliquées.</p></div>'
             f'<h2>Sommaire</h2><ol class="toc alltoc">{"".join(toc)}</ol>')
    (OUT / "AxiomEval_Tout_En_Un.html").write_text(page("AxiomEval — tout en un", cover + "".join(parts)),
                                                   encoding="utf-8")


def write_index(stats: list[dict], commit: str) -> None:
    volume = {w: n for n, _, ws in VOLUMES for w in ws}
    total_sig = sum(s["significant"] for s in stats)
    total_exp = sum(s["explained"] for s in stats)
    rows = ["# Index du code expliqué", "",
            f"Mesuré automatiquement par `tools/pedagogie/build.py` au commit `{commit}`. Une ligne significative est "
            "une ligne non vide qui n'est pas un commentaire seul. Une ligne est « expliquée » si elle appartient à "
            "une plage commentée dans `docs/pedagogie/explications/`.", "",
            f"**Total : {len(stats)} fichiers, {sum(s['lines'] for s in stats)} lignes, {total_sig} lignes "
            f"significatives, {total_exp} expliquées ({100 * total_exp / max(total_sig, 1):.1f} %).**", "",
            "| Fichier | Lignes | Significatives | Expliquées | Semaine | Volume PDF | Commit | Couverture |",
            "|---|---:|---:|---:|---|---|---|---|"]
    for s in stats:
        pct = 100 * s["explained"] / max(s["significant"], 1)
        rows.append(f"| `{s['file']}` | {s['lines']} | {s['significant']} | {s['explained']} | {s['week']} | "
                    f"{volume.get(s['week'], '—')} | `{commit}` | {pct:.0f} % |")
    missing = [s["file"] for s in stats if s["explained"] < s["significant"]]
    rows += ["", f"## Fichiers incomplets ({len(missing)})", ""] + [f"- `{m}`" for m in missing]
    (PED / "INDEX_CODE_EXPLIQUE.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
