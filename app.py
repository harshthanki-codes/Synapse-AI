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
    font=[gr.themes.GoogleFont("Geist"), gr.themes.GoogleFont("Inter"), "ui-sans-serif", "sans-serif"],
    primary_hue="neutral",
    secondary_hue="neutral",
    neutral_hue="neutral",
)

css = """
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

*, *::before, *::after {
    box-sizing: border-box !important;
}

html, body {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
    background-color: #090a0f !important;
    background-image: 
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(120, 119, 198, 0.15), transparent),
        radial-gradient(circle at 100% 100%, rgba(16, 185, 129, 0.04), transparent 40%),
        radial-gradient(circle at 0% 100%, rgba(99, 102, 241, 0.04), transparent 40%) !important;
    color: #f1f2f6 !important;
    font-family: 'Geist', 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
    text-rendering: optimizeLegibility !important;
}

:root, .dark, body, .gradio-container {
    --background-fill-primary: #090a0f !important;
    --background-fill-secondary: #11121a !important;
    --border-color-primary: #1e202e !important;
    --border-color-accent: #2e3247 !important;
    --body-text-color: #f1f2f6 !important;
    --body-text-color-subdued: #9498ab !important;
    --button-primary-background-fill: #ffffff !important;
    --button-primary-text-color: #090a0f !important;
    --panel-background-fill: #0e0f17 !important;
    --input-background-fill: #11121a !important;
}

.gradio-container {
    height: 100vh !important;
    max-height: 100vh !important;
    display: flex !important;
    flex-direction: column !important;
    padding: 10px 24px 12px 24px !important;
    width: 100% !important;
    max-width: 1560px !important;
    margin: 0 auto !important;
    overflow: hidden !important;
}

/* ================= TOP COMMAND BAR ================= */
.top-command-bar {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 6px 14px 10px 14px !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    flex-shrink: 0 !important;
}

.brand-section {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
}

.brand-logo-mark {
    width: 26px !important;
    height: 26px !important;
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%) !important;
    border-radius: 6px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #ffffff !important;
    font-size: 14px !important;
    font-weight: 800 !important;
    box-shadow: 0 0 16px rgba(99, 102, 241, 0.4) !important;
}

.brand-name {
    font-size: 1.12rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
    color: #ffffff !important;
}

.brand-pill {
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    color: #818cf8 !important;
    background: rgba(99, 102, 241, 0.1) !important;
    border: 1px solid rgba(99, 102, 241, 0.25) !important;
    padding: 2px 8px !important;
    border-radius: 9999px !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
}

.meta-stats {
    display: flex !important;
    align-items: center !important;
    gap: 16px !important;
}

.system-status-indicator {
    display: inline-flex !important;
    align-items: center !important;
    gap: 7px !important;
    font-size: 0.76rem !important;
    font-weight: 500 !important;
    color: #34d399 !important;
    background: rgba(16, 185, 129, 0.08) !important;
    border: 1px solid rgba(16, 185, 129, 0.2) !important;
    padding: 3px 10px !important;
    border-radius: 9999px !important;
}

.pulsing-dot {
    width: 6px !important;
    height: 6px !important;
    background: #10b981 !important;
    border-radius: 50% !important;
    box-shadow: 0 0 8px #10b981 !important;
}

/* ================= MAIN INTERFACE DECK ================= */
.main-tabs-shell {
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
    min-height: 0 !important;
    margin-top: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 14px !important;
    background: rgba(14, 15, 23, 0.75) !important;
    backdrop-filter: blur(20px) !important;
    box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.7) !important;
    overflow: hidden !important;
}

.tab-nav, div[role="tablist"] {
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    background: rgba(10, 11, 16, 0.6) !important;
    padding: 8px 12px !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    flex-shrink: 0 !important;
}

.tab-nav button, div[role="tablist"] button {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    padding: 7px 14px !important;
    border-radius: 8px !important;
    border: 1px solid transparent !important;
    color: #8c90a3 !important;
    background: transparent !important;
    transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer !important;
}

.tab-nav button:hover, div[role="tablist"] button:hover {
    color: #ffffff !important;
    background: rgba(255, 255, 255, 0.04) !important;
}

.tab-nav button.selected, div[role="tablist"] button.selected {
    color: #ffffff !important;
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.12) !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4) !important;
}

div[role="tabpanel"] {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    padding: 12px 16px !important;
    overflow: hidden !important;
}

/* ================= CORE 1: DUAL-PANE PRODUCTION CHAT ================= */
.core1-dual-pane {
    display: grid !important;
    grid-template-columns: 280px 1fr !important;
    gap: 14px !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
    height: 100% !important;
}

.sidebar-controls {
    display: flex !important;
    flex-direction: column !important;
    gap: 12px !important;
    background: rgba(17, 18, 26, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 10px !important;
    padding: 14px !important;
    overflow-y: auto !important;
}

.sidebar-header {
    font-size: 0.74rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
    color: #6366f1 !important;
    margin-bottom: 2px !important;
}

.sidebar-card {
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 8px !important;
    padding: 10px 12px !important;
    font-size: 0.78rem !important;
    color: #9da1b6 !important;
    line-height: 1.45 !important;
}

.sidebar-card strong {
    color: #e2e4ee !important;
    font-weight: 600 !important;
}

.chat-stream-column {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
    height: 100% !important;
}

/* Production Chatbot Window filling full remaining height */
.production-chatbot, div[data-testid="chatbot"] {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    height: auto !important;
    max-height: none !important;
    background: rgba(10, 11, 17, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    border-radius: 10px !important;
    overflow-y: auto !important;
}

/* ================= MODERN CHAT BUBBLES ================= */
.message-wrap .message.user {
    background: #1e202e !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px 12px 2px 12px !important;
    padding: 10px 14px !important;
    font-size: 0.9rem !important;
    line-height: 1.5 !important;
}

.message-wrap .message.bot {
    background: rgba(17, 18, 27, 0.9) !important;
    color: #e6e8f2 !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 12px 12px 12px 2px !important;
    padding: 12px 16px !important;
    font-size: 0.9rem !important;
    line-height: 1.55 !important;
}

/* Input Bar Styling (Anthropic / OpenAI Style) */
textarea, input, .dropdown {
    background-color: #12131d !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    font-size: 0.9rem !important;
    transition: all 0.2s ease !important;
}

textarea:focus, input:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25) !important;
    outline: none !important;
}

/* Primary Action Buttons */
.gradio-button.primary {
    background: #ffffff !important;
    color: #090a0f !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    transition: all 0.15s ease !important;
    border: none !important;
}

.gradio-button.primary:hover {
    background: #f3f4f6 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(255, 255, 255, 0.15) !important;
}

/* Compact Examples Tray */
div[data-testid="examples"] {
    flex-shrink: 0 !important;
    max-height: 78px !important;
    overflow-y: auto !important;
    margin-top: 6px !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 8px !important;
    background: rgba(14, 15, 23, 0.4) !important;
}

div[data-testid="examples"] table {
    font-size: 0.78rem !important;
}
"""

with gr.Blocks(title="Synapse AI Nexus", fill_width=True) as demo:
    gr.HTML(
        """
        <div class='top-command-bar'>
            <div class='brand-section'>
                <div class='brand-logo-mark'>S</div>
                <div class='brand-name'>SYNAPSE AI</div>
                <div class='brand-pill'>Enterprise Agent Nexus</div>
            </div>
            <div class='meta-stats'>
                <div class='system-status-indicator'>
                    <span class='pulsing-dot'></span> CLUSTER OPERATIONAL
                </div>
            </div>
        </div>
        """
    )
    
    with gr.Tabs(elem_classes="main-tabs-shell"):
        with gr.TabItem("⚡ Autonomous Researcher"):
            with gr.Row(elem_classes="core1-dual-pane"):
                with gr.Column(elem_classes="sidebar-controls", scale=1):
                    gr.HTML("<div class='sidebar-header'>Agent Architecture</div>")
                    persona_dropdown = gr.Dropdown(
                        choices=["Standard Assistant", "Strict Architect", "Creative Visionary"], 
                        value="Standard Assistant", 
                        label="Active Persona",
                    )
                    gr.HTML(
                        """
                        <div class='sidebar-card'>
                            <strong>Model:</strong> Gemini Flash 2.5<br>
                            <strong>Routing:</strong> Dynamic LangGraph Edges<br>
                            <strong>Safety Bound:</strong> 6-Turn Max Tool Execution<br>
                            <strong>Multi-Key Failover:</strong> 5 Active Keys
                        </div>
                        <div class='sidebar-card'>
                            <strong>Production Tools:</strong><br>
                            • <code>calculate_latency_budget</code><br>
                            • <code>search_caching_strategies</code><br>
                            • <code>fetch_system_metrics</code>
                        </div>
                        """
                    )
                
                with gr.Column(elem_classes="chat-stream-column", scale=4):
                    def chat_with_persona(message, history, persona):
                        return chat_a1(message, history, persona)
                    
                    chat_box = gr.Chatbot(elem_classes="production-chatbot", render=False)
                    gr.ChatInterface(
                        fn=chat_with_persona,
                        chatbot=chat_box,
                        additional_inputs=[persona_dropdown],
                        examples=[
                            ["What's the best caching strategy for a read-heavy API?", "Standard Assistant"], 
                            ["How do I implement a circuit breaker?", "Strict Architect"]
                        ]
                    )

        with gr.TabItem("⚖️ Worker–Reviewer Dyad"):
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
