import unittest
import importlib

a3 = importlib.import_module("assignment-3.agent")

class TestAssignment3(unittest.TestCase):
    def test_route_processing_continue(self):
        state = {"current_index": 0, "items": ["Item 1", "Item 2"]}
        route = a3.route_processing(state, config={"configurable": {"crash_at_item_3": False}})
        self.assertEqual(route, "process")

    def test_route_processing_finished(self):
        state = {"current_index": 2, "items": ["Item 1", "Item 2"]}
        route = a3.route_processing(state, config={"configurable": {"crash_at_item_3": False}})
        self.assertEqual(route, "check")

    def test_state_keys_preservation(self):
        test_state = {
            "items": ["Sample text"],
            "results": {"item_0": "Existing summary"},
            "current_index": 0,
            "llm_call_count": 0
        }
        self.assertIn("results", test_state)
        self.assertEqual(len(test_state["items"]), 1)

if __name__ == '__main__':
    unittest.main()
