# 🚀 Synapse-AI — Autonomous Agent Fleet

[![Live Demo](https://img.shields.io/badge/🤗%20Live%20Demo-Synapse--AI%20Studio-blue?style=for-the-badge)](https://huggingface.co/spaces/harshthanki-codes/Synapse-AI)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Production-00A67E?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Gradio](https://img.shields.io/badge/Gradio-UI-FF7F0E?style=flat-square&logo=gradio)](https://gradio.app)

> Production-grade autonomous multi-agent systems built with **LangGraph**, **Google Gemini**, and **Gradio**.

---

## 🎯 Live Demo

**👉 [Try the live app here](https://huggingface.co/spaces/harshthanki-codes/Synapse-AI)** — Chat with the agents, trigger code synthesis, and simulate crash recovery right in your browser. No setup required.

---

## 📋 Assignments

### 1. 🔍 Autonomous Research Agent
A research assistant that **dynamically selects tools** to answer complex technical queries.

| Feature | Implementation |
|---------|---------------|
| Tool Routing | LangGraph conditional edges with dynamic tool binding |
| Safety Limit | Hard 6-turn cap enforced at the graph routing level |
| Failure Recovery | Graceful fallback with mock-failure injection for resilience testing |
| Multi-Key Failover | 5 API keys with automatic LLM-level failover to prevent quota exhaustion |

### 2. ⚖️ Worker–Reviewer Dyad
A **two-agent pipeline** where one agent writes code and a second agent reviews it against strict criteria.

| Feature | Implementation |
|---------|---------------|
| Worker Agent | Generates Python code from a task description |
| Reviewer Agent | Validates output using `Pydantic BaseModel` structured output |
| Deterministic Verdicts | Reviewer forced into `{is_approved: bool, reason: str}` schema — no ambiguity |
| Token Tracking | Custom `BaseCallbackHandler` tracks total LLM calls and token usage |

### 3. 💾 Resumable Memory (Fault-Tolerant State)
Processes a data stream with **continuous SQLite checkpointing**. If the process crashes, it resumes from the exact point of failure without duplicating work.

| Feature | Implementation |
|---------|---------------|
| State Persistence | LangGraph `SqliteSaver` checkpointer writes state after every node |
| Crash Simulation | Toggle to deliberately kill the process at Item #3 |
| Zero-Duplication Resume | On restart, reads the checkpoint and skips already-completed items |
| Production Proof | Demonstrates enterprise-grade resilience for long-running pipelines |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Gradio Web Interface                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │ Chat Agent   │ │ Dyad Pipeline│ │ Resumable Memory │  │
│  └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘  │
│         │                │                   │            │
│  ┌──────▼───────┐ ┌──────▼───────┐ ┌────────▼─────────┐  │
│  │ LangGraph    │ │ LangGraph    │ │ LangGraph        │  │
│  │ StateGraph   │ │ StateGraph   │ │ StateGraph +     │  │
│  │ + Tools      │ │ + Pydantic   │ │ SqliteSaver      │  │
│  └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘  │
│         └────────────────┼──────────────────┘            │
│                   ┌──────▼───────┐                       │
│                   │ Google Gemini│                       │
│                   │ (Multi-Key)  │                       │
│                   └──────────────┘                       │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart (Local)

```bash
# Clone
git clone https://github.com/harshthanki-codes/Synapse-AI.git
cd Synapse-AI

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your GEMINI_API_KEY_1 through GEMINI_API_KEY_5

# Run
python app.py
```

## 🐳 Docker

```bash
docker-compose up
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Google Gemini 3.5 Flash Lite |
| **Orchestration** | LangGraph (StateGraph, conditional edges, checkpointers) |
| **Validation** | Pydantic BaseModel |
| **Persistence** | SQLite via `langgraph-checkpoint-sqlite` |
| **UI** | Gradio |
| **CI/CD** | GitHub Actions |
| **Containerization** | Docker + Docker Compose |

---

## 📄 License

MIT
