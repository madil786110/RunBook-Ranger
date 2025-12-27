import time
from src.shared.storage import db
from src.shared.models import ActionLog, ActionStatus, IncidentState
from src.shared.actions import action_handler

def execute_plan(incident_id: str):
    plan = db.get_plan(incident_id)
    if not plan:
        print(f"No plan found for incident {incident_id}")
        return

    print(f"Executing Plan for Incident {incident_id}...")
    
    incident = db.get_incident(incident_id)
    incident.state = IncidentState.MITIGATING
    db.save_incident(incident)

    all_success = True
    
    for action in plan.actions:
        action_id = action["id"]
        action_type = action["type"]
        params = action["params"]
        
        # TODO: Check Idempotency (skip if already done)
        # TODO: Check Locks
        
        log = ActionLog(
            incident_id=incident_id,
            action_id=action_id,
            status=ActionStatus.IN_PROGRESS
        )
        db.log_action(log)
        
        try:
            print(f"Running Action: {action_id} ({action_type})")
            result = action_handler.execute(action_type, params)
            
            log.status = ActionStatus.SUCCESS
            log.details = result
            print(f"  [SUCCESS] {result}")
            
        except Exception as e:
            log.status = ActionStatus.FAILED
            log.details = {"error": str(e)}
            print(f"  [FAILED] {e}")
            all_success = False
            break # Stop on error for now
            
        db.log_action(log)
        
    # Update Incident State
    if all_success:
        incident.state = IncidentState.RESOLVED
        incident.resolved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"Incident {incident_id} RESOLVED.")
    else:
        incident.state = IncidentState.FAILED
        print(f"Incident {incident_id} FAILED.")
        
    db.save_incident(incident)
