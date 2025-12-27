from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

class IncidentState(str, Enum):
    OPEN = "OPEN"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Incident(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alarm_name: str
    state: IncidentState = IncidentState.OPEN
    severity: Severity = Severity.MEDIUM
    summary: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: Optional[str] = None
    cloudwatch_event: Dict[str, Any] = Field(default_factory=dict)

class RemediationPlan(BaseModel):
    incident_id: str
    plan_version: str = "v1"
    requires_approval: bool = False
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ActionStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class ActionLog(BaseModel):
    incident_id: str
    action_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: ActionStatus
    details: Dict[str, Any] = Field(default_factory=dict)
