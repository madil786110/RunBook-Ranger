import json
import os
from src.shared.models import Incident, IncidentState, Severity
from src.shared.storage import db

# In local mode, we might not use the actual Lambda context
def handler(event, context=None):
    """
    Ingest Lambda Handler.
    Receives CloudWatch Alarm State Change event.
    Creates an Incident in DynamoDB (or local storage).
    """
    print(f"Received event: {json.dumps(event)}")
    
    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName")
    new_state = detail.get("state", {}).get("value")
    
    if not alarm_name or not new_state:
        print("Invalid event format")
        return {"statusCode": 400, "body": "Invalid event"}

    if new_state != "ALARM":
        print(f"Alarm {alarm_name} transitioned to {new_state}. Ignoring non-ALARM state.")
        return {"statusCode": 200, "body": "Ignored"}

    # Create Incident
    summary = detail.get("state", {}).get("reason", "No reason provided")
    
    incident = Incident(
        alarm_name=alarm_name,
        state=IncidentState.OPEN,
        severity=Severity.HIGH, # Heuristic for now
        summary=summary,
        cloudwatch_event=event
    )
    
    # Save to DB (Local or DynamoDB)
    db.save_incident(incident)
    print(f"Created incident: {incident.incident_id}")

    # Trigger Step Functions (if in AWS)
    sfn_arn = os.environ.get("STATE_MACHINE_ARN")
    if sfn_arn:
        import boto3
        client = boto3.client("stepfunctions")
        print(f"Starting execution of {sfn_arn} for {incident.incident_id}")
        client.start_execution(
            stateMachineArn=sfn_arn,
            name=incident.incident_id,
            input=json.dumps({"incident_id": incident.incident_id})
        )
    
    return {
        "statusCode": 200, 
        "body": json.dumps({"incident_id": incident.incident_id})
    }
