import re
from typing import Dict, Any, List
from src.shared.models import Incident, RemediationPlan
from src.shared.storage import db
from src.planner.loader import find_matching_runbook
from src.shared.runbook_models import Runbook

def _resolve_vars(text: str, context: Dict[str, Any]) -> str:
    """
    Resolves variables like ${dimensions.InstanceId} from context.
    """
    if not isinstance(text, str):
        return text
        
    pattern = r"\$\{(.+?)\}"
    
    def replacer(match):
        path = match.group(1).split(".")
        value = context
        for key in path:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return match.group(0) # Failed to resolve
            if value is None:
                return match.group(0)
        return str(value)
        
    return re.sub(pattern, replacer, text)

def _resolve_params(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    resolved = {}
    for k, v in params.items():
        resolved[k] = _resolve_vars(v, context)
    return resolved

def handler_manual_trigger(incident_id: str):
    """
    Triggered by Step Functions (or local loop) after Ingest.
    1. Load incident
    2. Match runbook
    3. Generate Plan
    4. Save Plan
    """
    incident = db.get_incident(incident_id)
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")
        
    # Extract context from CloudWatch event
    cw_detail = incident.cloudwatch_event.get("detail", {})
    metrics = cw_detail.get("configuration", {}).get("metrics", [])
    
    # Flatten context for variable resolution
    context = incident.cloudwatch_event.get("detail", {}).copy()
    
    # Try to find dimensions from the first metric
    # In real world, we'd handle multiple metrics more robustly
    namespace = "Unknown"
    dimensions = {}
    
    if metrics:
        metric = metrics[0].get("metricStat", {}).get("metric", {})
        namespace = metric.get("namespace", "Unknown")
        dimensions = metric.get("dimensions", {})
        context["dimensions"] = dimensions
        context["namespace"] = namespace

    print(f"Planning for Incident {incident_id} (Alarm: {incident.alarm_name}, Namespace: {namespace})")
    
    runbook = find_matching_runbook(incident.alarm_name, namespace)
    if not runbook:
        print("No matching runbook found.")
        return None

    # Generate Plan
    actions = []
    requires_approval = False
    
    for action_def in runbook.actions:
        resolved_params = _resolve_params(action_def.params, context)
        action_plan = {
            "id": action_def.id,
            "type": action_def.type,
            "params": resolved_params,
            "sanity_checks": action_def.safety
        }
        actions.append(action_plan)
        if action_def.safety.get("approval_required", False):
            requires_approval = True
            
    plan = RemediationPlan(
        incident_id=incident_id,
        requires_approval=requires_approval,
        actions=actions
    )
    
    db.save_plan(plan)
    print(f"Generated Plan: {len(actions)} actions. Approval Required: {requires_approval}")
    return plan
