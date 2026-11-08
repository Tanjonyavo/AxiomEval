"""Contrôles du contrat apparié et des calculs hors ligne."""
import json
from math import isclose, log, sqrt
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from axiomeval.errors import ValidationError
from labs.comparaison_axm import analyse, load_plan, planning

FIXTURES = Path(__file__).resolve().parents[1] / "labs/fixtures_axm"


class ComparaisonAxmTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name)
        self.plan = FIXTURES / "plan.json"
        self.rows = FIXTURES / "executions.csv"

    def test_groupes_poids_et_hoeffding(self):
        result = analyse(self.plan, self.rows)
        comparison = result["comparaison_a_temps_fixe"]
        self.assertEqual(result["usage"]["evaluation"]["executions"], 52)
        self.assertEqual(result["usage"]["evaluation"]["taches"], 13)
        self.assertEqual(result["usage"]["evaluation"]["groupes"], 12)
        self.assertTrue(isclose(comparison["ecart"], .125))
        radius = sqrt(2 * log(20) * (.6**2 / 6 + .4**2 / 6))
        self.assertTrue(isclose(comparison["borne_inferieure_hoeffding"], .125 - radius))
        self.assertEqual(comparison["non_inferiorite"], "inconclusive")
        self.assertEqual(result["signal_permissions_evaluation"], "violation_observee")
        self.assertGreater(result["usage"]["evaluation"]["issues"]["TIMEOUT"], 0)

    def test_ordre_des_lignes(self):
        header, *rows = self.rows.read_text(encoding="utf-8").splitlines()
        other = self.temp / "ordre.csv"
        other.write_text("\n".join([header, *reversed(rows)]) + "\n", encoding="utf-8")
        self.assertEqual(analyse(self.plan, self.rows), analyse(self.plan, other))

    def test_disparition_d_une_tache_entiere(self):
        lines = self.rows.read_text(encoding="utf-8").splitlines()
        task = lines[1].split(",")[1]
        other = self.temp / "incomplet.csv"
        other.write_text("\n".join(line for line in lines if line.split(",")[1] != task), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "Exécution prévue absente"):
            analyse(self.plan, other)

    def test_fuite_par_groupe_et_reel_refuse(self):
        plan = json.loads(self.plan.read_text(encoding="utf-8"))
        first = next(task for task in plan["taches"] if task["partition"] == "pilote")
        second = next(task for task in plan["taches"] if task["partition"] == "evaluation")
        second["groupe"] = first["groupe"]
        modified = self.temp / "plan.json"
        modified.write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "Groupe partagé"):
            load_plan(modified)
        plan["synthetique"] = False
        modified.write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "plans synthétiques"):
            load_plan(modified)

    def test_doublon_d_execution(self):
        lines = self.rows.read_text(encoding="utf-8").splitlines()
        other = self.temp / "doublon.csv"
        other.write_text("\n".join([*lines, lines[1]]), encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "dupliqué"):
            analyse(self.plan, other)

    def test_allocation_entiere_optimale(self):
        weights = {"a": .65, "b": .35}
        scores = {"a": [-1, 0, 1], "b": [0, .25, .5]}
        result = planning(weights, scores, 17)
        costs = [.65**2 / a + .35**2 * .0625 / (17-a) for a in range(2, 16)]
        self.assertEqual(sum(result["allocation"].values()), 17)
        self.assertTrue(isclose(result["variance_prevue"], min(costs)))
        self.assertLess(result["variance_prevue"], result["variance_equilibree"])
