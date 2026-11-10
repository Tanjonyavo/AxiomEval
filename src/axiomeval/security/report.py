"""Security report per attack family, with exact bounds and release deltas (S7, spec §31.10)."""
from collections import defaultdict

from axiomeval.stats.paired import binomial_upper


def family_table(records: list[dict], alpha: float = 0.05) -> dict:
    """Unit reported: runs. Draws of one scenario are correlated, so bounds are optimistic."""
    table = defaultdict(lambda: {"runs": 0, "attempted": 0, "breaches": 0, "groups": set(), "channels": defaultdict(int)})
    for r in records:
        if r["kind"] != "attack":
            continue
        row = table[r["attack_family"]]
        row["runs"] += 1
        row["groups"].add(r["group_id"])
        row["attempted"] += int(r["security"]["attack_attempted"])
        row["breaches"] += int(r["security"]["attack_succeeded"])
        for channel in r["security"]["leak_channels"]:
            row["channels"][channel] += 1
        for breach in r["security"].get("breaches", ()):
            if breach not in ("assistant_output", "tool_arguments"):
                row["channels"][breach] += 1
    out = {}
    for family, row in sorted(table.items()):
        out[family] = {"groups": len(row["groups"]), "runs": row["runs"], "attempted": row["attempted"],
                       "breaches": row["breaches"], "breach_rate": row["breaches"] / row["runs"],
                       "breach_upper_bound": binomial_upper(row["breaches"], row["runs"], alpha),
                       "channels": dict(row["channels"])}
    return out


def findings(records: list[dict]) -> list[dict]:
    return [{"scenario_id": r["scenario_id"], "release_id": r["release_id"], "draw": r["draw"],
             "attack_family": r["attack_family"], "breaches": r["security"]["breaches"],
             "reasons": r["reasons"], "trace_digest": r["trace_digest"]}
            for r in records if r["permission"] == "VIOLATION"]


def markdown(reports: dict[str, list[dict]], alpha: float = 0.05) -> str:
    lines = ["# Rapport de sécurité", "",
             "Unité : exécution (un tirage d'un scénario). Les tirages d'un même scénario sont corrélés : les bornes "
             f"exactes à {int((1 - alpha) * 100)} % supposent des essais indépendants et sont donc optimistes.", "",
             "Une **tentative** a été stoppée par un contrôle (autorisation ou garde de sortie). Une **brèche** a eu "
             "un effet : secret ou donnée protégée divulgués, ou effet interdit exécuté.", ""]
    families = sorted({f for recs in reports.values() for f in family_table(recs, alpha)})
    header = "| Famille | " + " | ".join(reports) + " |"
    lines += ["## Brèches par famille (brèches / exécutions, borne supérieure)", "", header,
              "|---|" + "---|" * len(reports)]
    tables = {name: family_table(recs, alpha) for name, recs in reports.items()}
    for fam in families:
        cells = []
        for name in reports:
            row = tables[name].get(fam)
            cells.append(f"{row['breaches']}/{row['runs']} (≤ {row['breach_upper_bound']:.0%})" if row else "—")
        lines.append(f"| {fam} | " + " | ".join(cells) + " |")
    lines += ["", "## Tentatives stoppées par les contrôles", "", header, "|---|" + "---|" * len(reports)]
    for fam in families:
        cells = []
        for name in reports:
            row = tables[name].get(fam)
            cells.append(f"{row['attempted'] - row['breaches']}/{row['runs']}" if row else "—")
        lines.append(f"| {fam} | " + " | ".join(cells) + " |")
    lines += ["", "## Brèches observées", ""]
    for name, recs in reports.items():
        found = findings(recs)
        lines.append(f"- **{name}** : {len(found)} exécution(s) avec brèche")
        for f in found[:12]:
            lines.append(f"  - `{f['scenario_id']}` tirage {f['draw']} : {', '.join(f['breaches'])} "
                         f"(trace `{f['trace_digest'][:12]}`)")
    return "\n".join(lines) + "\n"
