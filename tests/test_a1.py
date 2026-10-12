import unittest
import importlib

a1 = importlib.import_module("assignment-1.agent")

class TestAssignment1(unittest.TestCase):
    def test_latency_budget_tool(self):
        res = a1.calculate_latency_budget.invoke({"db_read_ms": 100, "network_ms": 20, "compute_ms": 30})
        self.assertIn("150ms", res)

    def test_caching_strategies_tool(self):
        redis_res = a1.search_caching_strategies.invoke({"query": "read heavy redis workload"})
        self.assertIn("Redis is highly recommended", redis_res)
        
        general_res = a1.search_caching_strategies.invoke({"query": "general assets"})
        self.assertIn("CDN caching", general_res)

    def test_system_metrics_tool(self):
        metrics_res = a1.fetch_system_metrics.invoke({"system_name": "Cluster-A"})
        self.assertIn("Metrics for Cluster-A", metrics_res)

    def test_should_continue_limit(self):
        from langchain_core.messages import AIMessage
        state = {
            "messages": [AIMessage(content="test", tool_calls=[{"name": "mock", "args": {}, "id": "1"}])],
            "tool_call_count": 6
        }
        next_step = a1.should_continue(state)
        self.assertEqual(next_step, "__end__")

if __name__ == '__main__':
    unittest.main()
