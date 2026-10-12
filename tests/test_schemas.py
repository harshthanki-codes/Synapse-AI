import unittest
from pydantic import ValidationError
import sys
import os
import importlib
a2 = importlib.import_module("assignment-2.agent")
ReviewVerdict = a2.ReviewVerdict

class TestSchemas(unittest.TestCase):
    def test_review_verdict_valid(self):
        verdict = ReviewVerdict(is_approved=True, reason="Looks good")
        self.assertTrue(verdict.is_approved)

if __name__ == '__main__':
    unittest.main()
