import copy
import unittest

from skills.optimax.scripts.work_breakdown import readiness


def task(id, deps=(), paths=(), resources=()):
    return dict(id=id, outcome="deliver", acceptance="verify",
                dependencies=list(deps), complexity="low",
                write_paths=list(paths), resources=list(resources))


class ReadinessTests(unittest.TestCase):
    def test_occupancy_must_be_known_before_selecting_ready_work(self):
        plan = [task("native"), task("direct")]
        with self.assertRaisesRegex(ValueError, "other_inflight"):
            readiness(plan, [], ["native"], 2)
        with self.assertRaisesRegex(ValueError, "other_inflight"):
            readiness(plan, [], ["native"], 2, None)
        zero = readiness(plan, [], ["native"], 2, 0)
        self.assertEqual(zero["ready"], ["direct"])
        self.assertEqual(zero["used_capacity"], 2)
        occupied = readiness(plan, [], ["native"], 2, 1)
        self.assertEqual(occupied["ready"], [])
        self.assertEqual(occupied["status"]["direct"], "capacity")
        self.assertEqual(occupied["used_capacity"], 2)

    def test_branching_acceptance_and_running_capacity(self):
        plan = [task("a"), task("b"), task("next", ["a"])]
        self.assertEqual(readiness(plan, [], [], 2, 0)["ready"], ["a", "b"])
        self.assertEqual(readiness(plan, [], ["b"], 2, 0)["ready"], ["a"])
        result = readiness(plan, ["a"], ["b"], 2, 0)
        self.assertEqual(result["ready"], ["next"])
        self.assertEqual(result["used_capacity"], 2)
        self.assertEqual(readiness(plan, [], ["b"], 2, 0)["status"]["next"], "dependencies")
        self.assertEqual(readiness(plan, [], [], 2, 2)["ready"], [])

    def test_ownership_and_resources(self):
        plan = [task("a", paths=["src"]), task("b", paths=["src/file"]),
                task("c", paths=["other"], resources=["db"]),
                task("d", paths=["elsewhere"], resources=["db"])]
        result = readiness(plan, [], [], 4, 0)
        self.assertEqual(result["ready"], ["a", "c"])
        self.assertEqual(result["status"]["b"], "ownership")
        self.assertEqual(result["status"]["d"], "resources")
        self.assertEqual(readiness([task("a", paths=["src/a"]), task("b", paths=["src/ab"])], [], [], 2, 0)["ready"], ["a", "b"])
        self.assertEqual(readiness(plan, [], ["a"], 4, 0)["status"]["b"], "ownership")

    def test_invalid_inputs(self):
        invalid = [
            ([task("a"), task("a")], [], [], 2, 0),
            ([task("a", ["missing"])], [], [], 2, 0),
            ([task("a", ["b"]), task("b", ["a"])], [], [], 2, 0),
            ([task("a")], ["a"], ["a"], 2, 0),
            ([task("a")], ["missing"], [], 2, 0),
            ([task("a")], [], ["missing"], 2, 0),
            ([task("a")], [], ["a"], 0, 0),
            ([task("a")], [], [], -1, 0),
            ([task("a")], [], [], 1, 2),
            ([dict(task("a"), complexity="huge")], [], [], 1, 0),
            ([dict(task("a"), outcome=" ")], [], [], 1, 0),
            ([dict(task("a"), dependencies="a")], [], [], 1, 0),
            ([dict(task("a"), write_paths=[""])], [], [], 1, 0),
            ([dict(task("a"), resources=[1])], [], [], 1, 0),
            ([dict(task("a"), acceptance=None)], [], [], 1, 0),
        ]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValueError):
                readiness(*args)

    def test_empty_and_no_mutation(self):
        self.assertEqual(readiness([], [], [], 0, 0), {"ready": [], "status": {}, "used_capacity": 0})
        plan = [task("a"), task("b", ["a"])]
        accepted, running = ["a"], []
        before = copy.deepcopy((plan, accepted, running))
        readiness(plan, accepted, running, 2, 0)
        self.assertEqual((plan, accepted, running), before)

    def test_deep_chain_and_cycle(self):
        plan = [task(str(i), [str(i + 1)] if i < 1199 else [])
                for i in range(1200)]
        result = readiness(plan, [], [], 1, 0)
        self.assertEqual(result["ready"], ["1199"])
        self.assertEqual(result["status"]["0"], "dependencies")
        plan[-1]["dependencies"] = ["0"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            readiness(plan, [], [], 1, 0)


if __name__ == "__main__":
    unittest.main()
