from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator
import yaml
import os

class ActionDef(BaseModel):
    id: str
    type: str
    params: Dict[str, Any]
    safety: Dict[str, Any] = Field(default_factory=dict)

class MatchCriteria(BaseModel):
    alarm_name_prefix: Optional[str] = None
    namespace: Optional[str] = None
    dimensions: Optional[Dict[str, str]] = None

class Runbook(BaseModel):
    runbook_id: str
    match: MatchCriteria
    actions: List[ActionDef]

    @classmethod
    def load_from_file(cls, filepath: str) -> 'Runbook':
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
