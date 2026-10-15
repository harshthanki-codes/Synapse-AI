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
    neutral_hue="neutral"
)

css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root, .dark, body, .gradio-container {
    --background-fill-primary: #070709 !important;
    --background-fill-secondary: #0d0d12 !important;
    --border-color-primary: #1f1f28 !important;
    --border-color-accent: #333342 !important;
    --body-text-color: #ededf0 !important;
    --body-text-color-subdued: #9da0ae !important;
    --button-primary-background-fill: #ffffff !important;
    --button-primary-text-color: #000000 !important;
    --panel-background-fill: #0c0c10 !important;
    --input-background-fill: #09090d !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

body, .gradio-container { 
    background-color: #070709 !important;
    background-image: radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.03) 0%, transparent 60%) !important;
    color: #ededf0 !important;
    margin: 0 !important;
    padding: clamp(12px, 2.5vw, 24px) !important;
    min-height: 100vh !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

/* Fluid responsive wrapper - stretches comfortably on wide screens without empty voids */
.gradio-container {
    max-width: 1360px !important;
    width: 100% !important;
    margin: 0 auto !important;
}

/* Sleek Responsive Header */
.glow-header {
    font-size: clamp(1.8rem, 4.5vw, 3rem) !important;
    font-weight: 700 !important;
    letter-spacing: -1.5px !important;
    background: linear-gradient(135deg, #ffffff 30%, #a1a1aa 100%) !important;
    -webkit-background-clip: text !important;
    background-clip: text !important;
    color: transparent !important;
    text-align: center;
    margin: 0 0 4px 0 !important;
    line-height: 1.15 !important;
}

.sub-header {
    color: #71717a !important;
    font-size: clamp(0.7rem, 1.8vw, 0.85rem) !important;
    text-align: center;
    letter-spacing: 2.5px;
    margin-bottom: clamp(16px, 3vw, 28px) !important;
    text-transform: uppercase;
    font-weight: 500;
}

/* Fluid Glass Panels with Subtle Borders */
.glass { 
    background: #0b0b0f !important; 
    border: 1px solid #1f1f28 !important; 
    border-radius: 12px !important; 
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6) !important; 
    overflow: hidden;
    padding: clamp(12px, 2vw, 20px) !important;
    margin-bottom: 16px !important;
}

/* Responsive Tab Navigation: NEVER clips into '...' */
.tab-nav, div[role="tablist"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    border-bottom: 1px solid #1f1f28 !important;
    background: transparent !important;
    padding: 6px 4px 12px 4px !important;
    width: 100% !important;
}

.tab-nav button, div[role="tablist"] button {
    font-size: clamp(0.8rem, 1.6vw, 0.95rem) !important;
    font-weight: 500 !important;
    padding: 8px 14px !important;
    border-radius: 8px !important;
    border: 1px solid transparent !important;
    color: #8f92a1 !important;
    background: transparent !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    white-space: nowrap !important;
    cursor: pointer !important;
}

.tab-nav button:hover, div[role="tablist"] button:hover {
    color: #ffffff !important;
    background: #14141c !important;
}

.tab-nav button.selected, div[role="tablist"] button.selected {
    color: #ffffff !important;
    background: #191924 !important;
    border-color: #2e2e3d !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5) !important;
}

/* Full Responsive Chatbot */
.chatbot, div[data-testid="chatbot"] {
    height: clamp(380px, 52vh, 600px) !important;
    min-height: 360px !important;
    border: 1px solid #1f1f28 !important;
    border-radius: 10px !important;
    background: #08080c !important;
    width: 100% !important;
}

/* Inputs, Textareas, and Dropdowns */
textarea, input, .dropdown {
    background-color: #0c0c12 !important;
    color: #ededed !important;
    border: 1px solid #22222d !important;
    border-radius: 8px !important;
    font-size: 0.92rem !important;
    transition: all 0.2s ease !important;
}

textarea:focus, input:focus {
    border-color: #4b4b60 !important;
    box-shadow: 0 0 0 1px #4b4b60 !important;
    outline: none !important;
}

/* Action Buttons */
.gradio-button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.18s ease !important;
    cursor: pointer !important;
}

.gradio-button.primary {
    background: #ffffff !important;
    color: #000000 !important;
    border: none !important;
}

.gradio-button.primary:hover {
    background: #e4e4e7 !important;
    transform: translateY(-1px);
}

/* Message Bubbles */
.message-wrap .message.user {
    background: #1a1a24 !important;
    color: #f4f4f5 !important;
    border-radius: 10px !important;
    border: 1px solid #2e2e3d !important;
}

.message-wrap .message.bot {
    background: #0e0e14 !important;
    color: #e4e4e7 !important;
    border: 1px solid #1f1f28 !important;
    border-radius: 10px !important;
}

/* Mobile & Tablet Specific Optimizations */
@media (max-width: 768px) {
    body, .gradio-container {
        padding: 8px 6px !important;
    }
    .glass {
        padding: 10px !important;
        border-radius: 8px !important;
    }
    .tab-nav, div[role="tablist"] {
        gap: 4px !important;
        overflow-x: auto !important;
        flex-wrap: nowrap !important;
        -webkit-overflow-scrolling: touch !important;
    }
    .tab-nav button, div[role="tablist"] button {
        padding: 7px 11px !important;
        font-size: 0.82rem !important;
    }
    .chatbot, div[data-testid="chatbot"] {
        height: 380px !important;
    }
    .glow-header {
        font-size: 1.7rem !important;
    }
    .sub-header {
        font-size: 0.7rem !important;
        letter-spacing: 1.5px;
    }
}
"""

with gr.Blocks(title="Synapse AI Nexus", fill_width=True) as demo:
    gr.HTML("<h1 class='glow-header'>SYNAPSE AI</h1><div class='sub-header'>Neural Interface Nexus</div>")
    
    with gr.Tabs(elem_classes="glass"):
        with gr.TabItem("📡 1. Neural Researcher"):
            # Feature 1: Persona Selector
            persona_dropdown = gr.Dropdown(
                choices=["Standard Assistant", "Strict Architect", "Creative Visionary"], 
                value="Standard Assistant", 
                label="Select Agent Persona",
                info="Dynamically alters the agent's response behavior."
            )
            
            def chat_with_persona(message, history, persona):
                return chat_a1(message, history, persona)
            
            chat_box = gr.Chatbot(height=480, render=False)
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

    # Feature 5: Live Status Footer
    gr.HTML("<div style='text-align: center; margin-top: 20px; font-weight: bold; color: #f97316; letter-spacing: 2px;'><span style='display:inline-block; width:10px; height:10px; background-color:#10b981; border-radius:50%; margin-right:8px; animation: pulse-glow 2s infinite;'></span> ALL NEURAL SYSTEMS ONLINE</div>")

if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        theme=custom_theme,
        css=css,
        js="function() { document.body.classList.add('dark'); }",
    )
