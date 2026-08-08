"""
Pydantic models for the Interview Agent API.
"""

from typing import List, Optional
from pydantic import BaseModel


class Mission(BaseModel):
    day: int
    title: str
    passed: Optional[bool] = None
    skipped: Optional[bool] = None
    attempts: Optional[int] = None


class Member(BaseModel):
    id: str
    name: str
    jobRole: str
    yearsExperience: int
    education: str
    status: str


class Signals(BaseModel):
    commitDays: int
    missionsCompleted: int
    missionsFirstTry: int


class Candidate(BaseModel):
    member: Member
    missions: List[Mission]
    signals: Signals


class InterviewRequest(BaseModel):
    sessionId: str
    candidate: Optional[Candidate] = None
    message: Optional[str] = None


class Feedback(BaseModel):
    summary: str
    strengths: List[str]
    gaps: List[str]
    next: List[str]


class InterviewResponse(BaseModel):
    reply: str
    done: bool
    feedback: Optional[Feedback] = None