import importlib
from langchain_core.runnables import RunnableConfig


def seed_default_checkpoint(thread_id: str = "seeded_demo_thread") -> dict:
    """Seeds the SQLite checkpointer with an initial resilient pipeline state."""
    a3 = importlib.import_module("assignment-3.agent")
    config = RunnableConfig(configurable={"thread_id": thread_id})
    initial_state = {
        "items": [
            "Company A reported a 20% increase in revenue driven by cloud adoption.",
            "Company B invested $2B into next-generation AI infrastructure.",
            "Company C restructured its hardware division for edge inference.",
        ],
        "results": {},
        "completed_items": {},
        "current_index": 0,
        "llm_call_count": 0,
    }
    a3.app.update_state(config, initial_state)
    return a3.app.get_state(config).values


if __name__ == "__main__":
    seeded = seed_default_checkpoint()
    print(f"Database seeded successfully with {len(seeded.get('items', []))} items.")
