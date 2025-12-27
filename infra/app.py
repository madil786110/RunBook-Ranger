#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.ranger_stack import RunbookRangerStack

app = cdk.App()
RunbookRangerStack(app, "RunbookRangerStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)

app.synth()
