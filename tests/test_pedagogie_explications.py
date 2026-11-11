"""Line-by-line explanations must match the code they explain.

Each file in docs/pedagogie/explications/ names the SHA-256 of the source it was
written against. When the source changes, its line numbers may shift: this test
fails until someone rereads the explanation, fixes its ranges and updates the
fingerprint (python tests/test_pedagogie_explications.py --print shows them).
"""
import hashlib
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPL = ROOT / "docs/pedagogie/explications"
RANGE = re.compile(r"^## L(\d+)(?:-L?(\d+))?\s*$", re.M)
FINGERPRINT = re.compile(r"<!-- source-sha256: ([0-9a-f]{64}) -->")


def source_of(explanation: Path) -> Path:
    return ROOT / explanation.stem.replace("__", "/")


def source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")).hexdigest()


@unittest.skipUnless(EXPL.is_dir(), "the teaching material (docs/pedagogie) is kept local and not published")
class ExplanationTests(unittest.TestCase):
    def test_every_explanation_matches_its_source(self):
        files = sorted(EXPL.glob("*.md"))
        self.assertTrue(files)
        for explanation in files:
            with self.subTest(explanation=explanation.name):
                source = source_of(explanation)
                self.assertTrue(source.exists(), f"{source} no longer exists")
                text = explanation.read_text(encoding="utf-8")
                found = FINGERPRINT.search(text)
                self.assertIsNotNone(found, "missing <!-- source-sha256: ... --> line")
                self.assertEqual(found.group(1), source_sha256(source),
                                 f"{source.relative_to(ROOT)} changed: reread the explanation, fix its ranges, "
                                 "then update the fingerprint")
                length = len(source.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n").split("\n"))
                previous_end = 0
                for match in RANGE.finditer(text):
                    start = int(match.group(1))
                    end = int(match.group(2) or start)
                    self.assertTrue(1 <= start <= end <= length, f"L{start}-L{end} outside 1..{length}")
                    self.assertGreater(start, previous_end, f"L{start}-L{end} overlaps or is out of order")
                    previous_end = end


if __name__ == "__main__":
    if "--print" in sys.argv:
        for explanation in sorted(EXPL.glob("*.md")):
            print(explanation.name, source_sha256(source_of(explanation)))
    else:
        unittest.main()
