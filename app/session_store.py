"""
In-memory session store.

The spec's single POST /api/interview endpoint is stateless per
request -- every turn is a fresh HTTP call. This module is what
makes the conversation feel continuous: it holds, per sessionId,
exactly where the candidate is in their interview plan.

No database, no persistence across server restarts -- that's
correct per the spec (no persistent accounts / long-term history
required). A plain dict is enough for a 48-hour hackathon judge run.
"""

from dataclasses import dataclass, field


@dataclass
class InterviewSession:
    session_id: str
    candidate_name: str
    plan: list[dict]              # from planner.build_interview_plan()
    topic_index: int = 0          # which plan[] entry we're currently on
    current_question: str = ""    # the question we most recently asked
    followups_used: int = 0       # follow-ups asked for the CURRENT topic
    max_followups_per_topic: int = 2
    required_per_topic: int = 2   # min questions/topic to hit the 8-question quota
    questions_asked_this_topic: int = 0
    total_questions_asked: int = 0
    transcript: list[dict] = field(default_factory=list)  # [{"topic","question","answer"}]
    done: bool = False

    @property
    def current_topic(self) -> dict:
        return self.plan[self.topic_index]

    def has_more_topics(self) -> bool:
        return self.topic_index < len(self.plan)

    def advance_to_next_topic(self) -> None:
        self.topic_index += 1
        self.followups_used = 0

    def record_turn(self, question: str, answer: str) -> None:
        self.transcript.append({
            "topic": self.current_topic["title"] if self.has_more_topics() else "N/A",
            "question": question,
            "answer": answer,
        })


# sessionId -> InterviewSession
_SESSIONS: dict[str, InterviewSession] = {}


def create_session(session_id: str, candidate_name: str, plan: list[dict]) -> InterviewSession:
    session = InterviewSession(
        session_id=session_id,
        candidate_name=candidate_name,
        plan=plan,
    )
    _SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> InterviewSession | None:
    return _SESSIONS.get(session_id)