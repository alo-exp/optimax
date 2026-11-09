"""Observable preparation, fail-closed capability, and receipt contracts."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'skills/optimax'
SPEC = importlib.util.spec_from_file_location("native_dispatch", ROOT / "scripts/native_dispatch.py")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


def reservation(platform="codex"):
    return dict(run_id="run-42", epoch="epoch-7", platform=platform, role="executor",
                family="codex" if platform == "codex" else "opus",
                model_id="codex-exact-v1" if platform == "codex" else "claude-opus-exact-v1",
                effort="xhigh" if platform == "codex" else "high", mode="direct")


def capabilities(platform="codex"):
    codex = platform == "codex"
    return dict(schema_verified=True, effective_settings_verified=True,
                effective_model_id="codex-exact-v1" if codex else "claude-opus-exact-v1",
                effective_effort="xhigh" if codex else "high",
                tool="collaboration.spawn_agent" if codex else "claude.agent",
                allowed_arguments=["model", "reasoning_effort", "message", "fork_turns"] if codex
                else ["model", "effort", "prompt"],
                required_arguments=["model", "reasoning_effort", "message", "fork_turns"] if codex
                else ["model", "effort", "prompt"],
                argument_map=dict(model="model", effort="reasoning_effort", prompt="message",
                                  fork="fork_turns") if codex else
                dict(model="model", effort="effort", prompt="prompt"),
                supported_models=["codex-exact-v1"] if codex else ["opus"],
                model_aliases={} if codex else {"claude-opus-exact-v1": "opus"},
                supported_efforts=["xhigh"] if codex else ["high"])


class DispatchTests(unittest.TestCase):
    def test_claude_advisor_max_requires_verified_support_and_exact_receipt(self):
        r = reservation("claude") | {"role": "advisor", "effort": "max"}
        c = capabilities("claude") | {"effective_effort": "max", "supported_efforts": ["high", "max"]}
        result = adapter.prepare_dispatch(r, "Review.", "claude-agent", c)
        self.assertEqual(result["arguments"]["effort"], "max")
        self.assertEqual(result["arguments"]["model"], "opus")
        receipt = dict(run_id=r["run_id"], epoch=r["epoch"], requested_model_id=r["model_id"],
                       requested_effort="max", effective_model_id=r["model_id"],
                       effective_effort="max", execution_id="native-max")
        self.assertEqual(adapter.validate_receipt(r, receipt), receipt)
        with self.assertRaises(ValueError):
            adapter.validate_receipt(r, receipt | {"effective_effort": "xhigh"})
        with self.assertRaisesRegex(ValueError, "effort"):
            adapter.prepare_dispatch(r, "Review.", "claude-agent", c | {"supported_efforts": ["high"]})

    def test_codex_exact_overrides_and_selfcontained_provenance(self):
        result = adapter.prepare_dispatch(reservation(), "Fix the exact brief.\nKeep tests.", "codex-spawn", capabilities())
        self.assertEqual(result["tool"], "collaboration.spawn_agent")
        self.assertEqual(set(result["arguments"]), {"model", "reasoning_effort", "message", "fork_turns"})
        self.assertEqual(result["arguments"]["model"], "codex-exact-v1")
        self.assertEqual(result["arguments"]["reasoning_effort"], "xhigh")
        self.assertEqual(result["arguments"]["fork_turns"], "none")
        for text in ("run-42", "epoch-7", "executor", "Fix the exact brief.\nKeep tests."):
            self.assertIn(text, result["arguments"]["message"])
        self.assertEqual(result["provenance"]["requested_model_id"], "codex-exact-v1")

    def test_supported_requested_controls_allow_dispatch_without_effective_evidence(self):
        for platform, route in (("codex", "codex-spawn"), ("claude", "claude-agent")):
            for evidence in ({}, {"effective_settings_verified": False},
                             {"effective_settings_verified": False,
                              "effective_model_id": None, "effective_effort": None}):
                c = capabilities(platform)
                for key in ("effective_settings_verified", "effective_model_id", "effective_effort"):
                    c.pop(key)
                c.update(evidence)
                with self.subTest(platform=platform, evidence=evidence):
                    try:
                        result = adapter.prepare_dispatch(reservation(platform), "Do the assigned work.", route, c)
                    except ValueError as exc:
                        self.fail("Supported requested controls must permit dispatch without effective evidence: " + str(exc))
                    self.assertEqual(result["arguments"]["model"], "codex-exact-v1" if platform == "codex" else "opus")
                    self.assertEqual(result["arguments"]["reasoning_effort" if platform == "codex" else "effort"],
                                     reservation(platform)["effort"])
                    if platform == "codex":
                        self.assertEqual(result["arguments"]["fork_turns"], "none")
                    self.assertIs(result["provenance"]["effective_settings_verified"], False)
                    for key in ("effective_model_id", "effective_effort", "execution_id"):
                        self.assertNotIn(key, result["provenance"])
                    with self.assertRaises(ValueError):
                        adapter.validate_receipt(reservation(platform), result["provenance"])

    def test_known_effective_override_blocks_even_without_verification_flag(self):
        for platform, route in (("codex", "codex-spawn"), ("claude", "claude-agent")):
            for key in ("effective_model_id", "effective_effort"):
                c = capabilities(platform)
                c.pop("effective_settings_verified")
                c[key] = "known-conflicting-override"
                with self.subTest(platform=platform, key=key), self.assertRaisesRegex(ValueError, key + ".*conflicts"):
                    adapter.prepare_dispatch(reservation(platform), "Work.", route, c)

    def test_requested_only_dispatch_preserves_schema_and_static_argument_fences(self):
        cases = (
            ({"schema_verified": False}, "verified actual tool schema"),
            ({"supported_models": []}, "requested model"),
            ({"supported_efforts": []}, "requested effort"),
            ({"static_arguments": {"model": "other"}}, "cannot override"),
            ({"static_arguments": {"fork_turns": "all"}}, "cannot override"),
            ({"static_arguments": {"unknown": "value"}}, "unsupported fields"),
        )
        for change, message in cases:
            c = capabilities()
            for key in ("effective_settings_verified", "effective_model_id", "effective_effort"):
                c.pop(key)
            c.update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                adapter.prepare_dispatch(reservation(), "Work.", "codex-spawn", c)

    def test_claude_explicit_supported_alias_and_actual_argument_mapping(self):
        c = capabilities("claude")
        c["argument_map"] = dict(model="model_name", effort="thinking_effort", prompt="task")
        c["allowed_arguments"] = ["model_name", "thinking_effort", "task"]
        c["required_arguments"] = list(c["allowed_arguments"])
        result = adapter.prepare_dispatch(reservation("claude"), "Research this.", "claude-agent", c)
        self.assertEqual(set(result["arguments"]), set(c["allowed_arguments"]))
        self.assertEqual(result["arguments"]["model_name"], "opus")
        self.assertEqual(result["arguments"]["thinking_effort"], "high")

    def test_flat_workflow_is_always_rejected_with_truthful_fallback(self):
        c = capabilities("claude")
        c["tool"] = "claude.workflow.stage"
        with self.assertRaisesRegex(ValueError, "WorkflowInput.*script.*scriptPath.*resumeFromRunId.*direct-agent"):
            adapter.prepare_dispatch(reservation("claude"), "Work.", "claude-workflow", c)

    def test_effective_settings_claims_never_attest_execution(self):
        for platform, route in (("codex", "codex-spawn"), ("claude", "claude-agent")):
            for verified in (True, False):
                c = capabilities(platform) | {"effective_settings_verified": verified}
                with self.subTest(platform=platform, verified=verified):
                    result = adapter.prepare_dispatch(reservation(platform), "Work.", route, c)
                    self.assertIs(result["provenance"]["effective_settings_verified"], False)
            c = capabilities(platform) | {"effective_settings_verified": 1}
            with self.subTest(platform=platform, malformed=True), self.assertRaisesRegex(ValueError, "effective"):
                adapter.prepare_dispatch(reservation(platform), "Work.", route, c)

    def test_role_specific_leaf_fence_in_every_brief(self):
        for platform, route in (("codex", "codex-spawn"), ("claude", "claude-agent")):
            for role in ("executor", "advisor"):
                r = reservation(platform)
                r["role"] = role
                result = adapter.prepare_dispatch(r, "Do the task.", route, capabilities(platform))
                prompt = result["arguments"]["message" if platform == "codex" else "prompt"]
                for term in ("root owns", "enable/off", "Advisor consultation", "WBS expansion", "dispatch", "runtime ledger", "inherited skills", "scheduler"):
                    with self.subTest(platform=platform, role=role, term=term):
                        self.assertIn(term, prompt)
                if role == "executor":
                    for term in ("no recursive delegation", "no Advisor", "request scope or replan from root"):
                        self.assertIn(term, prompt)
                else:
                    for term in ("read-only advice", "no implementation", "no mutations", "no recursive Advisor"):
                        self.assertIn(term, prompt)

    def test_effort_must_be_expressible_and_declared_supported(self):
        for route in ("claude-agent",):
            for change in ("mapping", "allowed", "supported"):
                c = capabilities("claude")
                if change == "mapping":
                    c["argument_map"].pop("effort")
                elif change == "allowed":
                    c["allowed_arguments"].remove("effort")
                else:
                    c["supported_efforts"] = ["low"]
                with self.subTest(route=route, change=change), self.assertRaisesRegex(ValueError, "effort"):
                    adapter.prepare_dispatch(reservation("claude"), "Work.", route, c)

    def test_codex_overrides_cannot_be_renamed_or_aliased(self):
        for change in ("renamed", "alias", "fork"):
            c = capabilities()
            if change == "renamed":
                c["argument_map"]["effort"] = "effort"
                c["allowed_arguments"].append("effort")
            elif change == "alias":
                c["model_aliases"] = {"codex-exact-v1": "codex"}
                c["supported_models"] = ["codex"]
            else:
                c["argument_map"].pop("fork")
            with self.subTest(change=change), self.assertRaises(ValueError):
                adapter.prepare_dispatch(reservation(), "Work.", "codex-spawn", c)

    def test_rejects_unsupported_routes_platforms_models_and_bad_input(self):
        cases = [
            (reservation(), "Work.", "unknown", capabilities()),
            (reservation("claude"), "Work.", "codex-spawn", capabilities()),
            (reservation(), "", "codex-spawn", capabilities()),
            (None, "Work.", "codex-spawn", capabilities()),
            (reservation(), "Work.", "codex-spawn", {}),
        ]
        c = capabilities()
        c["supported_models"] = []
        cases.append((reservation(), "Work.", "codex-spawn", c))
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                adapter.prepare_dispatch(*args)

    def test_rejects_missing_identity_and_duplicate_mapping(self):
        for key in ("run_id", "epoch", "role", "model_id", "effort", "family"):
            r = reservation()
            r.pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError):
                adapter.prepare_dispatch(r, "Work.", "codex-spawn", capabilities())
        c = capabilities("claude")
        c["argument_map"]["effort"] = "model"
        with self.assertRaisesRegex(ValueError, "distinct"):
            adapter.prepare_dispatch(reservation("claude"), "Work.", "claude-agent", c)

    def test_does_not_mutate_any_input_and_is_repeatable(self):
        args = [reservation(), "Work.", "codex-spawn", capabilities()]
        original = copy.deepcopy(args)
        self.assertEqual(adapter.prepare_dispatch(*args), adapter.prepare_dispatch(*args))
        self.assertEqual(args, original)

    def test_receipt_exact_consistency_does_not_attest_authenticity(self):
        r = reservation()
        receipt = dict(run_id=r["run_id"], epoch=r["epoch"], requested_model_id=r["model_id"],
                       requested_effort=r["effort"], effective_model_id=r["model_id"],
                       effective_effort=r["effort"], execution_id="native-123")
        self.assertEqual(adapter.validate_receipt(r, receipt), receipt)
        for key in receipt:
            bad = dict(receipt)
            bad[key] = "" if key == "execution_id" else "mismatch"
            with self.subTest(key=key), self.assertRaises(ValueError):
                adapter.validate_receipt(r, bad)
        missing = dict(receipt)
        missing.pop("effective_effort")
        with self.assertRaises(ValueError):
            adapter.validate_receipt(r, missing)

    def test_actual_tool_required_arguments_and_static_fields_are_checked(self):
        c = capabilities()
        c["allowed_arguments"].append("task_name")
        c["required_arguments"].append("task_name")
        with self.assertRaisesRegex(ValueError, "required"):
            adapter.prepare_dispatch(reservation(), "Work.", "codex-spawn", c)
        c["static_arguments"] = {"task_name": "run-42"}
        self.assertEqual(adapter.prepare_dispatch(reservation(), "Work.", "codex-spawn", c)["arguments"]["task_name"], "run-42")
        for static in ({"model": "different"}, {"unknown": "value"}):
            c["static_arguments"] = static
            with self.subTest(static=static), self.assertRaises(ValueError):
                adapter.prepare_dispatch(reservation(), "Work.", "codex-spawn", c)

    def test_invalid_modes_and_schema_shapes_block_with_fallback(self):
        r = reservation()
        r["mode"] = "unsupported-wrapper"
        with self.assertRaisesRegex(ValueError, "direct-agent"):
            adapter.prepare_dispatch(r, "Work.", "codex-spawn", capabilities())
        for key, value in (("schema_verified", 1), ("required_arguments", None),
                           ("allowed_arguments", "model"), ("supported_models", [None]),
                           ("model_aliases", []), ("static_arguments", [])):
            c = capabilities()
            c[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                adapter.prepare_dispatch(reservation(), "Work.", "codex-spawn", c)

    def test_cli_prepares_json_without_touching_input_or_creating_outputs(self):
        req = dict(reservation=reservation(), brief="Work.", route="codex-spawn", capabilities=capabilities())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            content = json.dumps(req)
            path.write_text(content)
            done = subprocess.run([sys.executable, str(ROOT / "scripts/native_dispatch.py"), str(path)],
                                  capture_output=True, text=True, check=False, cwd=directory)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)["arguments"]["fork_turns"], "none")
            self.assertEqual(path.read_text(), content)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_cli_invalid_request_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{}")
            done = subprocess.run([sys.executable, str(ROOT / "scripts/native_dispatch.py"), str(path)],
                                  capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 2)
            self.assertIn("error:", done.stderr)
            self.assertNotIn("Traceback", done.stderr)


if __name__ == "__main__":
    unittest.main()
