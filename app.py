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
    st.title("🎯 InterviewPilot")
    st.subheader("Adaptive AI Mock Interview Coach")
    st.markdown("Prepare for target roles with real-time, adaptive AI interviewing and structured coaching feedback.")
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
            index=1,  # Default to Technical
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
            "📷 Enable Live Webcam Practice Mode",
            value=False,
            help="Show your live camera feed during the interview to practice posture and eye contact.",
        )

        submitted = st.form_submit_button("🚀 Start Interview", use_container_width=True)

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
            st.session_state["interview_state"] = state
            st.rerun()


def render_interview_screen(state: InterviewState):
    """Screen 2: Interactive Chat Interview."""
    st.title("🎙️ Mock Interview Session")

    # Header stats
    c1, c2, c3 = st.columns([3, 2, 2])
    with c1:
        st.caption(f"**Role:** {state.candidate.target_role} ({state.candidate.focus_area.value.capitalize()})")
    with c2:
        diff_label = {
            1: "Beginner",
            2: "Elementary",
            3: "Intermediate",
            4: "Advanced",
            5: "Expert",
        }.get(state.current_difficulty, str(state.current_difficulty))
        st.caption(f"**Difficulty:** {diff_label} ({state.current_difficulty}/5)")
    with c3:
        st.caption(f"**Progress:** Turn {min(state.current_turn + 1, state.max_turns)} of {state.max_turns}")

    st.progress(min(state.current_turn / state.max_turns, 1.0))

    # Controls bar
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("⏹️ End Interview Early", use_container_width=True):
            with st.spinner("Synthesizing feedback report on completed turns..."):
                state.status = InterviewStatus.ENDED_EARLY
                state.final_report = generate_coaching_report(state)
                save_session(state)
                st.session_state["interview_state"] = state
                st.rerun()
    with col_b:
        if st.button("🔄 Start New Interview", use_container_width=True):
            reset_interview()

    st.markdown("---")

    # Layout: Split into Chat Column and Camera Column if webcam enabled
    if state.enable_webcam:
        col_chat, col_cam = st.columns([3, 2])
    else:
        col_chat = st.container()
        col_cam = None

    with col_chat:
        # Past Q&A chat history
        for turn in state.transcript:
            with st.chat_message("assistant"):
                st.write(turn.question.question)
            with st.chat_message("user"):
                st.write(turn.answer)

        # Current active question
        if state.current_question:
            with st.chat_message("assistant"):
                st.write(state.current_question.question)

            # Candidate answer chat input
            user_answer = st.chat_input("Type your answer here...")
            if user_answer and user_answer.strip():
                with st.spinner("Evaluating response & updating interview strategy..."):
                    updated_state = run_answer_turn(state, user_answer.strip())
                    updated_state.enable_webcam = state.enable_webcam
                    st.session_state["interview_state"] = updated_state
                    st.rerun()

    if col_cam:
        with col_cam:
            st.markdown("##### 📷 Live Camera Feed")
            st.caption("Practice eye contact and facial expressions while answering.")
            
            # Hide the "Take Photo" button via CSS injection
            st.markdown(
                """
                <style>
                [data-testid="stCameraInput"] button {
                    display: none !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            
            st.camera_input("Practice Feed", label_visibility="collapsed")


def render_analytics_dashboard(state: InterviewState):
    """Render interactive metrics and performance charts on the final report screen."""
    st.subheader("📊 Session Analytics & Performance Trajectory")

    evaluations = [turn.evaluation for turn in state.transcript if turn.evaluation]
    if not evaluations:
        st.info("No evaluation data available to chart.")
        return

    # 1. High-level KPI summary cards
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

    # 2. Turn-by-Turn Trajectory Chart
    st.markdown("##### 📈 Performance & Difficulty Trajectory")
    chart_data = {
        "Turn": [f"Turn {t.turn_number}" for t in state.transcript if t.evaluation],
        "Score (1-5)": [t.evaluation.overall_score for t in state.transcript if t.evaluation],
        "Difficulty": [t.question.difficulty for t in state.transcript if t.evaluation],
    }
    st.line_chart(chart_data, x="Turn", y=["Score (1-5)", "Difficulty"])

    # 3. Multi-Dimensional Skill Breakdown
    dim_scores: dict[str, list[float]] = {}
    for e in evaluations:
        for dim, score in e.dimension_scores.items():
            dim_scores.setdefault(dim.replace("_", " ").title(), []).append(score)

    if dim_scores:
        st.markdown("##### 🎯 Multi-Dimensional Skill Breakdown")
        avg_dim_scores = {dim: round(sum(scores) / len(scores), 2) for dim, scores in dim_scores.items()}
        st.bar_chart(avg_dim_scores)


def render_final_report_screen(state: InterviewState):
    """Screen 3: Final Coaching Report."""
    if state.status == InterviewStatus.ENDED_EARLY:
        st.warning("⚠️ Interview Ended Early by Candidate")
    else:
        st.success("🎉 Interview Complete!")

    # Export & Reset Controls
    col_d1, col_d2, col_r = st.columns([1, 1, 1])
    with col_d1:
        if state.final_report:
            st.download_button(
                label="📥 Report (.md)",
                data=state.final_report,
                file_name=f"InterviewPilot_Report_{state.session_id}.md",
                mime="text/markdown",
                use_container_width=True,
            )
    with col_d2:
        st.download_button(
            label="💾 Session (.json)",
            data=state.model_dump_json(indent=2),
            file_name=f"InterviewPilot_Session_{state.session_id}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_r:
        if st.button("🔄 Start New Interview", use_container_width=True):
            reset_interview()

    st.markdown("---")

    # Analytics Dashboard
    render_analytics_dashboard(state)

    st.markdown("---")

    # Main Coaching Report Markdown
    if state.final_report:
        st.markdown(state.final_report)
    else:
        st.info("No coaching report generated.")

    st.markdown("---")

    # Expandable sections for Transcript and Evaluations
    with st.expander("💬 View Full Conversation Transcript"):
        for turn in state.transcript:
            st.markdown(f"**Turn {turn.turn_number} ({turn.question.topic}):**")
            st.markdown(f"**Interviewer:** {turn.question.question}")
            st.markdown(f"**Candidate:** {turn.answer}")
            st.markdown("---")

    with st.expander("📊 View Per-Question Evaluation Summaries"):
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
    init_session_state()

    state: InterviewState | None = st.session_state.get("interview_state")

    if state is None or state.status == InterviewStatus.NOT_STARTED:
        render_setup_screen()
    elif state.status in (InterviewStatus.COMPLETED, InterviewStatus.ENDED_EARLY):
        render_final_report_screen(state)
    else:
        render_interview_screen(state)



if __name__ == "__main__":
    main()
