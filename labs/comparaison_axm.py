"""Comparer deux versions sur un plan synthétique apparié et préspécifié."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from itertools import product
import json
from math import ceil, fsum, isclose, log, sqrt
from pathlib import Path
from random import Random
from statistics import mean, variance

from axiomeval.errors import ValidationError
from axiomeval.ids import digest
from axiomeval.models.validation import text

COLUMNS = ("execution", "tache", "version", "repetition", "issue", "permission", "cout_unites")
ISSUES = ("SUCCES", "ECHEC", "TIMEOUT")
PERMISSIONS = ("OK", "VIOLATION", "INCERTAINE")
PARTITIONS = ("pilote", "evaluation")


@dataclass(frozen=True)
class Task:
    id: str
    groupe: str
    famille: str
    partition: str


@dataclass(frozen=True)
class Plan:
    id: str
    empreinte: str
    oracle: str
    reference: str
    candidate: str
    repetitions: int
    budget_groupes: int
    tirages: int
    graine: int
    alpha: float
    marge: float
    poids: dict[str, float]
    taches: dict[str, Task]


def fields(value, names, context):
    if not isinstance(value, dict) or value.keys() != set(names.split()):
        raise ValidationError(f"{context} : champs attendus {names}")
    return value


def integer(value, lower, upper, label):
    if type(value) is not int or not lower <= value <= upper:
        raise ValidationError(f"{label} : entier entre {lower} et {upper} attendu")
    return value


def proportion(value, label, *, strict=False):
    if type(value) not in (int, float) or not 0 <= value <= 1 or (strict and not 0 < value < 1):
        raise ValidationError(f"{label} : proportion admissible attendue")
    return float(value)


def unique_keys(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValidationError("Le plan contient une clé JSON en double")
    return obj


def load_plan(path):
    raw = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_keys)
    fields(raw, "schema synthetique id oracle reference candidate repetitions budget_groupes "
                "tirages_bootstrap graine alpha marge poids_familles taches", "Plan")
    if raw["synthetique"] is not True or type(raw["schema"]) is not int or raw["schema"] != 1:
        raise ValidationError("Le laboratoire accepte les plans synthétiques de schéma 1")
    reference, candidate = (text(raw[key], key) for key in ("reference", "candidate"))
    if reference == candidate:
        raise ValidationError("Le plan exige deux versions distinctes")

    weights = raw["poids_familles"]
    if not isinstance(weights, dict) or not weights:
        raise ValidationError("Le plan exige des poids de population par famille")
    normalized = {text(key, "famille"): proportion(value, key) for key, value in weights.items()}
    total = fsum(normalized.values())
    if len(normalized) != len(weights) or min(normalized.values()) <= 0 or not isclose(total, 1, rel_tol=0, abs_tol=1e-12):
        raise ValidationError("Les familles doivent être distinctes et leurs poids positifs de somme 1")
    weights = {key: normalized[key] / total for key in sorted(normalized)}

    if not isinstance(raw["taches"], list) or not raw["taches"]:
        raise ValidationError("Le plan doit déclarer les tâches attendues")
    tasks, group_design = {}, {}
    for row in raw["taches"]:
        fields(row, "id groupe famille partition", "Tâche")
        task = Task(**{key: text(value, key) for key, value in row.items()})
        if task.id in tasks or task.famille not in weights or task.partition not in PARTITIONS:
            raise ValidationError(f"Tâche dupliquée, famille ou partition invalide : {task.id}")
        design = (task.partition, task.famille)
        if group_design.setdefault(task.groupe, design) != design:
            raise ValidationError(f"Groupe partagé entre partitions ou familles : {task.groupe}")
        tasks[task.id] = task
    counts = Counter(group_design.values())
    if any(counts[partition, family] < 2 for partition, family in product(PARTITIONS, weights)):
        raise ValidationError("Chaque famille exige deux groupes distincts au minimum par partition")
    return Plan(
        text(raw["id"], "id"), digest(raw), text(raw["oracle"], "oracle"), reference, candidate,
        integer(raw["repetitions"], 1, 1000, "repetitions"),
        integer(raw["budget_groupes"], 2 * len(weights), 100_000, "budget_groupes"),
        integer(raw["tirages_bootstrap"], 200, 20_000, "tirages_bootstrap"),
        integer(raw["graine"], 0, 2**32 - 1, "graine"),
        proportion(raw["alpha"], "alpha", strict=True), proportion(raw["marge"], "marge"),
        weights, tasks,
    )


def load_trials(path, plan):
    rows, ids = {}, set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if reader.fieldnames != list(COLUMNS):
            raise ValidationError("En-tête du CSV d'exécutions invalide")
        for line, row in enumerate(reader, 2):
            if None in row or None in row.values():
                raise ValidationError(f"Colonnes manquantes ou excédentaires à la ligne {line}")
            row = {key: text(value, key) for key, value in row.items()}
            execution, task, version, rep, issue, permission, cost = (row[key] for key in COLUMNS)
            if task not in plan.taches or version not in (plan.reference, plan.candidate):
                raise ValidationError(f"Tâche ou version absente du plan à la ligne {line}")
            if not rep.isascii() or not rep.isdecimal() or not cost.isascii() or not cost.isdecimal():
                raise ValidationError(f"Répétition ou coût entier non négatif attendu à la ligne {line}")
            rep = integer(int(rep), 1, plan.repetitions, "repetition")
            cost = integer(int(cost), 0, 10**12, "cout_unites")
            key = (task, rep, version)
            if execution in ids or key in rows:
                raise ValidationError(f"Identifiant d'exécution ou membre d'une paire dupliqué à la ligne {line}")
            if issue not in ISSUES or permission not in PERMISSIONS:
                raise ValidationError(f"Issue ou observation de permission inconnue à la ligne {line}")
            spec = plan.taches[task]
            rows[key] = {
                **row, "repetition": rep, "cout_unites": cost, "succes": int(issue == "SUCCES"),
                "groupe": spec.groupe, "famille": spec.famille, "partition": spec.partition,
            }
            ids.add(execution)
    expected = len(plan.taches) * plan.repetitions * 2
    if len(rows) != expected:
        missing = next(key for key in product(sorted(plan.taches), range(1, plan.repetitions + 1),
                                               (plan.reference, plan.candidate)) if key not in rows)
        raise ValidationError(f"Exécution prévue absente : tâche={missing[0]}, répétition={missing[1]}, version={missing[2]}")
    return rows


def group_differences(plan, rows):
    groups = defaultdict(list)
    for task in sorted(plan.taches.values(), key=lambda item: item.id):
        pairs = (rows[task.id, rep, plan.candidate]["succes"] - rows[task.id, rep, plan.reference]["succes"]
                 for rep in range(1, plan.repetitions + 1))
        groups[task.partition, task.famille, task.groupe].append(fsum(pairs) / plan.repetitions)
    scores = {part: {family: [] for family in plan.poids} for part in PARTITIONS}
    for (part, family, _), differences in sorted(groups.items()):
        scores[part][family].append(mean(differences))
    return scores


def planning(weights, pilot, budget):
    """Minimiser la variance prévue sous coûts égaux et au moins deux groupes par strate."""
    terms = {family: weights[family] ** 2 * variance(pilot[family]) for family in weights}
    counts = dict.fromkeys(weights, 2)
    for _ in range(budget - sum(counts.values())):
        # La baisse marginale décroît dans chaque famille. Les plus grandes baisses
        # successives donnent un optimum entier pour ce budget en groupes.
        family = max(counts, key=lambda key: terms[key] / (counts[key] * (counts[key] + 1)))
        counts[family] += 1
    per_family, leftover = divmod(budget, len(weights))
    balanced = {family: per_family + int(i < leftover) for i, family in enumerate(weights)}
    return {
        "budget_groupes": budget,
        "allocation": counts, "allocation_equilibree": balanced,
        "variance_prevue": fsum(terms[h] / counts[h] for h in weights),
        "variance_equilibree": fsum(terms[h] / balanced[h] for h in weights),
    }


def compare(plan, evaluation):
    point = fsum(plan.poids[h] * mean(scores) for h, scores in evaluation.items())
    scale = fsum(plan.poids[h] ** 2 / len(scores) for h, scores in evaluation.items())
    radius = sqrt(-2 * log(plan.alpha) * scale)
    lower = max(-1., point - radius)
    rng = Random(plan.graine)
    samples = sorted(
        fsum(plan.poids[h] * mean(rng.choices(scores, k=len(scores))) for h, scores in evaluation.items())
        for _ in range(plan.tirages)
    )
    percentiles = [samples[max(0, ceil(p * plan.tirages) - 1)] for p in (plan.alpha / 2, 1 - plan.alpha / 2)]
    return {
        "ecart": point,
        "borne_inferieure_hoeffding": lower,
        "marge": plan.marge,
        "non_inferiorite": "demontree" if lower > -plan.marge else "inconclusive",
        "intervalle_bootstrap_approximatif": percentiles,
        "alpha": plan.alpha,
        "familles": {h: {"groupes": len(values), "poids": plan.poids[h], "ecart": mean(values)}
                     for h, values in evaluation.items()},
    }


def analyse(plan_path, trials_path):
    plan = load_plan(plan_path)
    rows = load_trials(trials_path, plan)
    scores = group_differences(plan, rows)
    executions = [row for _, row in sorted(rows.items())]
    usage = {}
    for part in PARTITIONS:
        selected = [row for row in executions if row["partition"] == part]
        usage[part] = {
            "executions": len(selected),
            "taches": len({row["tache"] for row in selected}),
            "groupes": sum(map(len, scores[part].values())),
            "cout_unites": sum(row["cout_unites"] for row in selected),
            "issues": {issue: sum(row["issue"] == issue for row in selected) for issue in ISSUES},
            "permissions": {status: sum(row["permission"] == status for row in selected)
                            for status in PERMISSIONS},
        }
    evaluation_permissions = usage["evaluation"]["permissions"]
    signal = ("violation_observee" if evaluation_permissions["VIOLATION"] else
              "observation_incertaine" if evaluation_permissions["INCERTAINE"] else "aucun_signal_observe")
    return {
        "schema": 1, "synthetique": True, "plan": plan.id, "oracle": plan.oracle,
        "versions": {"reference": plan.reference, "candidate": plan.candidate},
        "empreintes": {"plan": plan.empreinte,
                       "executions_normalisees": digest(executions)},
        "parametres": {"graine": plan.graine, "tirages_bootstrap": plan.tirages,
                       "repetitions_par_tache_et_version": plan.repetitions},
        "usage": usage,
        "signal_permissions_evaluation": signal,
        "comparaison_a_temps_fixe": compare(plan, scores["evaluation"]),
        "allocation_depuis_pilote": planning(plan.poids, scores["pilote"], plan.budget_groupes),
        "executions": executions,
    }


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--executions", required=True, type=Path)
    parser.add_argument("--sortie", type=Path)
    args = parser.parse_args()
    try:
        report = json.dumps(analyse(args.plan, args.executions), indent=2, ensure_ascii=False, allow_nan=False)
        if args.sortie:
            with args.sortie.open("x", encoding="utf-8") as stream:
                stream.write(report + "\n")
        else:
            print(report)
    except (ValidationError, ValueError, OSError, csv.Error) as error:
        parser.exit(2, f"Analyse refusée : {error}\n")


if __name__ == "__main__":
    main()
