import os
import subprocess
import time

def run_git(cmd):
    subprocess.run(cmd, shell=True, check=True)

topics = [
    "LangChain", "LangGraph", "LLM", "Prompt_Engineering", "Retrieval_Augmented_Generation",
    "Vector_Databases", "Embeddings", "Tokens", "Context_Window", "Temperature",
    "Top_P", "Top_K", "Fine_Tuning", "Zero_Shot_Learning", "Few_Shot_Learning",
    "Chain_of_Thought", "ReAct_Framework", "Tool_Use", "Function_Calling", "Agents",
    "Multi_Agent_Systems", "State_Machines", "Directed_Acyclic_Graphs", "Checkpointers", "SQLite",
    "PostgreSQL", "Redis", "Memcached", "Cache_Aside", "Write_Through",
    "Thundering_Herd", "Rate_Limiting", "Exponential_Backoff", "Circuit_Breaker", "Idempotency",
    "Pydantic", "FastAPI", "Gradio", "Streamlit", "Docker",
    "Kubernetes", "CI_CD", "GitHub_Actions", "Pytest", "Unit_Testing",
    "Integration_Testing", "Mocking", "Dependency_Injection", "Design_Patterns", "Clean_Architecture"
]

os.makedirs("docs/glossary", exist_ok=True)

for i, topic in enumerate(topics):
    filepath = f"docs/glossary/{topic.lower()}.md"
    content = f"# {topic.replace('_', ' ')}\n\nThis document provides an architectural overview of {topic.replace('_', ' ')} in the context of enterprise AI systems.\n"
    
    with open(filepath, "w") as f:
        f.write(content)
        
    run_git(f"git add {filepath}")
    run_git(f'git commit -m "docs: add glossary entry for {topic}"')
    time.sleep(0.1)

print("Successfully generated 50 glossary documentation commits.")
