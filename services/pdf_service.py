"""
PDF Report Generator for InterviewPilot.

Converts the coaching report markdown and session analytics
into a professionally formatted, downloadable PDF document.
"""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone

from fpdf import FPDF


# ── Colour palette (matches the warm UI theme) ────────────────────────
_ACCENT  = (232, 133, 106)   # #E8856A
_TEXT_1  = (45, 42, 38)      # #2D2A26
_TEXT_2  = (107, 101, 96)    # #6B6560
_BG      = (250, 247, 244)   # #FAF7F4
_WHITE   = (255, 255, 255)
_GREEN   = (120, 193, 149)   # #78C195
_BORDER  = (237, 217, 204)   # #EDD9CC


class _ReportPDF(FPDF):
    """Custom FPDF subclass with InterviewPilot header/footer."""

    def __init__(self, candidate_role: str, session_id: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self._role = candidate_role
        self._sid = session_id
        self.set_auto_page_break(auto=True, margin=25)

    # ── Header ────────────────────────────────────────────────────────
    def header(self):
        self.set_fill_color(*_ACCENT)
        self.rect(0, 0, 210, 18, "F")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*_WHITE)
        self.set_xy(10, 4)
        self.cell(0, 10, "InterviewPilot  |  AI Mock Interview Report", ln=True)
        self.ln(6)

    # ── Footer ────────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_TEXT_2)
        self.cell(0, 10, f"Session {self._sid}  |  Page {self.page_no()}/{{nb}}", align="C")


def _strip_md(text: str) -> str:
    """Very lightweight Markdown → plain-text for PDF cells."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)        # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)             # italic
    text = re.sub(r"`(.+?)`", r"\1", text)               # inline code
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)   # heading markers
    text = re.sub(r"^[-*]\s+", "  • ", text, flags=re.M) # list bullets
    text = re.sub(r"^---+$", "", text, flags=re.M)       # horizontal rules
    return text.strip()


def generate_report_pdf(state) -> bytes:
    """
    Build a complete PDF report from an InterviewState object.

    Returns the PDF as raw bytes suitable for st.download_button.
    """
    pdf = _ReportPDF(
        candidate_role=state.candidate.target_role,
        session_id=state.session_id,
    )
    pdf.alias_nb_pages()
    pdf.add_page()

    # ── Title Block ───────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*_ACCENT)
    pdf.cell(0, 12, "Interview Coaching Report", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_TEXT_2)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.cell(0, 6, f"Role: {state.candidate.target_role}  |  "
                    f"Focus: {state.candidate.focus_area.value.capitalize()}  |  "
                    f"Generated: {now}", ln=True)
    pdf.ln(4)

    # Accent line
    pdf.set_draw_color(*_ACCENT)
    pdf.set_line_width(0.6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # ── Session Summary Metrics ───────────────────────────────────────
    evaluations = [t.evaluation for t in state.transcript if t.evaluation]
    turns_completed = len(state.transcript)
    avg_score = sum(e.overall_score for e in evaluations) / len(evaluations) if evaluations else 0
    max_diff = max(
        (t.question.difficulty for t in state.transcript if t.question),
        default=state.current_difficulty,
    )

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_TEXT_1)
    pdf.cell(0, 8, "Session Summary", ln=True)
    pdf.ln(2)

    # Metric boxes
    box_w = 60
    box_h = 18
    start_x = 10
    pdf.set_font("Helvetica", "", 9)

    for i, (label, value) in enumerate([
        ("Average Score", f"{avg_score:.2f} / 5.0"),
        ("Peak Difficulty", f"Level {max_diff}"),
        ("Turns Completed", f"{turns_completed} / {state.max_turns}"),
    ]):
        x = start_x + i * (box_w + 5)
        pdf.set_fill_color(*_BG)
        pdf.set_draw_color(*_BORDER)
        pdf.rect(x, pdf.get_y(), box_w, box_h, "DF")
        pdf.set_xy(x + 3, pdf.get_y() + 2)
        pdf.set_text_color(*_TEXT_2)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(box_w - 6, 5, label)
        pdf.set_xy(x + 3, pdf.get_y() + 5)
        pdf.set_text_color(*_TEXT_1)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(box_w - 6, 7, value)
        pdf.set_xy(start_x, pdf.get_y() - 7)  # reset Y for same row

    pdf.ln(box_h + 8)

    # ── Main Coaching Report ──────────────────────────────────────────
    if state.final_report:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*_TEXT_1)
        pdf.cell(0, 8, "Coaching Report", ln=True)
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_TEXT_1)

        for line in state.final_report.split("\n"):
            stripped = line.strip()
            if not stripped:
                pdf.ln(3)
                continue

            # Detect heading lines
            heading_match = re.match(r"^(#{1,3})\s+(.*)", stripped)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2)
                pdf.ln(3)
                pdf.set_font("Helvetica", "B", max(14 - level * 2, 10))
                pdf.set_text_color(*_ACCENT if level == 1 else _TEXT_1)
                pdf.multi_cell(0, 7, _strip_md(heading_text))
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*_TEXT_1)
                continue

            # Detect horizontal rule
            if re.match(r"^-{3,}$", stripped):
                pdf.ln(2)
                pdf.set_draw_color(*_BORDER)
                pdf.set_line_width(0.3)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(4)
                continue

            # Regular text
            pdf.multi_cell(0, 5.5, _strip_md(stripped))

    pdf.ln(6)

    # ── Per-Turn Transcript & Evaluations ─────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*_TEXT_1)
    pdf.cell(0, 8, "Full Conversation Transcript & Evaluations", ln=True)
    pdf.ln(2)

    for turn in state.transcript:
        # Turn header
        pdf.set_draw_color(*_ACCENT)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        topic = turn.question.topic if turn.question else "General"
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_ACCENT)
        pdf.cell(0, 6, f"Turn {turn.turn_number}  —  {topic}  "
                        f"(Difficulty {turn.question.difficulty})", ln=True)
        pdf.ln(1)

        # Question
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_TEXT_2)
        pdf.cell(0, 5, "Interviewer:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_TEXT_1)
        pdf.multi_cell(0, 5, turn.question.question)
        pdf.ln(2)

        # Answer
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_TEXT_2)
        pdf.cell(0, 5, "Candidate:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_TEXT_1)
        pdf.multi_cell(0, 5, turn.answer)
        pdf.ln(2)

        # Evaluation summary
        if turn.evaluation:
            e = turn.evaluation
            pdf.set_fill_color(*_BG)
            y_start = pdf.get_y()
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*_TEXT_2)
            pdf.cell(0, 5, f"Score: {e.overall_score:.1f}/5.0 ({e.overall_level})  |  "
                           f"Status: {e.answer_status.value}  |  "
                           f"Action: {e.recommended_action.value}", ln=True)

            if e.strengths:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*_GREEN)
                pdf.multi_cell(0, 4.5, "Strengths: " + ", ".join(e.strengths))

            if e.weaknesses:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(*_ACCENT)
                pdf.multi_cell(0, 4.5, "Weaknesses: " + ", ".join(e.weaknesses))

            # Background fill for eval block
            y_end = pdf.get_y()
            pdf.rect(10, y_start - 1, 190, y_end - y_start + 2, "D")

        pdf.ln(5)

    # ── Output ────────────────────────────────────────────────────────
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
