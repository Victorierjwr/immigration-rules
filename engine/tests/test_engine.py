from datetime import date

import unittest

from engine.gap import analyze
from engine.gates import compile_expr, evaluate, run_gates
from engine.profile_map import age_years, clb_from_test, derived


def _cutoff_rows():
    return [
        {"draw_date": "2026-10-01", "round_type": "category", "category": "trades", "invitations": 3500,
         "cutoff": 476, "source_url": "https://example.com/1"},
        {"draw_date": "2026-10-15", "round_type": "category", "category": "french", "invitations": None,
         "cutoff": 435, "source_url": "https://example.com/2"},
        {"draw_date": "2025-11-01", "round_type": "category", "category": "french", "invitations": None,
         "cutoff": 420, "source_url": "https://example.com/3"},
        {"draw_date": "2026-10-15", "round_type": "program", "category": "cec", "invitations": 4000,
         "cutoff": 519, "source_url": "https://example.com/4"},
    ]


class GapTests(unittest.TestCase):
    def test_gap_to_latest_category(self):
        rows = _cutoff_rows()
        result = analyze(480, "canada", rows, category="trades")
        self.assertEqual(result["category"]["status"], "OK")
        self.assertEqual(result["category"]["gap"], 4)
        self.assertEqual(result["category"]["cutoff"], 476)
        # 项目轮参考应一并返回（cec 519）
        self.assertIn("general", result)
        self.assertEqual(result["general"]["cutoff"], 519)

    def test_category_no_draws_does_not_fabricate(self):
        rows = _cutoff_rows()
        result = analyze(450, "canada", rows, category="stem")
        self.assertEqual(result["category"]["status"], "CATEGORY_NO_DRAWS")
        self.assertNotIn("cutoff", result["category"])

    def test_no_category_filter_pools_all(self):
        rows = _cutoff_rows()
        result = analyze(478, "canada", rows)
        self.assertEqual(result["category"]["status"], "OK")
        self.assertEqual(result["category"]["cutoff"], 435)  # 最近类别轮
        self.assertEqual(result["general"]["cutoff"], 519)   # 最近项目轮

    def test_empty_rows_is_no_draws(self):
        result = analyze(480, "canada", [])
        self.assertEqual(result["category"]["status"], "CATEGORY_NO_DRAWS")
        self.assertNotIn("general", result)


class ProfileMapTests(unittest.TestCase):
    def test_age(self):
        self.assertGreaterEqual(age_years({"person": {"birth_date": "1998-05-14"}}), 28)
        self.assertEqual(age_years({"person": {}}), 0)

    def test_age_birthday_boundary(self):
        # 满周岁：生日当天才算满岁——2000 年出生，2026-01-01 时 25 岁，生日当天 26 岁
        self.assertEqual(age_years({"person": {"birth_date": "2000-12-31"}}, date(2026, 1, 1)), 25)
        self.assertEqual(age_years({"person": {"birth_date": "2000-12-31"}}, date(2026, 12, 31)), 26)

    def test_clb_ielts(self):
        clb = clb_from_test({
            "test": "ielts",
            "listening": 8.0, "reading": 7.0, "writing": 7.0, "speaking": 7.0,
        })
        self.assertEqual(clb, {"listening": 9, "reading": 9, "writing": 9, "speaking": 9})
        clb = clb_from_test({"test": "ielts", "listening": 6.0, "reading": 6.0, "writing": 6.0, "speaking": 6.0})
        self.assertTrue(all(v == 7 for v in clb.values()))
        clb = clb_from_test({"test": "ielts", "listening": 8.5, "reading": 8.0, "writing": 7.5, "speaking": 7.5})
        self.assertTrue(all(v == 10 for v in clb.values()))
        clb = clb_from_test({"test": "ielts", "listening": 4.0, "reading": 3.5, "writing": 4.0, "speaking": 4.0})
        self.assertEqual(clb, {"listening": 3, "reading": 4, "writing": 4, "speaking": 4})

    def test_clb_celpip_and_unknown(self):
        clb = clb_from_test({"test": "celpip", "listening": 12, "reading": 10, "writing": 9, "speaking": 11})
        self.assertEqual(clb, {"listening": 10, "reading": 10, "writing": 9, "speaking": 10})
        # v0 对未入库对照表的测试（TOEFL/PTE）不猜测，保持 None
        self.assertIsNone(clb_from_test({"test": "toefl"})["listening"])

    def test_derived(self):
        profile = {
            "person": {"birth_date": "1990-01-01", "spouse_profile": {"highest_degree": "bachelor"}},
            "language": {"english": {"test": "ielts", "listening": 6.0, "reading": 6.0,
                                     "writing": 6.0, "speaking": 6.0}},
            "work": {"years_in": {"CA": 3}},
        }
        d = derived(profile, ["CA"])
        self.assertEqual(d["clb_english_min"], 7)
        self.assertEqual(d["years_in_CA"], 3.0)
        self.assertEqual(d["spouse_education"], "bachelor")


class GateExprTests(unittest.TestCase):
    def _profile(self):
        return {"derived": {"clb_english_min": 7.0}, "education": {"eca_done": False}}

    def test_comparison_paths(self):
        p = self._profile()
        self.assertTrue(evaluate(compile_expr("derived.clb_english_min >= 7"), p))
        self.assertFalse(evaluate(compile_expr("derived.clb_english_min >= 8"), p))
        self.assertFalse(evaluate(compile_expr("derived.missing >= 7"), p))
        self.assertTrue(evaluate(compile_expr("not derived.missing >= 7"), p))
        self.assertTrue(evaluate(compile_expr("education.eca_done == false"), p))
        self.assertTrue(evaluate(compile_expr("100 - 40 >= 60"), p))
        self.assertTrue(evaluate(compile_expr("'completed' == 'completed'"), p))

    def test_logic_and_arith(self):
        p = self._profile()
        self.assertFalse(evaluate(compile_expr("a or b or derived.missing"), p))
        # None 参与算术 → None → 比较结果 False
        self.assertFalse(evaluate(compile_expr("70 - derived.missing < 71"), p))
        self.assertFalse(evaluate(compile_expr("derived.missing < 71"), p))
        self.assertTrue(evaluate(compile_expr("derived.missing == none"), p))

    def test_runner_pass_and_fail(self):
        gates = [
            {"id": "language", "test": "derived.clb_english_min >= 7",
             "fail_output": "语言不达标", "remedy_hint": "重考", "source_url": "https://x"},
            {"id": "eca", "test": "education.eca_done == true",
             "fail_output": "ECA 未做", "remedy_hint": "", "source_url": ""},
        ]
        self.assertEqual(
            run_gates(gates, {"derived": {"clb_english_min": 8}, "education": {"eca_done": True}}),
            [],
        )
        failures = run_gates(gates, {"derived": {"clb_english_min": 6}, "education": {"eca_done": False}})
        self.assertEqual({f["id"] for f in failures}, {"language", "eca"})

    def test_runner_broken_expr_fails_loud(self):
        broken = [{"id": "x", "test": "derived.a >=", "fail_output": "?", "source_url": ""}]
        failures = run_gates(broken, {})
        self.assertEqual(failures[0]["id"], "x")
        self.assertIn("表达式错误", failures[0]["fail_output"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
