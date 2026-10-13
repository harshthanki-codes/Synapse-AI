import unittest
import importlib
from pydantic import ValidationError

a2 = importlib.import_module("assignment-2.agent")


class TestAssignment2(unittest.TestCase):
    def test_review_result_schema(self):
        result = a2.ReviewResult(is_approved=True, reason="Code meets all type hint and style guidelines.")
        self.assertTrue(result.is_approved)
        self.assertIn("guidelines", result.reason)

    def test_review_result_invalid(self):
        with self.assertRaises(ValidationError):
            a2.ReviewResult(is_approved="not_a_bool_or_convertible_garbage", reason=123)

    def test_token_tracker_callback_legacy_and_gemini(self):
        tracker = a2.TokenTrackingCallback()

        class MockLegacyResponse:
            llm_output = {"token_usage": {"total_tokens": 128}}
            generations = []

        tracker.on_llm_end(MockLegacyResponse())
        self.assertEqual(tracker.total_calls, 1)
        self.assertEqual(tracker.total_tokens, 128)

        class MockGenMsg:
            usage_metadata = {"total_tokens": 72}

        class MockGen:
            message = MockGenMsg()

        class MockGeminiResponse:
            llm_output = None
            generations = [[MockGen()]]

        tracker.on_llm_end(MockGeminiResponse())
        self.assertEqual(tracker.total_calls, 2)
        self.assertEqual(tracker.total_tokens, 200)

    def test_ast_syntax_rejection_and_retry_loop(self):
        bad_state = {
            "task": "Write a function to add two ints",
            "worker_output": "def broken_syntax(a: int, b: int -> int:\n    return a + b",
            "revision_count": 0,
            "max_revisions": 2,
        }
        review_out = a2.reviewer_node(bad_state)
        self.assertEqual(review_out["review_verdict"], "rejected")
        self.assertIn("SyntaxError", review_out["review_reason"])

        merged_state = {**bad_state, **review_out}
        self.assertEqual(a2.should_retry_review(merged_state), "worker")

        exhausted_state = {**merged_state, "revision_count": 3}
        self.assertEqual(a2.should_retry_review(exhausted_state), "__end__")


if __name__ == "__main__":
    unittest.main()
