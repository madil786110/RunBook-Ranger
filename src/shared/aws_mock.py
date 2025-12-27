from typing import Dict, Any, List

class MockBoto3:
    """Simulates Boto3 client behavior for local testing"""
    
    def __init__(self):
        self._asg_state = {"app-prod-asg": {"DesiredCapacity": 2, "MaxSize": 5}}
        self._ecs_state = {"my-cluster/my-service": {"desiredCount": 2}}
    
    def client(self, service_name: str, region_name: str = "us-east-1"):
        if service_name == "autoscaling":
            return MockAutoScaling(self._asg_state)
        elif service_name == "ecs":
            return MockECS(self._ecs_state)
        elif service_name == "ssm":
            return MockSSM()
        else:
            raise NotImplementedError(f"Mock for {service_name} not implemented")

class MockAutoScaling:
    def __init__(self, state):
        self.state = state

    def describe_auto_scaling_groups(self, AutoScalingGroupNames: List[str]):
        asgs = []
        for name in AutoScalingGroupNames:
            if name in self.state:
                asgs.append({
                    "AutoScalingGroupName": name,
                    "DesiredCapacity": self.state[name]["DesiredCapacity"],
                    "MaxSize": self.state[name]["MaxSize"]
                })
        return {"AutoScalingGroups": asgs}

    def set_desired_capacity(self, AutoScalingGroupName: str, DesiredCapacity: int):
        if AutoScalingGroupName in self.state:
            # Enforce max size constraint logic here if needed, or assume AWS error
            if DesiredCapacity > self.state[AutoScalingGroupName]["MaxSize"]:
                 # Depending on strictness, we might raise an error or just let it 'fail'
                 pass 
            self.state[AutoScalingGroupName]["DesiredCapacity"] = DesiredCapacity
        return {}

class MockECS:
    def __init__(self, state):
        self.state = state

    def update_service(self, cluster: str, service: str, desiredCount: int):
        key = f"{cluster}/{service}"
        if key in self.state:
            self.state[key]["desiredCount"] = desiredCount
        return {}

class MockSSM:
    def send_command(self, InstanceIds: List[str], DocumentName: str, Parameters: Dict):
        # Always return success with a fake CommandId
        return {"Command": {"CommandId": "mock-command-id-12345"}}

# Global singleton
mock_boto3 = MockBoto3()
