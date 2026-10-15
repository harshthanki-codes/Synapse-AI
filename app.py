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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root, .dark, body, .gradio-container {
    --background-fill-primary: #000000 !important;
    --background-fill-secondary: #0a0a0a !important;
    --border-color-primary: #27272a !important;
    --border-color-accent: #3f3f46 !important;
    --body-text-color: #ededed !important;
    --body-text-color-subdued: #a1a1aa !important;
    --button-primary-background-fill: #ededed !important;
    --button-primary-text-color: #000000 !important;
    --panel-background-fill: #000000 !important;
    --input-background-fill: #0a0a0a !important;
    font-family: 'Inter', sans-serif !important;
}

body, .gradio-container { 
    background-color: #000000 !important;
    background-image: none !important;
    color: #ededed !important;
    margin: 0 !important;
    padding: 20px !important;
    min-height: 100vh !important;
}

/* Ensure container has some breathing room */
.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
}

/* Make Chatbot compact so everything fits on one screen naturally */
.chatbot {
    height: 40vh !important;
    max-height: 500px !important;
    overflow-y: auto !important;
}

/* Sleek Minimal Header */
.glow-header {
    font-size: 2.5rem !important;
    font-weight: 600 !important;
    letter-spacing: -1.5px !important;
    background: linear-gradient(to right, #ffffff, #888888) !important;
    -webkit-background-clip: text !important;
    background-clip: text !important;
    color: transparent !important;
    text-align: center;
    margin-bottom: 5px !important;
}
.sub-header {
    color: #888888 !important;
    font-size: 0.85rem !important;
    text-align: center;
    letter-spacing: 2px;
    margin-bottom: 30px !important;
    text-transform: uppercase;
}

/* Minimalist Cards / Panels */
.glass { 
    background: #000000 !important; 
    border: 1px solid #27272a !important; 
    border-radius: 6px !important; 
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5) !important; 
    overflow: hidden;
    transition: all 0.2s ease !important;
}
.glass:hover {
    border-color: #3f3f46 !important;
}

/* Minimalist Inputs */
textarea, input, .dropdown {
    background-color: #0a0a0a !important;
    color: #ededed !important;
    border: 1px solid #27272a !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
    font-size: 0.9rem !important;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.5) !important;
}
textarea:focus, input:focus {
    border-color: #ededed !important;
    box-shadow: 0 0 0 1px #ededed !important;
    outline: none !important;
}

/* Tab Navigation */
.tab-nav {
    border-bottom: 1px solid #27272a !important;
    background: transparent !important;
}
.tab-nav button {
    color: #888888 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    font-weight: 500 !important;
    transition: color 0.2s ease !important;
    border-radius: 0 !important;
}
.tab-nav button.selected {
    color: #ededed !important;
    border-bottom: 2px solid #ededed !important;
}
.tab-nav button:hover {
    color: #ededed !important;
}

/* Primary Buttons */
.gradio-button.primary {
    background: #ededed !important;
    color: #000000 !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
}
.gradio-button.primary:hover {
    background: #ffffff !important;
    opacity: 0.9 !important;
    transform: none !important;
}

/* Message Bubbles */
.message-wrap .message.user {
    background: #27272a !important;
    color: #ededed !important;
    border-radius: 6px !important;
    border: 1px solid #3f3f46 !important;
}
.message-wrap .message.bot {
    background: #000000 !important;
    color: #ededed !important;
    border: 1px solid #27272a !important;
    border-radius: 6px !important;
}
"""

with gr.Blocks(title="Synapse AI Nexus") as demo:
    gr.HTML("<h1 class='glow-header'>SYNAPSE AI</h1><div class='sub-header'>Neural Interface Nexus</div>")
    
    with gr.Tabs(elem_classes="glass"):
        with gr.TabItem("📡 Core 1: Neural Researcher"):
            # Feature 1: Persona Selector
            persona_dropdown = gr.Dropdown(
                choices=["Standard Assistant", "Strict Architect", "Creative Visionary"], 
                value="Standard Assistant", 
                label="Select Agent Persona",
                info="Dynamically alters the agent's response behavior."
            )
            
            def chat_with_persona(message, history, persona):
                return chat_a1(message, history, persona)
                
            gr.ChatInterface(
                fn=chat_with_persona,
                additional_inputs=[persona_dropdown],
                examples=[
                    ["What's the best caching strategy for a read-heavy API?", "Standard Assistant"], 
                    ["How do I implement a circuit breaker?", "Strict Architect"]
                ]
            )

        with gr.TabItem("🧠 Core 2: Architect Dyad"):
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
            
        with gr.TabItem("💾 Core 3: Quantum Memory"):
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
        with gr.TabItem("🎙️ Core 4: Vocal Synthesizer"):
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
        with gr.TabItem("📊 Core 5: System Telemetry"):
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
