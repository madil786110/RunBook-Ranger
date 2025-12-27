import os
import glob
from typing import List, Optional
from src.shared.runbook_models import Runbook

RUNBOOKS_DIR = os.path.join(os.getcwd(), "runbooks")

def load_all_runbooks() -> List[Runbook]:
    runbooks = []
    # Recursively find .yaml or .yml files
    files = glob.glob(os.path.join(RUNBOOKS_DIR, "**/*.yaml"), recursive=True)
    files += glob.glob(os.path.join(RUNBOOKS_DIR, "**/*.yml"), recursive=True)
    
    for f in files:
        try:
            rb = Runbook.load_from_file(f)
            runbooks.append(rb)
        except Exception as e:
            print(f"Failed to load runbook {f}: {e}")
            
    return runbooks

def find_matching_runbook(alarm_name: str, namespace: str) -> Optional[Runbook]:
    """
    Finds the first runbook that matches the alarm criteria.
    Simple prefix matching for now.
    """
    runbooks = load_all_runbooks()
    for rb in runbooks:
        # Check Namespace
        if rb.match.namespace and rb.match.namespace != namespace:
            continue
            
        # Check Alarm Name Prefix
        if rb.match.alarm_name_prefix and not alarm_name.startswith(rb.match.alarm_name_prefix):
            continue
            
        return rb
    return None
