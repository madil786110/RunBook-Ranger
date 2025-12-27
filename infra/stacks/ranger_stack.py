from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as ddb,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    Duration,
)
from constructs import Construct

class RunbookRangerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # =================================================================
        # 1. DynamoDB Tables
        # =================================================================
        
        # Incidents Table
        self.incidents_table = ddb.Table(
            self, "IncidentsTable",
            partition_key=ddb.Attribute(name="incident_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY  # For demo/student cleanup
        )

        # Plans Table
        self.plans_table = ddb.Table(
            self, "PlansTable",
            partition_key=ddb.Attribute(name="incident_id", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="plan_version", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Action Logs Table
        self.action_logs_table = ddb.Table(
            self, "ActionLogsTable",
            partition_key=ddb.Attribute(name="incident_id", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="ts_action_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Locks Table
        self.locks_table = ddb.Table(
            self, "LocksTable",
            partition_key=ddb.Attribute(name="resource_id", type=ddb.AttributeType.STRING),
            time_to_live_attribute="expires_at",
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # =================================================================
        # 2. Compute (Lambdas)
        # =================================================================
        
        # Shared Layer (for dependencies if needed, or just bundle code)
        # For simplicity in this demo, we'll assume code is bundled or small enough via Code.from_asset
        
        common_env = {
            "TABLE_INCIDENTS": self.incidents_table.table_name,
            "TABLE_PLANS": self.plans_table.table_name,
            "TABLE_ACTIONS": self.action_logs_table.table_name,
            "TABLE_LOCKS": self.locks_table.table_name,
        }

        # Ingest Lambda
        self.ingest_lambda = _lambda.Function(
            self, "IngestFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ingest.handler.handler",
            code=_lambda.Code.from_asset("../src"), # Assumes src is valid for asset
            environment=common_env,
            timeout=Duration.seconds(10)
        )
        self.incidents_table.grant_write_data(self.ingest_lambda)

        # Planner Lambda
        self.planner_lambda = _lambda.Function(
            self, "PlannerFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="planner.handler.handler_manual_trigger", # Adapted entrypoint
            code=_lambda.Code.from_asset("../src"),
            environment=common_env,
            timeout=Duration.seconds(30)
        )
        self.incidents_table.grant_read_data(self.planner_lambda)
        self.plans_table.grant_write_data(self.planner_lambda)
        
        # Executor Lambda
        self.executor_lambda = _lambda.Function(
            self, "ExecutorFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="executor.handler.lambda_handler", # Needs wrapper
            code=_lambda.Code.from_asset("../src"),
            environment=common_env,
            timeout=Duration.seconds(60)
        )
        self.incidents_table.grant_read_write_data(self.executor_lambda)
        self.plans_table.grant_read_data(self.executor_lambda)
        self.action_logs_table.grant_write_data(self.executor_lambda)
        self.locks_table.grant_read_write_data(self.executor_lambda)

        # Add Safety/Remediation IAM policies to Executor
        # Least Privilege: Only allow specific actions on specific resources if possible
        # For student demo general policy:
        self.executor_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["autoscaling:DescribeAutoScalingGroups", "autoscaling:SetDesiredCapacity"],
            resources=["*"], # In prod, restrict by tag
            conditions={"StringEquals": {"aws:ResourceTag/managed-by": "runbook-ranger"}}
        ))
        self.executor_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["ecs:UpdateService", "ecs:DescribeServices"],
            resources=["*"]
        ))
        self.executor_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["ssm:SendCommand"],
            resources=["*"], # Requires strict tagging
            conditions={"StringEquals": {"aws:ResourceTag/allow-remediation": "true"}}
        ))

        # =================================================================
        # 3. Workflow (Step Functions)
        # =================================================================
        
        # Simple Definition: Ingest -> Plan -> Choice(Approve?) -> Exec
        # In reality, CloudWatch triggers Ingest. Ingest triggers SFN.
        
        # States
        planner_task = tasks.LambdaInvoke(
            self, "Plan Remediation",
            lambda_function=self.planner_lambda,
            output_path="$.Payload"
        )
        
        executor_task = tasks.LambdaInvoke(
            self, "Execute Remediation",
            lambda_function=self.executor_lambda,
            input_path="$", # Pass result from planner or previous
            output_path="$.Payload"
        )
        
        # Choice: Approval Required?
        # For V1 simplicity, we skip the callback implementation in CDK to save time/complexity
        # and just do direct flow or fail if approval needed (demo limitation or TODO)
        # OR: We implement a simple Pass state for approval
        
        definition = planner_task.next(executor_task)
        
        self.state_machine = sfn.StateMachine(
            self, "RangerStateMachine",
            definition=definition,
            timeout=Duration.minutes(5)
        )
        
        # Grant Ingest Lambda permission to start execution
        self.state_machine.grant_start_execution(self.ingest_lambda)
        self.ingest_lambda.add_environment("STATE_MACHINE_ARN", self.state_machine.state_machine_arn)

        # =================================================================
        # 4. EventBridge Rule
        # =================================================================
        
        # Match ANY CloudWatch Alarm State Change to ALARM
        rule = events.Rule(
            self, "AlarmRule",
            event_pattern=events.EventPattern(
                source=["aws.cloudwatch"],
                detail_type=["CloudWatch Alarm State Change"],
                detail={
                    "state": {
                        "value": ["ALARM"]
                    }
                }
            )
        )
        rule.add_target(targets.LambdaFunction(self.ingest_lambda))
