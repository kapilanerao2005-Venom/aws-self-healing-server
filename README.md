🚑 Self-Healing Server on AWS


An automated incident-response pipeline: when the web server's CPU saturates, the system snapshots the disk, reboots the instance, and emails the on-call engineer — with zero human intervention.


📌 Problem
In real cloud environments, failures are noticed late and fixed manually. A 2 AM CPU spiral shouldn't wait for a human to wake up.

💡 Solution
CloudWatch watches CPU → after 2 consecutive minutes above 70% the alarm fires → EventBridge routes the event → a Lambda bot snapshots the EBS volume (data safety first), reboots the instance, prunes old snapshots, and notifies via SNS.


🏗️ Architecture

self-healing-server\architecture

         EC2 Web Server
                |
                v
      Amazon CloudWatch
       CPU > 70% for
      2 consecutive minutes
                |
                v
        CloudWatch Alarm
                |
                v
          EventBridge
                |
                v
        AWS Lambda Function
                |
        +-------+-------+
        |       |       |
        v       v       v
     Snapshot  Reboot  Cleanup
       EBS      EC2   Old Snapshots
                |
                v
             Amazon SNS
                |
                v
       On-Call Email Alert


🧰 Services

Service                     	Role
EC2             	Target web server (Amazon Linux 2023, t2.micro)
CloudWatch      	CPU metric + alarm (period 60 × 2 evaluations)
EventBridge     	Routes alarm state-change events to Lambda
Lambda          	Remediation logic (Python / boto3)
EBS	                Snapshots before every recovery
SNS             	Email alerts
IAM             	Two least-privilege roles (SSM for EC2, remediation for Lambda)
CloudFormation     	One-command full deployment


📸 self-healing-server\README.md — crashed the server on purpose
timeout 300 yes > /dev/null & → alarm red in ~2 min → snapshot + reboot + email, site back in under a minute. Screenshots in screenshots/.


🚀 Deploy
aws cloudformation deploy \  --template-file cloudformation/template.yaml \  --stack-name self-heal \  --capabilities CAPABILITY_IAM \  --parameter-overrides OperatorEmail=you@example.com
Also built step-by-step with the AWS CLI (lambda/, policies/) to learn each service individually.


💰 Cost
~₹0/month — single t2.micro within Free Tier; Lambda, SNS, alarms within free allowances.


😅 Real Challenges (and fixes)
Lambda crashed mid-recovery — CloudWatch Logs: ParamValidationError: Unknown parameter in Filters[0]: "Value", must be one of: Name, Values. boto3 filters take Values (a list); I'd written Value. Comparing with the correctly-shaped describe_volumes call above it pinpointed the bug in seconds.
Invalid base64 on CLI invoke — CLI v2 base64-encodes payloads by default → --cli-binary-format raw-in-base64-out.
Alarm fires but Lambda never runs — EventBridge needs explicit aws lambda add-permission for events.amazonaws.com.
No alert emails — SNS subscriptions stay PendingConfirmation until the email link is clicked.


📚 What I Learned
Event-driven architecture, IAM least privilege scoped to a single SNS topic ARN, debugging by tracing an event's path, and why treat-missing-data: breaching catches dead instances.