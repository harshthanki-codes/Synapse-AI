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

    def test_token_tracker_callback(self):
        tracker = a2.TokenTrackingCallback()
        class MockResponse:
            llm_output = {"token_usage": {"total_tokens": 128}}
        tracker.on_llm_end(MockResponse())
        self.assertEqual(tracker.total_calls, 1)
        self.assertEqual(tracker.total_tokens, 128)

if __name__ == '__main__':
    unittest.main()
