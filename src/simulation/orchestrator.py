import time
from rich.console import Console
from src.ingest.handler import handler as ingest_handler
from src.planner.handler import handler_manual_trigger as planner_handler
from src.shared.storage import db
from src.shared.models import IncidentState

console = Console()

class Orchestrator:
    """
    Simulates AWS Step Functions locally.
    """
    def __init__(self):
        pass

    def process_event(self, alarm_event):
        # 1. Ingest
        console.print("[bold yellow]Step 1: Ingestion[/bold yellow]")
        ingest_res = ingest_handler(alarm_event)
        if ingest_res["statusCode"] != 200:
            console.print(f"[red]Ingestion failed:[/red] {ingest_res}")
            return
            
        res_body = eval(ingest_res["body"]) # safely parse json in real app
        incident_id = res_body["incident_id"]
        console.print(f"Incident Created: {incident_id}")

        # 2. Plan
        console.print("[bold yellow]Step 2: Planning[/bold yellow]")
        plan = planner_handler(incident_id)
        if not plan:
            console.print("[red]No plan generated. Exiting.[/red]")
            return

        # 3. Decision
        if plan.requires_approval:
            console.print("[bold cyan]Plan requires approval. Pausing execution.[/bold cyan]")
            console.print(f"Run [bold]rr approve {incident_id}[/bold] to continue.")
            # Update state to MITIGATING (waiting)
            incident = db.get_incident(incident_id)
            incident.state = IncidentState.MITIGATING
            db.save_incident(incident)
            return
        
        # 4. Execute (Auto-Approve)
        console.print("[bold yellow]Step 3: Auto-Execution[/bold yellow]")
        from src.executor.handler import execute_plan
        execute_plan(incident_id)

    def resume_approval(self, incident_id):
        console.print(f"[bold yellow]Resuming Incident {incident_id}[/bold yellow]")
        # 4. Execute (after approval)
        from src.executor.handler import execute_plan
        execute_plan(incident_id)

# Global
orchestrator = Orchestrator()
