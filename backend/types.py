from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum


class ThreadStatus(str, Enum):
    ACTIVE = "active"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"


class SSEEventType(str, Enum):
    MESSAGE = "message"
    INTERRUPT = "interrupt"
    ERROR = "error"


class StreamResponseType(str, Enum):
    EMPATHY = "[EMPATHY]"
    PLANS = "[PLANS]"
    REQUIRE_USER_CONFIRM = "[REQUIRE_USER_CONFIRM]"


class StreamChatRequest(BaseModel):
    message: str
    thread_id: str


class StreamChatResponse(BaseModel):
    thread_id: str
    status: ThreadStatus
    message_count: int


class ThreadState(BaseModel):
    thread_id: str
    status: ThreadStatus
    messages: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CheckpointData(BaseModel):
    thread_id: str
    checkpoint_id: str
    state: Dict[str, Any]
    timestamp: str


class WanderPlan(BaseModel):
    id: str
    title: str
    category: str
    duration: str
    cost: str
    area: str
    quote: str
    highlightTag: str
    subChips: List[str]
    description: str
    image: str


class RiskAssessment(BaseModel):
    is_risky: bool
    risk_level: str
    message: str
    requires_confirmation: bool = False
