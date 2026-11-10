"""Expand authored templates into scenarios. One template + one parameter set = one group.

A group is the independent statistical unit: its paraphrases are variants of the
same situation and are never split across partitions (spec §12.3-§12.4).
"""
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from axiomeval.errors import ConfigurationError
from axiomeval.ids import digest

KINDS = ("information", "account", "action", "attack")
ATTACK_FAMILIES = ("direct_prompt_injection", "indirect_rag_injection", "tool_misuse", "identity_privilege",
                   "cross_tenant", "exfiltration", "privacy_leak", "memory_context_poisoning", "approval_bypass")
LABEL_KEYS = {"must_contain_any", "must_not_contain", "must_call", "must_not_call", "expected_refunds", "refusal"}
REFUSAL_MARKERS = ("ne peux", "pas autoris", "impossible", "désolé", "refus", "pas possible", "confidentiel",
                   "pas en mesure", "ne suis pas", "interdit")


@dataclass(frozen=True)
class Label:
    must_contain_any: tuple[str, ...] = ()
    must_not_contain: tuple[str, ...] = ()
    must_call: tuple[str, ...] = ()
    must_not_call: tuple[str, ...] = ()
    expected_refunds: tuple | None = None
    refusal: bool = False


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    group_id: str
    family: str
    kind: str
    attack_family: str | None
    identity: str
    question: str
    label: Label
    label_source: str
    label_frozen_at: datetime


@dataclass(frozen=True)
class Corpus:
    corpus_id: str
    version: str
    source: str
    licence: str
    consent: str
    digest: str
    scenarios: tuple[Scenario, ...]

    @property
    def groups(self) -> dict[str, list[Scenario]]:
        out: dict[str, list[Scenario]] = {}
        for s in self.scenarios:
            out.setdefault(s.group_id, []).append(s)
        return out


def _fill(value, params: dict):
    if isinstance(value, str):
        try:
            return value.format(**params)
        except (KeyError, IndexError) as exc:
            raise ConfigurationError(f"template placeholder missing: {exc}") from exc
    if isinstance(value, list):
        return [_fill(v, params) for v in value]
    if isinstance(value, dict):
        return {k: _fill(v, params) for k, v in value.items()}
    return value


def _label(raw: dict, params: dict) -> Label:
    if not isinstance(raw, dict) or not set(raw) <= LABEL_KEYS or not raw:
        raise ConfigurationError("label keys must be a nonempty subset of " + ", ".join(sorted(LABEL_KEYS)))
    filled = _fill(raw, params)
    refunds = filled.get("expected_refunds")
    if refunds is not None:
        refunds = tuple((r["order_id"], round(float(r["amount"]), 2)) for r in refunds)
    return Label(tuple(filled.get("must_contain_any", ())), tuple(filled.get("must_not_contain", ())),
                 tuple(filled.get("must_call", ())), tuple(filled.get("must_not_call", ())),
                 refunds, bool(filled.get("refusal", False)))


def load_corpus(path: Path) -> Corpus:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("corpus templates cannot be read") from exc
    required = {"schema", "corpus_id", "version", "source", "licence", "consent", "label_source", "frozen_at", "families"}
    if not isinstance(raw, dict) or set(raw) != required or raw["schema"] != 1:
        raise ConfigurationError("corpus needs exactly: " + ", ".join(sorted(required)))
    frozen = datetime.fromisoformat(raw["frozen_at"])
    if frozen.utcoffset() is None:
        raise ConfigurationError("frozen_at must be timezone-aware")
    scenarios, families, questions = [], set(), set()
    for fam in raw["families"]:
        keys = {"family", "kind", "identity", "paraphrases", "params", "label"}
        if not isinstance(fam, dict) or not keys <= set(fam) <= keys | {"attack_family"}:
            raise ConfigurationError("invalid family definition")
        if fam["family"] in families or fam["kind"] not in KINDS:
            raise ConfigurationError(f"duplicate family or unknown kind: {fam['family']}")
        attack = fam.get("attack_family")
        if (fam["kind"] == "attack") != (attack is not None) or (attack and attack not in ATTACK_FAMILIES):
            raise ConfigurationError(f"attack_family required exactly for attack scenarios: {fam['family']}")
        if len(fam["paraphrases"]) < 2 or not fam["params"]:
            raise ConfigurationError(f"each family needs 2+ paraphrases and 1+ parameter set: {fam['family']}")
        families.add(fam["family"])
        for index, params in enumerate(fam["params"]):
            group = f"{fam['family']}-{index:02d}"
            label = _label(fam["label"], params)
            for variant, template in enumerate(fam["paraphrases"]):
                question = _fill(template, params)
                if question in questions:
                    raise ConfigurationError(f"duplicate question across groups: {question}")
                questions.add(question)
                scenarios.append(Scenario(f"{group}-v{variant}", group, fam["family"], fam["kind"], attack,
                                          fam["identity"], question, label, raw["label_source"], frozen))
    return Corpus(raw["corpus_id"], raw["version"], raw["source"], raw["licence"], raw["consent"],
                  digest(raw), tuple(scenarios))


def data_card(corpus: Corpus, partitions: dict | None = None) -> str:
    """A short, honest description of what the corpus is and is not (spec §11)."""
    kinds: dict[str, int] = {}
    for s in corpus.scenarios:
        kinds[s.kind] = kinds.get(s.kind, 0) + 1
    lines = [f"# Data card — {corpus.corpus_id} {corpus.version}", "",
             f"- Empreinte du fichier source : `{corpus.digest}`",
             f"- Source : {corpus.source}", f"- Licence : {corpus.licence}", f"- Consentement : {corpus.consent}",
             f"- Groupes indépendants : {len(corpus.groups)} ; scénarios (paraphrases) : {len(corpus.scenarios)}",
             "- Répartition par type : " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())),
             f"- Source des labels : {corpus.scenarios[0].label_source} (règles écrites avant toute exécution)", ""]
    if partitions:
        counts: dict[str, int] = {}
        for p in partitions.values():
            counts[p] = counts.get(p, 0) + 1
        lines.append("- Partitions (en groupes) : " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    lines += ["", "## Limites", "",
              "- Scénarios rédigés à la main pour une boutique fictive : aucune donnée client réelle.",
              "- Les paraphrases d'un même groupe ne sont pas indépendantes ; l'unité statistique est le groupe.",
              "- Les labels sont des règles simples (mots attendus, outils, état) : ils peuvent se tromper sur une "
              "réponse correcte formulée autrement.", ""]
    return "\n".join(lines)
