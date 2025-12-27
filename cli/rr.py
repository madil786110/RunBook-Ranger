import click
import json
import os
import sys
from rich.console import Console
from rich.table import Table

# Add project root to path
sys.path.append(os.getcwd())

from src.shared.storage import db
from src.shared.models import Incident

console = Console()

@click.group()
def cli():
    """Runbook Ranger CLI - Local Simulator"""
    pass

@cli.command()
@click.argument('alarm_file', type=click.Path(exists=True))
def simulate(alarm_file):
    """Simulate an incident from a JSON alarm file"""
    console.print(f"[bold blue]Simulating incident from {alarm_file}...[/bold blue]")
    try:
        with open(alarm_file, 'r') as f:
            alarm_event = json.load(f)
        
        from src.simulation.orchestrator import orchestrator
        orchestrator.process_event(alarm_event)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback
        traceback.print_exc()

@cli.command()
def list_incidents():
    """List all local incidents"""
    incidents = db.list_incidents()
    table = Table(title="Local Incidents")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Alarm", style="magenta")
    table.add_column("State", style="green")
    table.add_column("Created")

    for i in incidents:
        table.add_row(i.incident_id, i.alarm_name, i.state.value, i.created_at)

    console.print(table)

@cli.command()
@click.argument('incident_id')
def show(incident_id):
    """Show details for a specific incident"""
    incident = db.get_incident(incident_id)
    if not incident:
        console.print(f"[red]Incident {incident_id} not found[/red]")
        return
        
    console.print(f"[bold]Incident:[/bold] {incident.incident_id}")
    console.print(f"[bold]State:[/bold] {incident.state.value}")
    console.print(f"[bold]Alarm:[/bold] {incident.alarm_name}")
    console.print(f"[bold]Summary:[/bold] {incident.summary}")
    
    plan = db.get_plan(incident_id)
    if plan:
        console.print("\n[bold]Remediation Plan:[/bold]")
        console.print(f"Approval Required: {plan.requires_approval}")
        for action in plan.actions:
            console.print(f"- {action['id']} ({action['type']})")

@cli.command()
@click.argument('incident_id')
def approve(incident_id):
    """Approve a pending plan for an incident"""
    incident = db.get_incident(incident_id)
    if not incident:
        console.print(f"[red]Incident {incident_id} not found[/red]")
        return

    plan = db.get_plan(incident_id)
    if not plan:
        console.print(f"[red]No plan found/needed for incident {incident_id}[/red]")
        return

    if not plan.requires_approval:
        console.print("[yellow]This plan does not require approval.[/yellow]")
        # We allow forcing it anyway for demo purposes
    
    console.print(f"[green]Approving Incident {incident_id}...[/green]")
    from src.simulation.orchestrator import orchestrator
    orchestrator.resume_approval(incident_id)

if __name__ == '__main__':
    cli()
