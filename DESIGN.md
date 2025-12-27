# System Design: Runbook Ranger

## Core Philosophy
1.  **Safety > Speed**: Better to do nothing than to make an outage worse.
2.  **Explicit > Implicit**: Runbooks must explicitly define actions and constraints.
3.  **Measurable**: Every action emits metrics to track MTTR and success rates.

## 1. State Machine Design
The core orchestration is handled by AWS Step Functions (Cloud) or a local state machine simulator (Local).

**States:**
- **Plan**: Loads the runbook matching the alarm and generates a remediation plan.
- **ApprovalWait**: (Optional) Pauses execution until a human or external system approves the plan.
- **Apply**: Executes the planned actions sequentially.
- **Verify**: (Future) Checks if the alarm has returned to OK state.

## 2. Safety Model

### Idempotency
Every action execution is tracked in the `ActionLogs` DynamoDB table with a composite key: `incident_id` + `action_id`.
- If an action is retried, the executor checks this table first.
- If previously successful: Return cached success.
- If running: Wait/Fail.
- If failed: Retry (up to limit).

### Resource Locking
To prevent race conditions (e.g., two alarms triggering simultaneous restarts on the same server), we use a `Locks` DDB table.
- **Key**: `resource_id` (e.g., `i-1234567890abcdef0`)
- **TTL**: Locks auto-expire after 10 minutes (failsafe).
- **Behavior**: If lock acquisition fails, the remediation defers or fails safely.

### Global Kill Switch
An environment variable `RR_KILL_SWITCH=true` on the Executor Lambda immediately halts all write actions. This is a "break glass" mechanism for operators.

## 3. Data Model

### Incidents Table
| Attribute | Type | Description |
| :--- | :--- | :--- |
| `incident_id` | String (PK) | UUID v4 |
| `alarm_name` | String | Source CloudWatch Alarm |
| `state` | Enum | OPEN, MITIGATING, RESOLVED, FAILED |
| `severity` | String | CRITICAL, HIGH, MEDIUM |
| `created_at` | Timestamp | ISO 8601 |
| `resolved_at` | Timestamp | ISO 8601 |

## 4. Security & IAM
- **Least Privilege**: Lambdas have scoped permissions (e.g., `ec2:StopInstances` only on tagged resources).
- **Tag-Based Access Control**:
    - `Condition: StringEquals: aws:ResourceTag/allow-remediation: true`
    - Resources MUST be tagged to be touched by the bot.

## 5. Future Work
- **Chaos Testing**: Integrate Fault Injection Simulator (FIS) to prove recovery.
- **Slack Integration**: ChatOps for approvals.
- **Multi-Region**: Global resiliency patterns.
