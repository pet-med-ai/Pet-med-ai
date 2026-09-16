"""Synthetic tests for the new pure helper; never import the application.

Run directly with Python's standard library. The route wiring check parses
backend/main.py as text only: no FastAPI, database, AI, or old-module execution.
"""

import ast
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "history_merge_under_test", ROOT / "backend" / "consult_history_merge.py"
)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
merge = HELPER.preserve_consult_history

FIRST = "【动态问诊追问记录】\n1. 问：既往用药？\n   答：待核实。"
SECOND = FIRST + "\n2. 问：近期饮食？\n   答：主人报告更换过食物。"


class HistoryPreservationTests(unittest.TestCase):
    def test_empty_legacy_history_uses_current_snapshot(self):
        self.assertEqual(merge(None, FIRST), FIRST)
        self.assertEqual(merge("", FIRST), FIRST)

    def test_missing_generated_history_leaves_legacy_text_untouched(self):
        old = "  原始文字\r\n\r\n"
        for incoming in (None, "", " \r\n\t"):
            with self.subTest(incoming=incoming):
                self.assertEqual(merge(old, incoming), old)

    def test_identical_snapshot_is_a_noop(self):
        self.assertEqual(merge(FIRST, FIRST), FIRST)

    def test_structured_history_and_manual_notes_survive_update(self):
        old = FIRST + "\n\n【犬猫结构化问诊记录】\n用药史：待核实。\n医生补充：保留这段原文。"
        result = merge(old, SECOND)
        self.assertTrue(result.startswith(old))
        self.assertTrue(result.endswith(SECOND))
        self.assertEqual(result.count("医生补充：保留这段原文。"), 1)

    def test_repeated_update_does_not_append_the_same_snapshot(self):
        once = merge("人工病史", SECOND)
        self.assertEqual(merge(once, SECOND), once)

    def test_note_added_after_a_snapshot_does_not_defeat_deduplication(self):
        old = merge("人工病史", SECOND) + "\n\n之后追加的医生记录。"
        self.assertEqual(merge(old, SECOND), old)

    def test_substring_inside_a_sentence_is_not_a_complete_snapshot(self):
        incoming = "问：用药？ 答：待核实。"
        old = "引述前缀" + incoming + "引述后缀"
        result = merge(old, incoming)
        self.assertTrue(result.startswith(old))
        self.assertNotEqual(result, old)
        self.assertTrue(result.endswith(incoming))

    def test_new_answer_preserves_the_older_answer(self):
        revised = FIRST.replace("待核实。", "主人更正：已提供药品包装。")
        result = merge(FIRST, revised)
        self.assertTrue(result.startswith(FIRST))
        self.assertTrue(result.endswith(revised))
        self.assertEqual(merge(result, revised), result)

    def test_whitespace_unicode_and_marker_like_notes_are_preserved(self):
        originals = (
            "\t \r\n", "【动态问诊更新补充】\n医生手写同名标题",
            "犬🐕\r\n  原始空格  \r\n", "ｅ\u0301\n原始合成字符",
        )
        for old in originals:
            with self.subTest(old=old):
                result = merge(old, SECOND)
                self.assertEqual(result[:len(old)], old)
                self.assertEqual(merge(result, SECOND), result)

    def test_crlf_bounded_existing_snapshot_is_detected(self):
        old = "前言\r\n" + FIRST + "\r\n医生补充"
        self.assertEqual(merge(old, FIRST), old)

    def test_nontext_inputs_are_rejected_without_coercion(self):
        for value in ({"history": FIRST}, [FIRST], 7, False):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    merge(value, FIRST)
                with self.assertRaises(TypeError):
                    merge(FIRST, value)

    def test_update_route_uses_both_existing_and_generated_history(self):
        tree = ast.parse((ROOT / "backend" / "main.py").read_text(encoding="utf-8"))
        route = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "ai_consult_session_update_case"
        )
        assignments = [
            node for node in ast.walk(route)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "obj" and target.attr == "history"
                    for target in node.targets)
        ]
        self.assertEqual(len(assignments), 1)
        expected = ast.parse('proposed["history"]', mode="eval").body
        self.assertEqual(ast.dump(assignments[0].value), ast.dump(expected))
        snapshot = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_consult_update_snapshot")
        merges = [node for node in ast.walk(snapshot) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "preserve_consult_history"]
        self.assertEqual(len(merges), 2)
        self.assertEqual(ast.dump(merges[0]), ast.dump(ast.parse('preserve_consult_history(obj.history, case_fields["history"])', mode="eval").body))
        self.assertEqual(ast.dump(merges[1]), ast.dump(ast.parse('preserve_consult_history(proposed["history"], "【医生病史补记】\\n" + history_addendum)', mode="eval").body))
        calls = [node for node in ast.walk(route) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_consult_update_snapshot"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(ast.dump(calls[0]), ast.dump(ast.parse('_consult_update_snapshot(session, obj, case_fields, history_addendum)', mode="eval").body))


if __name__ == "__main__":
    unittest.main(verbosity=2)
