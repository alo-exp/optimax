"""Packaged instruction-contract regressions; these do not prove host compliance."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReviewContractTests(unittest.TestCase):
    def assertIn(self, member, container, msg=None):
        self.assertTrue(member in container, msg or f"Missing contract: {member}")

    def assertNotIn(self, member, container, msg=None):
        self.assertTrue(member not in container, msg or f"Conflicting contract: {member}")

    def document(self, path):
        return re.sub(r"\s+", " ", (ROOT / path).read_text(encoding="utf-8")).lower()

    def test_controller_reservation_and_dispatch_outcomes_are_distinct(self):
        text = self.document("skills/optimax/references/calculator.md")
        for contract in (
            "legacy `launch` event is a reservation",
            "does not record host dispatch confirmation, failure, or cancellation",
            "unused reservations remain unused",
            "failed, uncertain, or cancelled dispatch",
            "do not invent an event or assessment",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, text)

    def test_fixed_review_uses_durable_report_without_contaminating_learning(self):
        text = self.document("skills/review-ladder/SKILL.md")
        for contract in (
            "fixed rung differs from adaptive selection",
            "ordinary durable review report",
            "actual host assignment id",
            "candidate, scope, pass",
            "dispatch outcome",
            "provider-effective settings as unknown",
            "never attach a mismatched reservation",
            "do not submit a score",
            "preserve the adaptive track",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, text)

    def test_optimax_entry_points_expose_limited_fixed_review_path(self):
        for path in ("skills/optimax/SKILL.md",
                     "skills/optimax/references/parallel-execution.md"):
            text = self.document(path)
            with self.subTest(path=path):
                self.assertIn("fixed user-directed review", text)
                self.assertIn("ordinary durable review report", text)
                self.assertIn("reservation", text)
                self.assertNotIn("follow the controller's failure and cancellation protocol", text)
        parallel = self.document("skills/optimax/references/parallel-execution.md")
        self.assertIn("does not record host dispatch confirmation, failure, or cancellation", parallel)

    def test_every_entry_point_distinguishes_matching_adaptive_and_report_only_reviews(self):
        paths = (
            "README.md",
            "skills/optimax/SKILL.md",
            "skills/optimax/references/calculator.md",
            "skills/optimax/references/parallel-execution.md",
            "skills/optimax/references/native-modes.md",
            "skills/optimax/references/platforms.md",
            "skills/optimax/references/policy.md",
            "skills/review-ladder/SKILL.md",
            "skills/review-ladder/references/report-template.md",
        )
        for path in paths:
            text = self.document(path)
            for contract in ("matching pre-dispatch adaptive reservation",
                             "policy is off", "report-only"):
                with self.subTest(path=path, contract=contract):
                    self.assertIn(contract, text)

    def test_fixed_selection_does_not_inherit_adaptive_upward_substitution(self):
        for path in ("skills/optimax/SKILL.md",
                     "skills/optimax/references/calculator.md",
                     "skills/optimax/references/platforms.md",
                     "skills/optimax/references/policy.md",
                     "skills/review-ladder/SKILL.md"):
            with self.subTest(path=path):
                self.assertIn("no upward substitution", self.document(path))
        native = self.document("skills/optimax/references/native-modes.md")
        self.assertNotIn("for every controlled stage, obtain a controller", native)
        self.assertNotIn("dispatch independent controlled stages in parallel only after preparation", native)

    def test_report_only_has_no_retroactive_learning_or_fabricated_identifiers(self):
        calculator = self.document("skills/optimax/references/calculator.md")
        self.assertIn("all existing eligibility rules", calculator)
        self.assertIn("no adaptive assessment even with a later receipt", calculator)
        self.assertIn("no controller run id or epoch", calculator)
        report = self.document("skills/review-ladder/references/report-template.md")
        for contract in ("dispatch outcome", "no returned assignment id",
                         "reservation", "no invented epoch"):
            with self.subTest(contract=contract):
                self.assertIn(contract, report)

    def test_readme_discloses_fixed_rung_controller_limit(self):
        text = self.document("README.md")
        self.assertIn("cannot represent every fixed review rung", text)
        self.assertIn("ordinary durable review report", text)
        self.assertIn("excluded from adaptive learning", text)


if __name__ == "__main__":
    unittest.main()
