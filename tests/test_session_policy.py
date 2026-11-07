"""Observable recommendation contracts; no platform settings are changed."""
import unittest
from skills.optimax.scripts import session_policy as policy


class SessionPolicyTests(unittest.TestCase):
    def test_orchestrator_mapping(self):
        for platform, family, low_effort in (("claude", "haiku", "xhigh"), ("codex", "terra", "medium")):
            for complexity in ("low", "medium", "high", "super_high", None):
                with self.subTest(platform=platform, complexity=complexity):
                    result = policy.orchestrator_recommendation(platform, complexity)
                    self.assertEqual(result["family"], family if complexity == "low" else ("sonnet" if platform == "claude" else "terra"))
                    self.assertEqual(result["effort"], low_effort if complexity == "low" else "high")
                    self.assertTrue(result["reason"])
                    self.assertIs(result.get("applied"), False)
                    self.assertEqual(bool(result.get("assumption")), complexity is None)

    def test_native_context_retains_current_and_exposes_baseline(self):
        for platform, mode, model, effort in (("codex", "codex-ultra", "current-codex", "ultra"),
                                               ("claude", "claude-ultracode", "current-claude", "high")):
            for active in (True, None):
                with self.subTest(platform=platform, active=active):
                    result = policy.orchestrator_recommendation(platform, "high", dict(
                        mode=mode, active=active, model_id=model, effort=effort))
                    self.assertEqual((result["model_id"], result["effort"]), (model, effort))
                    self.assertEqual(result["native_context"]["active"], active)
                    self.assertEqual(result["baseline"]["effort"], "high")
                    self.assertFalse(result["applied"])
        off = policy.orchestrator_recommendation("codex", "low", dict(mode="codex-ultra", active=False))
        self.assertEqual((off["family"], off["effort"]), ("terra", "medium"))

    def test_native_context_validation(self):
        invalid = [True, {}, {"mode": "claude-ultracode", "active": False},
                   {"mode": "codex-ultra", "active": 1},
                   {"mode": "codex-ultra", "active": True},
                   {"mode": "codex-ultra", "active": None, "model_id": " ", "effort": "high"},
                   {"mode": "codex-ultra", "active": True, "model_id": "x", "effort": False},
                   {"mode": "codex-ultra", "active": False, "model_id": "x"},
                   {"mode": "codex-ultra", "active": False, "extra": 1}]
        for context in invalid:
            with self.subTest(context=context), self.assertRaises(ValueError):
                policy.orchestrator_recommendation("codex", "high", context)

    def test_advisor_mapping_and_consultation(self):
        ladders = {"claude": [("opus", "medium"), ("opus", "high"), ("opus", "xhigh")],
                   "codex": [("sol", "xhigh"), ("sol", "max"), ("astra", "max")]}
        for platform, ladder in ladders.items():
            for complexity, step in (("low", 0), ("medium", 0), ("high", 1), ("super_high", 2), (None, 0)):
                for purpose in ("planning", "design", "execution"):
                    for needed in (False, True):
                        with self.subTest(platform=platform, complexity=complexity, purpose=purpose, needed=needed):
                            result = policy.advisor_context(platform, complexity, purpose, needed)
                            required = purpose in ("planning", "design")
                            allowed = required or complexity != "low"
                            self.assertEqual(result["required"], required)
                            self.assertEqual(result["allowed"], allowed)
                            self.assertEqual(result["consult"], required or (allowed and needed))
                            self.assertEqual(result["starting_step"], step)
                            self.assertEqual((result["family"], result["effort"]), ladder[step])
                            self.assertEqual(result["advice_level"], "medium" if complexity in ("low", None) else complexity)
                            self.assertEqual(bool(result.get("assumption")), complexity is None)

    def test_invalid_inputs(self):
        for platform in ("", "Claude", "other", None, 1, [], {}):
            with self.subTest(platform=platform):
                with self.assertRaises(ValueError):
                    policy.orchestrator_recommendation(platform, "low")
                with self.assertRaises(ValueError):
                    policy.advisor_context(platform, "low", "planning")
        for complexity in ("", "super-high", 0, True, [], {}):
            with self.subTest(complexity=complexity):
                with self.assertRaises(ValueError):
                    policy.orchestrator_recommendation("codex", complexity)
                with self.assertRaises(ValueError):
                    policy.advisor_context("codex", complexity, "planning")
        for purpose in ("", "review", None, [], 1):
            with self.assertRaises(ValueError):
                policy.advisor_context("codex", "medium", purpose)
        for needed in (0, 1, None, "true", [], {}):
            with self.assertRaises(ValueError):
                policy.advisor_context("codex", "medium", "execution", needed)

    def test_fresh_return_values(self):
        first = policy.orchestrator_recommendation("codex")
        first["family"] = "changed"
        self.assertEqual(policy.orchestrator_recommendation("codex")["family"], "terra")
        first = policy.advisor_context("claude", None, "planning")
        first["family"] = "changed"
        self.assertEqual(policy.advisor_context("claude", None, "planning")["family"], "opus")


if __name__ == "__main__":
    unittest.main()
