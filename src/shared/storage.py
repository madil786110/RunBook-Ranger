import json
import os
from typing import List, Optional, Dict, Any
from .models import Incident, RemediationPlan, ActionLog

# Local file storage for simulation
DB_DIR = os.path.join(os.getcwd(), ".rr_db")

class LocalStorage:
    def __init__(self):
        os.makedirs(DB_DIR, exist_ok=True)
        self.incidents_file = os.path.join(DB_DIR, "incidents.json")
        self.plans_file = os.path.join(DB_DIR, "plans.json")
        self.actions_file = os.path.join(DB_DIR, "actions.json")
        self._init_files()

    def _init_files(self):
        for f in [self.incidents_file, self.plans_file, self.actions_file]:
            if not os.path.exists(f):
                with open(f, 'w') as fh:
                    json.dump({}, fh)

    def _read_json(self, filepath: str) -> Dict[str, Any]:
        with open(filepath, 'r') as f:
            return json.load(f)

    def _write_json(self, filepath: str, data: Dict[str, Any]):
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    # --- Incidents ---
    def save_incident(self, incident: Incident):
        data = self._read_json(self.incidents_file)
        data[incident.incident_id] = incident.model_dump()
        self._write_json(self.incidents_file, data)

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        data = self._read_json(self.incidents_file)
        if incident_id in data:
            return Incident(**data[incident_id])
        return None

    def list_incidents(self) -> List[Incident]:
        data = self._read_json(self.incidents_file)
        return [Incident(**v) for v in data.values()]

    # --- Plans ---
    def save_plan(self, plan: RemediationPlan):
        data = self._read_json(self.plans_file)
        data[plan.incident_id] = plan.model_dump()
        self._write_json(self.plans_file, data)
    
    def get_plan(self, incident_id: str) -> Optional[RemediationPlan]:
        data = self._read_json(self.plans_file)
        if incident_id in data:
            return RemediationPlan(**data[incident_id])
        return None

    # --- Actions ---
    def log_action(self, log: ActionLog):
        data = self._read_json(self.actions_file)
        if log.incident_id not in data:
            data[log.incident_id] = []
        data[log.incident_id].append(log.model_dump())
        self._write_json(self.actions_file, data)

class DynamoDBStorage:
    def __init__(self):
        import boto3
        self.ddb = boto3.resource("dynamodb")
        self.table_incidents = self.ddb.Table(os.environ.get("TABLE_INCIDENTS", "Incidents"))
        self.table_plans = self.ddb.Table(os.environ.get("TABLE_PLANS", "Plans"))
        self.table_actions = self.ddb.Table(os.environ.get("TABLE_ACTIONS", "ActionLogs"))

    def save_incident(self, incident: Incident):
        self.table_incidents.put_item(Item=incident.model_dump())

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        resp = self.table_incidents.get_item(Key={"incident_id": incident_id})
        if "Item" in resp:
            return Incident(**resp["Item"])
        return None
        
    def list_incidents(self) -> List[Incident]:
        # Scan is expensive; used here only for demo lists
        resp = self.table_incidents.scan()
        return [Incident(**i) for i in resp.get("Items", [])]

    def save_plan(self, plan: RemediationPlan):
         # Composite key handling simplified for demo
        item = plan.model_dump()
        self.table_plans.put_item(Item=item)

    def get_plan(self, incident_id: str) -> Optional[RemediationPlan]:
        # In real app, query by partition key and sort by version desc
        resp = self.table_plans.query(
            KeyConditionExpression="incident_id = :id",
            ExpressionAttributeValues={":id": incident_id}
        )
        items = resp.get("Items", [])
        if items:
            return RemediationPlan(**items[0])
        return None

    def log_action(self, log: ActionLog):
        item = log.model_dump()
        item["ts_action_id"] = f"{log.timestamp}#{log.action_id}" # Sort key
        self.table_actions.put_item(Item=item)

# Switch backend
if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    db = DynamoDBStorage()
else:
    db = LocalStorage()
