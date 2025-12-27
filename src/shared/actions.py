from src.shared.aws_mock import mock_boto3

class ActionHandler:
    def scale_asg(self, params):
        asg_name = params.get("asg_name")
        adjustment = int(params.get("adjustment", 1))
        
        client = mock_boto3.client("autoscaling")
        # 1. Get current capacity
        res = client.describe_auto_scaling_groups([asg_name])
        asgs = res.get("AutoScalingGroups", [])
        if not asgs:
            raise ValueError(f"ASG {asg_name} not found")
            
        current = asgs[0]["DesiredCapacity"]
        new_capacity = current + adjustment
        
        # 2. Set new capacity
        print(f"  -> scale_asg: {asg_name} {current} -> {new_capacity}")
        client.set_desired_capacity(asg_name, new_capacity)
        return {"old": current, "new": new_capacity}

    def ssm_restart_service(self, params):
        instance_id = params.get("instance_id")
        service = params.get("service_name")
        print(f"  -> ssm_restart_service: Rebooting {service} on {instance_id}")
        
        client = mock_boto3.client("ssm")
        res = client.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={"commands": [f"systemctl restart {service}"]}
        )
        return {"command_id": res["Command"]["CommandId"]}

    
    def scale_ecs_service(self, params):
        cluster = params.get("cluster")
        service = params.get("service")
        adjustment = int(params.get("adjustment", 1))
        
        # Mock logic
        print(f"  -> scale_ecs_service: Scaling {service} in {cluster} by {adjustment}")
        return {"status": "scaled", "new_count": 5} # Mock return

    def rollback_deployment(self, params):
        # Supports ECS or Lambda based on params
        target_type = params.get("target_type") # ecs | lambda
        target_id = params.get("target_id")
        
        print(f"  -> rollback_deployment: Rolling back {target_type} {target_id}")
        return {"status": "rolled_back", "previous_version": "v1"}

    def execute(self, action_type: str, params: dict):
        if hasattr(self, action_type):
            return getattr(self, action_type)(params)
        raise NotImplementedError(f"Action {action_type} not implemented")

# Singleton
action_handler = ActionHandler()
