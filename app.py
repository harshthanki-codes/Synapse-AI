import gradio as gr
import importlib
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import json
import ast
import os
from config.settings import PERSONA_PROMPTS
from utils.helpers import clean_content, synthesize_speech_wav, telemetry_tracker

a1 = importlib.import_module("assignment-1.agent")
a2 = importlib.import_module("assignment-2.agent")
a3 = importlib.import_module("assignment-3.agent")


def build_message_history(history, system_prompt: str, current_message: str):
    """Converts Gradio chat history (tuples or message dicts) into LangChain messages."""
    messages = [SystemMessage(content=system_prompt)]
    if history:
        for entry in history:
            if isinstance(entry, (list, tuple)) and len(entry) == 2:
                user_msg, bot_msg = entry
                if user_msg:
                    messages.append(HumanMessage(content=str(user_msg)))
                if bot_msg:
                    messages.append(AIMessage(content=str(bot_msg)))
            elif isinstance(entry, dict):
                role = entry.get("role", "")
                text = clean_content(entry.get("content", ""))
                if role == "user" and text:
                    messages.append(HumanMessage(content=text))
                elif role in ("assistant", "bot") and text:
                    messages.append(AIMessage(content=text))
    messages.append(HumanMessage(content=current_message))
    return messages


def chat_a1(message, history, persona: str = "Standard Assistant"):
    base_persona = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["Standard Assistant"])
    system_prompt = (
        f"{base_persona} "
        "Drift AI is a cutting-edge AI research startup revolutionizing enterprise agentic architectures "
        "with production-grade LangGraph, resumable memory systems, and multi-agent dyads."
    )
    messages = build_message_history(history, system_prompt, message)
    state = {"messages": messages, "tool_call_count": 0, "should_fail": False}
    result = a1.app.invoke(state)
    return clean_content(result["messages"][-1].content)


def run_a2_interactive(
    task_text: str = "Write a python function that calculates the fibonacci sequence with type hints.",
    max_revisions: int = 1,
):
    if not task_text or not task_text.strip():
        task_text = "Write a python function that calculates the fibonacci sequence with type hints."
    state = {
        "task": task_text.strip(),
        "worker_output": "",
        "review_verdict": "",
        "review_reason": "",
        "revision_count": 0,
        "max_revisions": int(max_revisions),
    }
    result = a2.app.invoke(state)
    worker_clean = clean_content(result.get("worker_output", ""))
    revisions_used = result.get("revision_count", 1)

    is_approved = "approved" in str(result.get("review_verdict", "")).lower()
    verdict_md = (
        f"### {'✅ APPROVED' if is_approved else '❌ REJECTED'} "
        f"*(Pass #{revisions_used})*\n\n"
        f"**Reviewer Feedback:**\n> {result.get('review_reason', '')}"
    )
    return verdict_md, worker_clean


def run_a3_interactive(crash_toggle):
    from langchain_core.runnables import RunnableConfig
    config = RunnableConfig(configurable={"thread_id": "test_session_1", "crash_at_item_3": crash_toggle})
    
    if not crash_toggle and os.path.exists(".resumed"):
        try:
            os.remove(".resumed")
        except OSError:
            pass

    try:
        a3.app.invoke({"items": ["Company A experienced a 20% revenue growth.", "The new cloud division is profitable.", "Stock prices drop sharply."]}, config=config)
        
        final_state = a3.app.get_state(config).values
        completed = final_state.get("results") or final_state.get("completed_items", {})
        return json.dumps(completed, indent=2)
    except SystemExit:
        final_state = a3.app.get_state(config).values
        completed = final_state.get("results") or final_state.get("completed_items", {})
        return f"🚨 FATAL CRASH INTERCEPTED (Item #3)\n\nSystem state safely persisted to SQLite.\n\nDatabase Snapshot:\n{json.dumps(completed, indent=2)}\n\n(Uncheck 'Simulate Crash' and run again to watch the checkpointer perfectly resume.)"

custom_theme = gr.themes.Monochrome(
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "sans-serif"],
    primary_hue="neutral",
    secondary_hue="neutral",
    neutral_hue="neutral",
)

css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
    background-color: #050508 !important;
    color: #ededf0 !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}

:root, .dark, body, .gradio-container {
    --background-fill-primary: #050508 !important;
    --background-fill-secondary: #0a0a0f !important;
    --border-color-primary: #1c1c24 !important;
    --border-color-accent: #2e2e3a !important;
    --body-text-color: #ededf0 !important;
    --body-text-color-subdued: #8e90a0 !important;
    --button-primary-background-fill: #ffffff !important;
    --button-primary-text-color: #000000 !important;
    --panel-background-fill: #09090e !important;
    --input-background-fill: #07070b !important;
}

.gradio-container {
    height: 100vh !important;
    max-height: 100vh !important;
    display: flex !important;
    flex-direction: column !important;
    padding: 8px 18px !important;
    box-sizing: border-box !important;
    max-width: 1440px !important;
    width: 100% !important;
    margin: 0 auto !important;
    overflow: hidden !important;
}

/* Compact Top Brand Bar */
.top-brand-bar {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 4px 10px 8px 10px !important;
    border-bottom: 1px solid #181822 !important;
    flex-shrink: 0 !important;
}
.brand-title {
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    color: #ffffff !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}
.brand-badge {
    font-size: 0.68rem !important;
    background: #14141e !important;
    color: #a1a1aa !important;
    padding: 2px 7px !important;
    border-radius: 4px !important;
    border: 1px solid #222230 !important;
    letter-spacing: 0.5px !important;
}
.status-pill {
    display: inline-flex !important;
    align-items: center !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    color: #10b981 !important;
    gap: 5px !important;
}
.status-dot {
    width: 7px !important;
    height: 7px !important;
    background: #10b981 !important;
    border-radius: 50% !important;
    box-shadow: 0 0 8px #10b981 !important;
}

/* Single Screen Tabs Shell */
.main-tabs-shell {
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0 !important;
    margin-top: 6px !important;
    border: 1px solid #1a1a24 !important;
    border-radius: 10px !important;
    background: #08080d !important;
    overflow: hidden !important;
}

.main-tabs-shell > div:first-child {
    flex-shrink: 0 !important;
}

.tab-nav, div[role="tablist"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 4px !important;
    background: #06060a !important;
    padding: 4px 8px !important;
    border-bottom: 1px solid #181822 !important;
    overflow-x: auto !important;
}

.tab-nav button, div[role="tablist"] button {
    font-size: 0.85rem !important;
    padding: 6px 12px !important;
    border-radius: 6px !important;
    border: 1px solid transparent !important;
    color: #8b8e9e !important;
    background: transparent !important;
    white-space: nowrap !important;
    cursor: pointer !important;
}

.tab-nav button.selected, div[role="tablist"] button.selected {
    color: #ffffff !important;
    background: #151520 !important;
    border-color: #262638 !important;
}

/* Tab Panel Fills Remaining Height */
div[role="tabpanel"] {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    padding: 8px 12px !important;
    overflow: hidden !important;
}

/* One Screen Full Chat Panel */
.chat-container-split {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
    gap: 6px !important;
}

.persona-compact-row {
    flex-shrink: 0 !important;
    margin-bottom: 2px !important;
}

/* The Chatbot viewports auto-stretches to fill exact remaining height on screen */
.one-screen-chatbot, div[data-testid="chatbot"] {
    flex: 1 1 auto !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: calc(100vh - 240px) !important;
    border: 1px solid #181824 !important;
    border-radius: 8px !important;
    background: #050508 !important;
    overflow-y: auto !important;
}

/* Input Area */
textarea, input, .dropdown {
    background-color: #08080c !important;
    color: #ededed !important;
    border: 1px solid #1e1e2b !important;
    border-radius: 6px !important;
    font-size: 0.88rem !important;
}

textarea:focus, input:focus {
    border-color: #3b3b4f !important;
    box-shadow: 0 0 0 1px #3b3b4f !important;
    outline: none !important;
}

.gradio-button {
    border-radius: 6px !important;
    font-size: 0.86rem !important;
    font-weight: 600 !important;
}

/* Examples Table Compact */
div[data-testid="examples"] {
    flex-shrink: 0 !important;
    max-height: 90px !important;
    overflow-y: auto !important;
    margin-top: 4px !important;
}
"""

with gr.Blocks(title="Synapse AI Nexus", fill_width=True) as demo:
    gr.HTML(
        """
        <div class='top-brand-bar'>
            <div class='brand-title'>
                ⚡ SYNAPSE AI <span class='brand-badge'>NEURAL INTERFACE NEXUS</span>
            </div>
            <div class='status-pill'>
                <span class='status-dot'></span> ALL NEURAL SYSTEMS ONLINE
            </div>
        </div>
        """
    )
    
    with gr.Tabs(elem_classes="main-tabs-shell"):
        with gr.TabItem("📡 1. Neural Researcher"):
            with gr.Column(elem_classes="chat-container-split"):
                persona_dropdown = gr.Dropdown(
                    choices=["Standard Assistant", "Strict Architect", "Creative Visionary"], 
                    value="Standard Assistant", 
                    label="Active Persona",
                    elem_classes="persona-compact-row",
                )
                
                def chat_with_persona(message, history, persona):
                    return chat_a1(message, history, persona)
                
                chat_box = gr.Chatbot(elem_classes="one-screen-chatbot", render=False)
                gr.ChatInterface(
                    fn=chat_with_persona,
                    chatbot=chat_box,
                    additional_inputs=[persona_dropdown],
                    examples=[
                        ["What's the best caching strategy for a read-heavy API?", "Standard Assistant"], 
                        ["How do I implement a circuit breaker?", "Strict Architect"]
                    ]
                )

        with gr.TabItem("🧠 2. Architect Dyad"):
            with gr.Row(elem_classes="glass", variant="panel"):
                with gr.Column(scale=1):
                    gr.Markdown("### 👨‍💻 Adversarial Synthesis\nWatch two agents debate. The Worker writes Python, the Critic enforces strict architectural schemas and triggers self-correction.")
                    a2_task = gr.Textbox(
                        label="Engineering Task Specification",
                        value="Write a python function that calculates the fibonacci sequence with type hints.",
                        lines=2,
                    )
                    a2_revisions = gr.Slider(
                        minimum=0,
                        maximum=3,
                        value=1,
                        step=1,
                        label="Max Self-Correction Revisions",
                    )
                    a2_btn = gr.Button("⚡ Initialize Neural Dyad", variant="primary", size="lg")
                    a2_verdict = gr.Markdown("*(Awaiting Execution)*")
                with gr.Column(scale=2):
                    a2_code = gr.Code(label="Synthesized Architecture (Python)", language="python")
            a2_btn.click(run_a2_interactive, inputs=[a2_task, a2_revisions], outputs=[a2_verdict, a2_code])
            
        with gr.TabItem("💾 3. Quantum Memory"):
            with gr.Row(elem_classes="glass", variant="panel"):
                with gr.Column(scale=1):
                    gr.Markdown("### 🛡️ Indestructible Checkpointing\nProcesses data with SQLite checkpoints. Survives terminal crashes without losing state.")
                    a3_crash = gr.Checkbox(label="🔥 Simulate Kernel Panic (Crash at #3)?", value=True)
                    a3_btn = gr.Button("🔄 Execute Resilient Pipeline", variant="primary", size="lg")
                    reset_btn = gr.Button("🗑️ Reset Thread Checkpoint")
                    
                    # Feature 2: Memory Export
                    export_btn = gr.Button("📥 Export State to JSON")
                    export_out = gr.File(label="Exported SQLite Memory")
                    
                    def export_memory():
                        import tempfile
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w")
                        state_values = {}
                        try:
                            from langchain_core.runnables import RunnableConfig
                            cfg = RunnableConfig(configurable={"thread_id": "test_session_1"})
                            snapshot = a3.app.get_state(cfg)
                            if snapshot and snapshot.values:
                                state_values = snapshot.values
                        except Exception as e:
                            state_values = {"error": str(e)}
                            
                        export_data = {
                            "status": "exported",
                            "checkpoint_thread": "test_session_1",
                            "persisted_state": state_values or {"message": "No active state found yet; execute pipeline first."}
                        }
                        json.dump(export_data, tmp, indent=2)
                        tmp.close()
                        return tmp.name

                    def reset_memory_thread():
                        a3.reset_thread("test_session_1")
                        return json.dumps({"status": "reset", "thread_id": "test_session_1", "message": "Checkpoint cleared."}, indent=2)
                        
                    export_btn.click(export_memory, inputs=[], outputs=[export_out])
                    
                with gr.Column(scale=2):
                    a3_output = gr.Code(label="SQLite State Manifold", language="json")
            a3_btn.click(run_a3_interactive, inputs=a3_crash, outputs=a3_output)
            reset_btn.click(reset_memory_thread, inputs=[], outputs=a3_output)

        # Feature 3: Voice Synthesis Tab
        with gr.TabItem("🎙️ 4. Vocal Synthesizer"):
            with gr.Row(elem_classes="glass", variant="panel"):
                with gr.Column():
                    gr.Markdown("### 🗣️ Neural Text-to-Speech\nConvert agent responses into synthesized harmonic audio waveforms.")
                    voice_text = gr.Textbox(label="Input Text for Synthesis", lines=3, placeholder="Type here to synthesize voice...")
                    voice_btn = gr.Button("🔊 Synthesize Audio", variant="primary")
                    voice_out = gr.Audio(label="Synthesized Output", interactive=False)
                    
                    def run_voice_synthesis(text):
                        return synthesize_speech_wav(text)
                    
                    voice_btn.click(run_voice_synthesis, inputs=[voice_text], outputs=[voice_out])

        # Feature 4: Telemetry Dashboard
        with gr.TabItem("📊 5. System Telemetry"):
            with gr.Row(elem_classes="glass", variant="panel"):
                gr.Markdown("### 📈 Live Agent Telemetry & Resource Utilization")
                refresh_telemetry_btn = gr.Button("🔄 Refresh Live Telemetry", size="sm")
            with gr.Row():
                import pandas as pd

                def fetch_live_telemetry():
                    return pd.DataFrame(telemetry_tracker.get_rows())

                telemetry_df = gr.Dataframe(value=fetch_live_telemetry(), interactive=False)
                refresh_telemetry_btn.click(fetch_live_telemetry, inputs=[], outputs=[telemetry_df])


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        theme=custom_theme,
        css=css,
        js="function() { document.body.classList.add('dark'); }",
    )
