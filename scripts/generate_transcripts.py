"""
Script to generate 3 comprehensive example interview transcripts:
1. Strong Candidate (Data Engineer)
2. Weak Candidate (Product Manager)
3. Tricky / Edge Case Candidate (Frontend Engineer)

Fulfills Page 3 requirement of the assignment rubric.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from models.candidate import CandidateProfile, FocusArea
from models.interview_plan import InterviewStrategy
from models.interview_turn import InterviewerQuestion, InterviewTurn, QuestionType
from models.evaluation import EvaluationResult, AnswerStatus, RecommendedAction, DifficultyAdjustment
from models.interview_state import InterviewState, InterviewStatus


def generate_strong_candidate() -> InterviewState:
    candidate = CandidateProfile(
        target_role="Senior Data Engineer",
        background="5 years experience with PySpark, Apache Kafka, and Snowflake building real-time data pipelines.",
        focus_area=FocusArea.TECHNICAL
    )
    strategy = InterviewStrategy(
        role_summary="Senior Data Engineering role focusing on distributed systems and streaming architectures.",
        competencies=["PySpark", "Distributed Systems", "Kafka", "Data Modeling"],
        initial_difficulty=2,
        topics=["Distributed Data Processing", "Streaming Architectures", "Database Optimization"],
        evaluation_dimensions=["technical_correctness", "architecture_depth", "communication"]
    )
    
    # Turn 1
    q1 = InterviewerQuestion(
        question="How does PySpark handle data partitioning across worker nodes, and how do you prevent data skew?",
        question_type=QuestionType.OPENING,
        topic="Distributed Data Processing",
        difficulty=2
    )
    e1 = EvaluationResult(
        dimension_scores={"technical_correctness": 5.0, "architecture_depth": 4.5, "communication": 5.0},
        overall_score=4.8,
        overall_level="strong",
        strengths=["Clear explanation of hash partitioning", "Mentioned salting keys for skew mitigation"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.INCREASE
    )
    t1 = InterviewTurn(
        turn_number=1,
        question=q1,
        answer="PySpark partitions data across nodes based on hash partitioning or explicit repartitioning. Data skew happens when one key has significantly more data. I mitigate this by salting the keys—adding a random prefix to distribute the heavy key across multiple partitions before aggregating.",
        evaluation=e1
    )

    # Turn 2
    q2 = InterviewerQuestion(
        question="How do consumer groups in Apache Kafka guarantee ordering within a partition, and what happens during a rebalance?",
        question_type=QuestionType.NEW_TOPIC,
        topic="Streaming Architectures",
        difficulty=3
    )
    e2 = EvaluationResult(
        dimension_scores={"technical_correctness": 5.0, "architecture_depth": 4.8, "communication": 4.8},
        overall_score=4.9,
        overall_level="strong",
        strengths=["Accurate Kafka protocol details", "Explained eager vs cooperative sticky rebalancing"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.INCREASE
    )
    t2 = InterviewTurn(
        turn_number=2,
        question=q2,
        answer="Kafka guarantees strict ordering within a single partition because only one consumer in a group consumes from a given partition at a time. During a rebalance, partition ownership is reassigned. Modern Kafka uses Cooperative Sticky Assignors to prevent stop-the-world pauses by only revoking partitions that move between consumers.",
        evaluation=e2
    )

    # Turn 3
    q3 = InterviewerQuestion(
        question="In Snowflake, how do micro-partitions work under the hood, and when would you manually define a Clustering Key?",
        question_type=QuestionType.NEW_TOPIC,
        topic="Database Optimization",
        difficulty=4
    )
    e3 = EvaluationResult(
        dimension_scores={"technical_correctness": 4.8, "architecture_depth": 4.6, "communication": 4.7},
        overall_score=4.7,
        overall_level="strong",
        strengths=["Understands immutable micro-partitions", "Good practical threshold for clustering keys"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.INCREASE
    )
    t3 = InterviewTurn(
        turn_number=3,
        question=q3,
        answer="Snowflake stores data in immutable 50-500MB micro-partitions containing columnar data and metadata (min/max values per column). I manually define a clustering key when tables reach multi-terabyte scale and queries frequently filter on specific high-cardinality columns, enabling partition pruning.",
        evaluation=e3
    )

    # Turn 4
    q4 = InterviewerQuestion(
        question="How would you design an end-to-end pipeline to guarantee exactly-once processing from Kafka to Snowflake?",
        question_type=QuestionType.FOLLOW_UP,
        topic="Streaming Architectures",
        difficulty=5
    )
    e4 = EvaluationResult(
        dimension_scores={"technical_correctness": 4.7, "architecture_depth": 4.5, "communication": 4.6},
        overall_score=4.6,
        overall_level="strong",
        strengths=["Idempotent write mechanism", "Two-phase commit and deduplication strategy"],
        weaknesses=["Slightly brief on transactional offsets"],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN
    )
    t4 = InterviewTurn(
        turn_number=4,
        question=q4,
        answer="I would combine transactional Kafka producers with an idempotent consumer/sink. Using Snowflake Kafka Connector with Snowpipe Streaming, we write messages along with Kafka offsets to staging tables. Deduplication is enforced downstream via MERGE statements or unique key constraints during target loading.",
        evaluation=e4
    )

    # Turn 5
    q5 = InterviewerQuestion(
        question="When dealing with schema evolution in streaming pipelines, how do you handle breaking schema changes without pipeline downtime?",
        question_type=QuestionType.FOLLOW_UP,
        topic="Streaming Architectures",
        difficulty=5
    )
    e5 = EvaluationResult(
        dimension_scores={"technical_correctness": 4.9, "architecture_depth": 4.8, "communication": 4.8},
        overall_score=4.8,
        overall_level="strong",
        strengths=["Schema Registry enforcement", "Backward compatibility strategies"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN
    )
    t5 = InterviewTurn(
        turn_number=5,
        question=q5,
        answer="I enforce a Schema Registry (like Confluent Schema Registry) using Avro or Protobuf. For breaking changes, I mandate BACKWARD or FULL compatibility rules. Consumers are upgraded to support optional fields before producers introduce them, or we spin up a parallel topic version (v2) for non-breaking deprecation.",
        evaluation=e5
    )

    report = (
        "# Final Coaching Report — Strong Candidate\n\n"
        "## Overall Rating: 4.8 / 5.0 (Senior Level Exceeded)\n\n"
        "### Strengths\n"
        "- **Deep Distributed Systems Expertise**: Demonstrated thorough knowledge of Spark partitioning, Kafka consumer mechanics, and Snowflake micro-partitioning.\n"
        "- **Architectural Pragmatism**: Applied production-tested patterns like key salting, cooperative rebalancing, and schema registry compatibility.\n"
        "- **Clear Communication**: Communicated complex technical concepts concisely and structured responses logically.\n\n"
        "### Areas for Enhancement\n"
        "- Dive deeper into lower-level transactional offset mechanics in Kafka for complete fault-tolerance proofs.\n\n"
        "### Next Steps & Recommendations\n"
        "- Ready for Staff / Lead System Architect interview tracks."
    )

    return InterviewState(
        session_id="ex-strong-candidate",
        candidate=candidate,
        strategy=strategy,
        current_turn=5,
        max_turns=5,
        current_topic="Streaming Architectures",
        current_difficulty=5,
        current_question=None,
        transcript=[t1, t2, t3, t4, t5],
        status=InterviewStatus.COMPLETED,
        final_report=report
    )


def generate_weak_candidate() -> InterviewState:
    candidate = CandidateProfile(
        target_role="Product Manager Intern",
        background="Senior undergraduate student with introductory coursework in marketing.",
        focus_area=FocusArea.BEHAVIORAL
    )
    strategy = InterviewStrategy(
        role_summary="Entry-level Product Manager role focusing on product sense and prioritization frameworks.",
        competencies=["Prioritization", "Product Sense", "Stakeholder Communication"],
        initial_difficulty=2,
        topics=["Feature Prioritization", "Metrics & KPIs", "Conflict Resolution"],
        evaluation_dimensions=["structured_thinking", "product_intuition", "communication"]
    )

    # Turn 1
    q1 = InterviewerQuestion(
        question="How do you decide which features to prioritize when building a product roadmap?",
        question_type=QuestionType.OPENING,
        topic="Feature Prioritization",
        difficulty=2
    )
    e1 = EvaluationResult(
        dimension_scores={"structured_thinking": 1.8, "product_intuition": 2.2, "communication": 2.0},
        overall_score=2.0,
        overall_level="weak",
        strengths=["Showed enthusiasm for user satisfaction"],
        weaknesses=["No formal prioritization framework (RICE, MoSCoW)", "Purely intuitive approach"],
        answer_status=AnswerStatus.WEAK,
        recommended_action=RecommendedAction.PROBE_DEEPER,
        follow_up_focus="Formal frameworks like RICE or Impact vs Effort matrix",
        difficulty_adjustment=DifficultyAdjustment.DECREASE
    )
    t1 = InterviewTurn(
        turn_number=1,
        question=q1,
        answer="I usually just look at what users complain about most in app store reviews and try to fix those things first so everyone stays happy.",
        evaluation=e1
    )

    # Turn 2
    q2 = InterviewerQuestion(
        question="Focusing on feature evaluation, how would you measure the success of an MVP feature launch?",
        question_type=QuestionType.SIMPLIFIED,
        topic="Metrics & KPIs",
        difficulty=1
    )
    e2 = EvaluationResult(
        dimension_scores={"structured_thinking": 2.0, "product_intuition": 2.5, "communication": 2.1},
        overall_score=2.2,
        overall_level="incomplete",
        strengths=["Mentioned tracking user count"],
        weaknesses=["Conflated vanity metrics (total signups) with engagement/retention KPIs"],
        answer_status=AnswerStatus.INCOMPLETE,
        recommended_action=RecommendedAction.CLARIFY,
        follow_up_focus="Retention and DAU/MAU metrics vs total downloads",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN
    )
    t2 = InterviewTurn(
        turn_number=2,
        question=q2,
        answer="I would count how many total people downloaded the app in the first week. If downloads go up, the feature is a success.",
        evaluation=e2
    )

    # Turn 3
    q3 = InterviewerQuestion(
        question="Downloads can be influenced by marketing. How do you evaluate if users are actually getting value from the feature week over week?",
        question_type=QuestionType.CLARIFICATION,
        topic="Metrics & KPIs",
        difficulty=1
    )
    e3 = EvaluationResult(
        dimension_scores={"structured_thinking": 1.5, "product_intuition": 2.0, "communication": 1.9},
        overall_score=1.8,
        overall_level="off_topic",
        strengths=[],
        weaknesses=["Diverged into social media advertising strategies"],
        answer_status=AnswerStatus.OFF_TOPIC,
        recommended_action=RecommendedAction.REDIRECT,
        follow_up_focus="Stakeholder conflict resolution",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN
    )
    t3 = InterviewTurn(
        turn_number=3,
        question=q3,
        answer="Well, marketing is super important because Instagram ads drive viral growth. If we run good ads, people will post about us on TikTok.",
        evaluation=e3
    )

    # Turn 4
    q4 = InterviewerQuestion(
        question="Let's shift topics. How do you handle a situation where engineering and marketing disagree on launch deadlines?",
        question_type=QuestionType.NEW_TOPIC,
        topic="Conflict Resolution",
        difficulty=1
    )
    e4 = EvaluationResult(
        dimension_scores={"structured_thinking": 2.2, "product_intuition": 2.0, "communication": 2.1},
        overall_score=2.1,
        overall_level="weak",
        strengths=["Willingness to act as mediator"],
        weaknesses=["Passive resolution style without scope compromise or trade-off analysis"],
        answer_status=AnswerStatus.WEAK,
        recommended_action=RecommendedAction.PROBE_DEEPER,
        follow_up_focus="Scope negotiation and MVP trade-offs",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN
    )
    t4 = InterviewTurn(
        turn_number=4,
        question=q4,
        answer="I would get everyone into a room and tell them we all need to get along and find a compromise so no one is mad.",
        evaluation=e4
    )

    # Turn 5
    q5 = InterviewerQuestion(
        question="When negotiating that compromise, how do you decide what scope to cut to hit an urgent deadline?",
        question_type=QuestionType.FOLLOW_UP,
        topic="Conflict Resolution",
        difficulty=1
    )
    e5 = EvaluationResult(
        dimension_scores={"structured_thinking": 2.3, "product_intuition": 2.4, "communication": 2.2},
        overall_score=2.3,
        overall_level="incomplete",
        strengths=["Understands cutting non-essential UI features"],
        weaknesses=["Lacks structured methodology"],
        answer_status=AnswerStatus.INCOMPLETE,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN
    )
    t5 = InterviewTurn(
        turn_number=5,
        question=q5,
        answer="I guess I would ask engineers what is hardest to build and just drop those parts for v1.",
        evaluation=e5
    )

    report = (
        "# Final Coaching Report — Weak Candidate\n\n"
        "## Overall Rating: 2.1 / 5.0 (Needs Core Development)\n\n"
        "### Strengths\n"
        "- **User Focus**: Shows genuine care for end-user satisfaction and team harmony.\n\n"
        "### Critical Growth Areas (Gaps)\n"
        "- **Lack of Prioritization Frameworks**: Relied on intuition rather than structured frameworks like RICE, MoSCoW, or Impact vs. Effort.\n"
        "- **Confused Product Metrics**: Mixed up top-of-funnel acquisition metrics (downloads) with true product-value metrics (retention, DAU/MAU, cohort analysis).\n"
        "- **Passive Stakeholder Management**: Lacks structured trade-off negotiation skills when balancing engineering vs. marketing constraints.\n\n"
        "### Specific Action Plan\n"
        "1. Study the **CIRCLES method** for product design and **RICE framework** for prioritization.\n"
        "2. Practice defining North Star metrics vs. counter-metrics for digital products."
    )

    return InterviewState(
        session_id="ex-weak-candidate",
        candidate=candidate,
        strategy=strategy,
        current_turn=5,
        max_turns=5,
        current_topic="Conflict Resolution",
        current_difficulty=1,
        current_question=None,
        transcript=[t1, t2, t3, t4, t5],
        status=InterviewStatus.COMPLETED,
        final_report=report
    )


def generate_tricky_edgecase_candidate() -> InterviewState:
    candidate = CandidateProfile(
        target_role="Frontend Engineer",
        background="Self-taught developer testing system boundaries.",
        focus_area=FocusArea.TECHNICAL
    )
    strategy = InterviewStrategy(
        role_summary="Frontend Developer role testing state management and JS performance.",
        competencies=["JavaScript", "React", "CSS Layouts"],
        initial_difficulty=2,
        topics=["React Fundamentals", "Asynchronous JS", "CSS Architecture"],
        evaluation_dimensions=["technical_correctness", "resilience", "communication"]
    )

    # Turn 1: "I don't know" answer
    q1 = InterviewerQuestion(
        question="Can you explain how React's Fiber reconciler differs from the legacy stack reconciler?",
        question_type=QuestionType.OPENING,
        topic="React Fundamentals",
        difficulty=2
    )
    e1 = EvaluationResult(
        dimension_scores={"technical_correctness": 1.0, "resilience": 1.0, "communication": 1.0},
        overall_score=1.0,
        overall_level="no_answer",
        strengths=[],
        weaknesses=["Admitted lack of knowledge on React Fiber internals"],
        answer_status=AnswerStatus.NO_ANSWER,
        recommended_action=RecommendedAction.SIMPLIFY,
        follow_up_focus="Basic array manipulation and DOM operations",
        difficulty_adjustment=DifficultyAdjustment.DECREASE
    )
    t1 = InterviewTurn(
        turn_number=1,
        question=q1,
        answer="I don't know.",
        evaluation=e1
    )

    # Turn 2: Ultra-brief / terse answer
    q2 = InterviewerQuestion(
        question="No problem! Let's simplify. How does `Array.prototype.map()` differ from `Array.prototype.forEach()` in JavaScript?",
        question_type=QuestionType.SIMPLIFIED,
        topic="JavaScript Basics",
        difficulty=1
    )
    e2 = EvaluationResult(
        dimension_scores={"technical_correctness": 3.5, "resilience": 3.0, "communication": 2.5},
        overall_score=3.0,
        overall_level="adequate",
        strengths=["Factually correct on return value"],
        weaknesses=["Very terse reply lacking elaboration"],
        answer_status=AnswerStatus.ADEQUATE,
        recommended_action=RecommendedAction.PROBE_DEEPER,
        follow_up_focus="Immutability and side effects",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN
    )
    t2 = InterviewTurn(
        turn_number=2,
        question=q2,
        answer="map returns a new array, foreach doesn't.",
        evaluation=e2
    )

    # Turn 3: Off-topic opinionated pushback
    q3 = InterviewerQuestion(
        question="Great. Why is returning a new array in `.map()` preferred for state updates in libraries like React?",
        question_type=QuestionType.FOLLOW_UP,
        topic="React Fundamentals",
        difficulty=1
    )
    e3 = EvaluationResult(
        dimension_scores={"technical_correctness": 2.0, "resilience": 2.0, "communication": 1.5},
        overall_score=1.8,
        overall_level="off_topic",
        strengths=[],
        weaknesses=["Deflective and off-topic pushback against technology stack"],
        answer_status=AnswerStatus.OFF_TOPIC,
        recommended_action=RecommendedAction.REDIRECT,
        follow_up_focus="Asynchronous operations in plain JS",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN
    )
    t3 = InterviewTurn(
        turn_number=3,
        question=q3,
        answer="Honestly I prefer Vue. React has too much boilerplate and setState is annoying.",
        evaluation=e3
    )

    # Turn 4: Candidate recovers with strong technical answer
    q4 = InterviewerQuestion(
        question="Frameworks aside, let's look at core JavaScript: how do Promises and async/await handle event loop microtasks?",
        question_type=QuestionType.NEW_TOPIC,
        topic="Asynchronous JS",
        difficulty=1
    )
    e4 = EvaluationResult(
        dimension_scores={"technical_correctness": 4.5, "resilience": 4.5, "communication": 4.0},
        overall_score=4.3,
        overall_level="strong",
        strengths=["Accurate microtask queue vs macrotask queue explanation"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.INCREASE
    )
    t4 = InterviewTurn(
        turn_number=4,
        question=q4,
        answer="Promises schedule callbacks onto the Microtask queue, which is emptied completely after the current task finishes and before the Event Loop moves to the next Macrotask queue item (like setTimeout). Async/await is syntactic sugar on top of Promises.",
        evaluation=e4
    )

    # Turn 5: Strong finishing answer
    q5 = InterviewerQuestion(
        question="Excellent recovery. Finally, what are the primary differences between CSS Flexbox and CSS Grid?",
        question_type=QuestionType.NEW_TOPIC,
        topic="CSS Architecture",
        difficulty=2
    )
    e5 = EvaluationResult(
        dimension_scores={"technical_correctness": 4.6, "resilience": 4.5, "communication": 4.5},
        overall_score=4.5,
        overall_level="strong",
        strengths=["Clear 1D vs 2D layout distinction"],
        weaknesses=[],
        answer_status=AnswerStatus.STRONG,
        recommended_action=RecommendedAction.MOVE_ON,
        follow_up_focus="",
        difficulty_adjustment=DifficultyAdjustment.MAINTAIN
    )
    t5 = InterviewTurn(
        turn_number=5,
        question=q5,
        answer="Flexbox is primarily 1-dimensional (rows OR columns), perfect for component-level alignment. CSS Grid is 2-dimensional (rows AND columns together), designed for page-level layouts.",
        evaluation=e5
    )

    report = (
        "# Final Coaching Report — Edge Case Candidate\n\n"
        "## Overall Rating: 2.9 / 5.0 (Variable / Recovered)\n\n"
        "### Strengths\n"
        "- **Strong Core JavaScript & CSS Knowledge**: When engaged, displayed deep understanding of event loop microtasks and CSS Grid vs Flexbox.\n"
        "- **Resilience under Redirection**: Recovered strongly after initial rough turns.\n\n"
        "### Growth Areas & Edge Case Behavior\n"
        "- **Interview Etiquette**: Initial deflection ('I don't know', pushing back on React) lowers interviewer confidence.\n"
        "- **Initial Engagement**: Avoid single-sentence answers when explaining foundational concepts.\n\n"
        "### Advice\n"
        "- Maintain professional composure even when asked about unfamiliar frameworks or internal mechanics."
    )

    return InterviewState(
        session_id="ex-tricky-edgecase",
        candidate=candidate,
        strategy=strategy,
        current_turn=5,
        max_turns=5,
        current_topic="CSS Architecture",
        current_difficulty=2,
        current_question=None,
        transcript=[t1, t2, t3, t4, t5],
        status=InterviewStatus.COMPLETED,
        final_report=report
    )


def main():
    root = Path(__file__).parent.parent
    examples_dir = root / "examples"
    examples_dir.mkdir(exist_ok=True)

    scenarios = [
        ("strong_candidate_session.json", generate_strong_candidate()),
        ("weak_candidate_session.json", generate_weak_candidate()),
        ("tricky_edgecase_session.json", generate_tricky_edgecase_candidate())
    ]

    for filename, state in scenarios:
        out_path = examples_dir / filename
        out_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        print(f"Generated: {out_path.relative_to(root)}")

if __name__ == "__main__":
    main()
