"""
InterviewPilot — Streamlit UI Application Entry Point.

Manages setup, interactive chat interview, and final report rendering screens
using st.session_state and LangGraph application services.
"""

from __future__ import annotations

import json
import streamlit as st

from agents.coach import generate_coaching_report
from models.candidate import CandidateProfile, FocusArea
from models.interview_state import InterviewState, InterviewStatus
from orchestration.graph import run_answer_turn, run_start_interview
from services.session_service import save_session
from services.pdf_service import generate_report_pdf


GLOBAL_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons+Round');

/* ── Self-collapsing injection (removes blank space Streamlit creates) ─ */
[data-testid="stMarkdownContainer"]:has(> style:only-child) {
    display: none !important; height: 0 !important; overflow: hidden !important;
}

/* ── Global font ─────────────────────────────────────────────────────── */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Inter', sans-serif !important;
}

/* ── Design tokens ───────────────────────────────────────────────────── */
:root {
    --accent:       #E8856A;
    --accent-lt:    #F2A484;
    --accent-dk:    #D4674E;
    --bg:           #FAF7F4;
    --card:         rgba(255,255,255,0.78);
    --glass:        rgba(255,255,255,0.55);
    --border:       rgba(232,133,106,0.18);
    --border-gl:    rgba(255,255,255,0.45);
    --shadow-sm:    0 4px 16px rgba(232,133,106,0.10);
    --shadow-md:    0 8px 32px rgba(232,133,106,0.15);
    --shadow-lg:    0 16px 48px rgba(232,133,106,0.22);
    --text-1:       #2D2A26;
    --text-2:       #6B6560;
    --text-3:       #9B9490;
    --grad-hero:    linear-gradient(135deg,#FAF7F4 0%,#F5EDE6 60%,#EDD9CC 100%);
    --grad-accent:  linear-gradient(135deg,#E8856A 0%,#F2A484 100%);
    --grad-card:    linear-gradient(145deg,rgba(255,255,255,0.92) 0%,rgba(255,255,255,0.68) 100%);
}

/* ── Glassmorphism card ──────────────────────────────────────────────── */
.ip-card {
    background: var(--grad-card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border-gl);
    border-radius: 24px;
    padding: 1.75rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow-md);
    transition: box-shadow .25s ease, transform .25s ease;
}
.ip-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }

/* ── Stat pill ───────────────────────────────────────────────────────── */
.ip-stat {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg,rgba(255,255,255,.90),rgba(242,164,132,.12));
    border: 1px solid rgba(232,133,106,.20);
    border-radius: 50px;
    padding: 7px 18px;
    font-size: .82rem;
    font-weight: 500;
    color: var(--text-1);
    box-shadow: 0 2px 8px rgba(232,133,106,.10);
}
.ip-stat .material-icons-round { font-size: 15px; color: var(--accent); }

/* ── Header ──────────────────────────────────────────────────────────── */
.ip-header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 0 4px 0;
}
.ip-header h1 {
    margin: 0;
    font-size: 1.9rem;
    font-weight: 700;
    background: var(--grad-accent);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -.5px;
}

/* ── Icon helpers ────────────────────────────────────────────────────── */
.mi    { vertical-align: middle; font-size: 18px !important; color: var(--accent); margin-right: 4px; }
.mi-lg { vertical-align: middle; font-size: 24px !important; color: var(--accent); margin-right: 6px; }

/* ── Question bubble ─────────────────────────────────────────────────── */
.ip-question-bubble {
    background: linear-gradient(135deg,rgba(255,255,255,.95),rgba(242,164,132,.08));
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-left: 4px solid var(--accent);
    border-radius: 0 20px 20px 0;
    padding: 1.25rem 1.5rem;
    margin: .8rem 0;
    font-size: 1rem;
    line-height: 1.65;
    color: var(--text-1);
    box-shadow: var(--shadow-sm);
}

/* ── Transcript bubbles ──────────────────────────────────────────────── */
.ip-history-q {
    background: linear-gradient(135deg,rgba(255,255,255,.9),rgba(232,133,106,.05));
    border-left: 3px solid var(--accent-lt);
    border-radius: 0 16px 16px 0;
    padding: .75rem 1.2rem;
    margin: .35rem 0;
    font-size: .9rem;
    color: var(--text-1);
}
.ip-history-a {
    background: linear-gradient(135deg,rgba(255,255,255,.9),rgba(120,193,149,.08));
    border-left: 3px solid #78C195;
    border-radius: 0 16px 16px 0;
    padding: .75rem 1.2rem;
    margin: .35rem 0 .8rem 0;
    font-size: .9rem;
    color: var(--text-1);
}

/* ── Voice banner ────────────────────────────────────────────────────── */
.ip-voice-banner {
    display: flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg,rgba(255,255,255,.9),rgba(232,133,106,.07));
    border: 1px solid rgba(232,133,106,.20);
    border-radius: 16px;
    padding: 11px 18px;
    font-size: .88rem;
    color: var(--text-2);
    margin: 8px 0;
    backdrop-filter: blur(8px);
}
.ip-voice-banner .material-icons-round { color: var(--accent); font-size: 20px; }

/* ── Progress bar ────────────────────────────────────────────────────── */
.stProgress > div > div { background: var(--grad-accent) !important; border-radius: 100px !important; }
.stProgress > div { border-radius: 100px !important; background: rgba(232,133,106,.12) !important; height: 6px !important; }

/* ── Buttons ─────────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: 16px !important;
    font-weight: 600 !important;
    font-size: .9rem !important;
    border: 1px solid rgba(232,133,106,.30) !important;
    transition: all .25s cubic-bezier(.4,0,.2,1) !important;
    background: var(--card) !important;
    color: var(--text-1) !important;
}
.stButton > button:hover {
    background: var(--grad-accent) !important;
    color: #fff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(232,133,106,.35) !important;
    border-color: transparent !important;
}
.stButton > button[kind="primary"] {
    background: var(--grad-accent) !important;
    color: #fff !important;
    border-color: transparent !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ── Form inputs ─────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 14px !important;
    border: 1.5px solid rgba(232,133,106,.22) !important;
    background: rgba(255,255,255,.80) !important;
    backdrop-filter: blur(8px) !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color .2s ease, box-shadow .2s ease !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(232,133,106,.15) !important;
}
.stSelectbox > div > div {
    border-radius: 14px !important;
    border: 1.5px solid rgba(232,133,106,.22) !important;
    background: rgba(255,255,255,.80) !important;
}

/* ── Metric cards ────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--card) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-radius: 20px !important;
    padding: 1.1rem 1.4rem !important;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stMetricLabel"] { font-size: .8rem !important; color: var(--text-2) !important; font-weight: 500 !important; }
[data-testid="stMetricValue"] { font-weight: 700 !important; color: var(--text-1) !important; }

/* ── File uploader ───────────────────────────────────────────────────── */
[data-testid="stFileUploaderDropzone"] {
    border-radius: 16px !important;
    border: 2px dashed rgba(232,133,106,.35) !important;
    background: rgba(255,255,255,.60) !important;
    backdrop-filter: blur(8px) !important;
    transition: border-color .2s ease !important;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--accent) !important; }

/* ── Expander ────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border-radius: 18px !important;
    border: 1px solid var(--border) !important;
    overflow: hidden !important;
    background: var(--card) !important;
}

/* ── Camera ──────────────────────────────────────────────────────────── */
[data-testid="stCameraInput"] button { display: none !important; }
[data-testid="stCameraInput"] { border-radius: 24px !important; overflow: hidden !important; }

/* ── Alerts ──────────────────────────────────────────────────────────── */
[data-testid="stAlert"], .stSuccess, .stWarning, .stError { border-radius: 16px !important; }

/* ── Download button ─────────────────────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
    border-radius: 16px !important;
    background: var(--card) !important;
    border: 1px solid rgba(232,133,106,.30) !important;
    font-weight: 600 !important;
    transition: all .25s ease !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: var(--grad-accent) !important;
    color: #fff !important;
    border-color: transparent !important;
    box-shadow: var(--shadow-md) !important;
}

/* ── Chat input ──────────────────────────────────────────────────────── */
[data-testid="stChatInput"] > div {
    border-radius: 20px !important;
    border: 1.5px solid rgba(232,133,106,.25) !important;
    background: rgba(255,255,255,.85) !important;
}

/* ── Charts ──────────────────────────────────────────────────────────── */
[data-testid="stVegaLiteChart"] {
    border-radius: 20px !important;
    overflow: hidden !important;
    padding: 1rem !important;
    background: var(--card) !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ── Divider ─────────────────────────────────────────────────────────── */
hr { border-color: rgba(232,133,106,.15) !important; margin: 1.25rem 0 !important; }

/* ── Scrollbar ───────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(232,133,106,.30); border-radius: 100px; }
::-webkit-scrollbar-thumb:hover { background: rgba(232,133,106,.55); }
</style>"""


def icon(name: str, size: str = "") -> str:
    """Return an inline Material Icon span."""
    cls = f"material-icons-round mi {size}"
    return f'<span class="{cls}">{name}</span>'


def icon_lg(name: str) -> str:
    return icon(name, "mi-lg")


# --- Streamlit Session State & Helper Functions ---

def init_session_state():
    """Safely initialize session state keys."""
    if "interview_state" not in st.session_state:
        st.session_state["interview_state"] = None


def reset_interview():
    """Reset session state to start a fresh interview without server restart."""
    st.session_state["interview_state"] = None
    st.rerun()


def render_setup_screen():
    """Screen 1: Candidate Setup Form."""
    st.markdown('<div class="ip-header"><span class="material-icons-round" style="font-size:36px;color:var(--accent);">target</span><h1>InterviewPilot</h1></div>', unsafe_allow_html=True)
    st.caption("Adaptive AI Mock Interview Coach — powered by LangGraph Agentic Workflows")
    st.markdown("---")

    with st.form("setup_form"):
        target_role = st.text_input(
            "Target Role *",
            placeholder="e.g. Frontend Engineer Intern, Data Analyst, Product Manager",
            help="Enter the specific role you are interviewing for.",
        )

        focus_area = st.selectbox(
            "Focus Area *",
            options=[fa.value for fa in FocusArea],
            index=1,
            help="Select the category of interview questions.",
        )

        from utils.resume_parser import extract_resume_text
        resume_file = st.file_uploader(
            "Upload Resume (Optional)", 
            type=["pdf", "txt"],
            help="Upload your resume. The AI will extract it to customize your interview questions."
        )

        background = st.text_area(
            "Background Snippet (Optional)",
            placeholder="e.g. CS junior proficient in Python, SQL, React. Built a fullstack web app during internship.",
            help="Provide 2-3 lines about your experience. If you uploaded a resume, this field is ignored.",
        )

        job_description = st.text_area(
            "Job Description (Optional)",
            placeholder="Paste the target job description here...",
            help="Provide the real job description to ground the interview competencies in actual requirements.",
        )

        enable_webcam = st.checkbox(
            "Enable Live Webcam Practice Mode",
            value=False,
            help="Show your live camera feed during the interview to practice posture and eye contact.",
        )

        enable_voice = st.checkbox(
            "Enable Voice-to-Voice Mode",
            value=False,
            help="Speak your answers via microphone and hear the AI Interviewer speak back to you.",
        )

        submitted = st.form_submit_button("Start Interview", use_container_width=True)

    if submitted:
        if not target_role.strip():
            st.error("Target Role is required. Please enter a role to proceed.")
            return

        final_background = background.strip()
        if resume_file:
            with st.spinner("Extracting text from resume..."):
                extracted_text = extract_resume_text(resume_file)
                if extracted_text:
                    final_background = extracted_text
                else:
                    st.warning("Failed to extract text from resume. Falling back to background snippet if provided.")

        candidate = CandidateProfile(
            target_role=target_role.strip(),
            focus_area=FocusArea(focus_area),
            background=final_background if final_background else None,
            job_description=job_description.strip() if job_description.strip() else None,
        )

        with st.spinner("Generating role-aware interview strategy and first question..."):
            state = run_start_interview(candidate)
            state.enable_webcam = enable_webcam
            state.enable_voice = enable_voice
            st.session_state["interview_state"] = state
            st.rerun()


def render_interview_screen(state: InterviewState):
    """Screen 2: Interactive Chat Interview — Camera LEFT (2/3), Chat RIGHT (1/3)."""
    # --- Top Header Bar ---
    st.markdown('<div class="ip-header"><span class="material-icons-round" style="font-size:30px;color:var(--accent);">record_voice_over</span><h1>Mock Interview Session</h1></div>', unsafe_allow_html=True)

    # --- Stat Pills ---
    diff_label = {1: "Beginner", 2: "Elementary", 3: "Intermediate", 4: "Advanced", 5: "Expert"}.get(
        state.current_difficulty, str(state.current_difficulty)
    )
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px;">'
        f'<div class="ip-stat"><span class="material-icons-round">work</span>{state.candidate.target_role} &middot; {state.candidate.focus_area.value.capitalize()}</div>'
        f'<div class="ip-stat"><span class="material-icons-round">speed</span>{diff_label} ({state.current_difficulty}/5)</div>'
        f'<div class="ip-stat"><span class="material-icons-round">format_list_numbered</span>Turn {min(state.current_turn + 1, state.max_turns)} / {state.max_turns}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.progress(min(state.current_turn / state.max_turns, 1.0))

    # --- Control Buttons ---
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("End Interview Early", use_container_width=True, type="secondary"):
            with st.spinner("Synthesizing feedback report on completed turns..."):
                state.status = InterviewStatus.ENDED_EARLY
                state.final_report = generate_coaching_report(state)
                save_session(state)
                st.session_state["interview_state"] = state
                st.rerun()
    with col_b:
        if st.button("Start New Interview", use_container_width=True, type="secondary"):
            reset_interview()

    st.markdown("---")

    # ========== MAIN SPLIT LAYOUT ==========
    # Camera LEFT (2/3) | Chat RIGHT (1/3)
    if state.enable_webcam:
        col_cam, col_chat = st.columns([2, 1])
    else:
        col_chat = st.container()
        col_cam = None

    # --- LEFT: Camera Feed ---
    if col_cam:
        with col_cam:
            st.markdown('<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><span class="material-icons-round" style="font-size:22px;color:var(--accent);">videocam</span><span style="font-weight:600;font-size:1rem;color:var(--text-1);">Live Camera Feed</span></div>', unsafe_allow_html=True)
            st.camera_input("Practice Feed", label_visibility="collapsed")

    # --- RIGHT: Chat Panel ---
    with col_chat:
        # Past Q&A transcript (scrollable history)
        if state.transcript:
            with st.expander("View conversation history", expanded=False):
                for turn in state.transcript:
                    st.markdown(
                        f'<div class="ip-history-q">{icon("psychology")} <strong>Q{turn.turn_number}:</strong> {turn.question.question}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="ip-history-a">{icon("person")} {turn.answer}</div>',
                        unsafe_allow_html=True,
                    )

        # Current active question
        if state.current_question:
            st.markdown(
                f'<div class="ip-question-bubble">{icon_lg("psychology")} {state.current_question.question}</div>',
                unsafe_allow_html=True,
            )

            # TTS Playback
            if state.enable_voice:
                from services.audio_service import generate_speech, transcribe_audio
                from audio_recorder_streamlit import audio_recorder

                audio_bytes = generate_speech(state.current_question.question)
                if audio_bytes:
                    st.audio(audio_bytes, format='audio/mp3', autoplay=True)

            # Candidate answer input
            user_answer = ""

            if state.enable_voice:
                st.markdown('<div class="ip-voice-banner"><span class="material-icons-round">mic</span>Voice Mode Active — Click to record, click again to stop.</div>', unsafe_allow_html=True)
                recorder_key = f"audio_recorder_{state.current_turn}"
                recorded_audio = audio_recorder(text=" Record / Stop", key=recorder_key, pause_threshold=60.0)

                if recorded_audio:
                    with st.spinner("Transcribing audio..."):
                        transcribed = transcribe_audio(recorded_audio)
                        if transcribed:
                            st.success(f"Transcribed: *{transcribed}*")
                            user_answer = transcribed
                        else:
                            st.error("Failed to transcribe audio. Please try typing instead.")

                st.caption("Or type your answer below:")

            text_input = st.chat_input("Type your answer here...")
            if text_input and text_input.strip():
                user_answer = text_input.strip()

            if user_answer:
                with st.spinner("Evaluating response & updating interview strategy..."):
                    updated_state = run_answer_turn(state, user_answer)
                    updated_state.enable_webcam = state.enable_webcam
                    updated_state.enable_voice = state.enable_voice
                    st.session_state["interview_state"] = updated_state
                    st.rerun()


def render_analytics_dashboard(state: InterviewState):
    """Render interactive metrics and performance charts on the final report screen."""
    st.markdown('<div style="display:flex;align-items:center;gap:8px;margin:16px 0 8px 0;"><span class="material-icons-round" style="font-size:24px;color:var(--accent);">insights</span><span style="font-weight:700;font-size:1.15rem;color:var(--text-1);">Session Analytics &amp; Performance Trajectory</span></div>', unsafe_allow_html=True)

    evaluations = [turn.evaluation for turn in state.transcript if turn.evaluation]
    if not evaluations:
        st.info("No evaluation data available to chart.")
        return

    avg_score = sum(e.overall_score for e in evaluations) / len(evaluations)
    max_difficulty = max((turn.question.difficulty for turn in state.transcript if turn.question), default=state.current_difficulty)
    turns_completed = len(state.transcript)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Average Score", value=f"{avg_score:.2f} / 5.0")
    with col2:
        st.metric(label="Peak Difficulty", value=f"Level {max_difficulty}")
    with col3:
        st.metric(label="Turns Completed", value=f"{turns_completed} / {state.max_turns}")

    st.markdown('<div style="display:flex;align-items:center;gap:6px;margin:12px 0 4px 0;"><span class="material-icons-round mi">trending_up</span><strong>Performance &amp; Difficulty Trajectory</strong></div>', unsafe_allow_html=True)
    chart_data = {
        "Turn": [f"Turn {t.turn_number}" for t in state.transcript if t.evaluation],
        "Score (1-5)": [t.evaluation.overall_score for t in state.transcript if t.evaluation],
        "Difficulty": [t.question.difficulty for t in state.transcript if t.evaluation],
    }
    st.line_chart(chart_data, x="Turn", y=["Score (1-5)", "Difficulty"])

    dim_scores: dict[str, list[float]] = {}
    for e in evaluations:
        for dim, score in e.dimension_scores.items():
            dim_scores.setdefault(dim.replace("_", " ").title(), []).append(score)

    if dim_scores:
        st.markdown('<div style="display:flex;align-items:center;gap:6px;margin:12px 0 4px 0;"><span class="material-icons-round mi">radar</span><strong>Multi-Dimensional Skill Breakdown</strong></div>', unsafe_allow_html=True)
        avg_dim_scores = {dim: round(sum(scores) / len(scores), 2) for dim, scores in dim_scores.items()}
        st.bar_chart(avg_dim_scores)


def render_final_report_screen(state: InterviewState):
    """Screen 3: Final Coaching Report."""
    if state.status == InterviewStatus.ENDED_EARLY:
        st.warning("Interview Ended Early by Candidate")
    else:
        st.success("Interview Complete!")

    col_d1, col_d2, col_d3, col_r = st.columns([1, 1, 1, 1])
    with col_d1:
        if state.final_report:
            st.download_button(
                label="Report (.md)",
                data=state.final_report,
                file_name=f"InterviewPilot_Report_{state.session_id}.md",
                mime="text/markdown",
                use_container_width=True,
            )
    with col_d2:
        if state.final_report:
            pdf_bytes = generate_report_pdf(state)
            st.download_button(
                label="Report (.pdf)",
                data=pdf_bytes,
                file_name=f"InterviewPilot_Report_{state.session_id}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
    with col_d3:
        st.download_button(
            label="Session (.json)",
            data=state.model_dump_json(indent=2),
            file_name=f"InterviewPilot_Session_{state.session_id}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_r:
        if st.button("Start New Interview", use_container_width=True):
            reset_interview()

    st.markdown("---")

    render_analytics_dashboard(state)

    st.markdown("---")

    if state.final_report:
        st.markdown(state.final_report)
    else:
        st.info("No coaching report generated.")

    st.markdown("---")

    with st.expander("View Full Conversation Transcript"):
        for turn in state.transcript:
            st.markdown(f"**Turn {turn.turn_number} ({turn.question.topic}):**")
            st.markdown(f"**Interviewer:** {turn.question.question}")
            st.markdown(f"**Candidate:** {turn.answer}")
            st.markdown("---")

    with st.expander("View Per-Question Evaluation Summaries"):
        for turn in state.transcript:
            if turn.evaluation:
                st.markdown(f"**Turn {turn.turn_number} — {turn.question.topic}:**")
                st.markdown(f"- **Overall Score:** {turn.evaluation.overall_score:.1f}/5.0 ({turn.evaluation.overall_level})")
                st.markdown(f"- **Answer Status:** `{turn.evaluation.answer_status.value}`")
                st.markdown(f"- **Recommended Action:** `{turn.evaluation.recommended_action.value}`")
                if turn.evaluation.strengths:
                    st.markdown(f"- **Strengths:** {', '.join(turn.evaluation.strengths)}")
                if turn.evaluation.weaknesses:
                    st.markdown(f"- **Weaknesses:** {', '.join(turn.evaluation.weaknesses)}")
                st.markdown("---")


def main():
    """Application main router."""
    st.set_page_config(
        page_title="InterviewPilot",
        page_icon="🎯",
        layout="wide",
    )
    init_session_state()

    # Inject global CSS once — self-collapsing rule keeps it zero-height
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    state: InterviewState | None = st.session_state.get("interview_state")

    if state is None or state.status == InterviewStatus.NOT_STARTED:
        render_setup_screen()
    elif state.status in (InterviewStatus.COMPLETED, InterviewStatus.ENDED_EARLY):
        render_final_report_screen(state)
    else:
        render_interview_screen(state)



if __name__ == "__main__":
    main()
