import os
import boto3

ec2 = boto3.client("ec2")
sns = boto3.client("sns")

INSTANCE_ID = os.environ["INSTANCE_ID"]
TOPIC_ARN = os.environ["TOPIC_ARN"]
KEEP_SNAPSHOTS = int(os.environ.get("KEEP_SNAPSHOTS", "5"))


def lambda_handler(event, context):
    # 1. Read alarm details from the EventBridge event
    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName", "unknown-alarm")
    state = detail.get("state", {}).get("value", "UNKNOWN")
    previous_state = detail.get("previousState", {}).get("value", "UNKNOWN")
    print(f"Alarm {alarm_name} changed {previous_state} -> {state}")

    # 2. DATA SAFETY: snapshot every volume before touching the instance
    volumes = ec2.describe_volumes(
        Filters=[{"Name": "attachment.instance-id", "Values": [INSTANCE_ID]}]
    ).get("Volumes", [])

    snapshot_ids = []
    for vol in volumes:
        snap = ec2.create_snapshot(
            VolumeId=vol["VolumeId"],
            Description=f"Self-heal snapshot before reboot (trigger: {alarm_name})",
            TagSpecifications=[
                {"ResourceType": "snapshot",
                 "Tags": [{"Key": "AutoSnapshot", "Value": "true"}]}
            ],
        )
        snapshot_ids.append(snap["SnapshotId"])
        print(f"Created snapshot {snap['SnapshotId']} of volume {vol['VolumeId']}")

    # 3. RECOVERY: reboot the instance
    ec2.reboot_instances(InstanceIds=[INSTANCE_ID])
    print(f"Rebooted instance {INSTANCE_ID}")

    # 4. COST HYGIENE: keep only the newest N auto-snapshots
    snaps = ec2.describe_snapshots(
        Filters=[{"Name": "tag:AutoSnapshot", "Values": ["true"]}],
        OwnerIds=["self"],
    ).get("Snapshots", [])
    snaps.sort(key=lambda s: s["StartTime"], reverse=True)
    for old in snaps[KEEP_SNAPSHOTS:]:
        ec2.delete_snapshot(SnapshotId=old["SnapshotId"])
        print(f"Deleted old snapshot {old['SnapshotId']} (cost hygiene)")

    # 5. NOTIFY the on-call human
    message = (
        "AUTOMATED RECOVERY EXECUTED\n"
        f"Alarm: {alarm_name}\n"
        f"State: {previous_state} -> {state}\n"
        f"Instance: {INSTANCE_ID}\n"
        f"Snapshots taken: {', '.join(snapshot_ids) or 'none'}\n"
        "Action: instance rebooted\n"
    )
    sns.publish(TopicArn=TOPIC_ARN,
                Subject="[Self-Healing Bot] Recovery executed",
                Message=message)
    print("Notification sent")

    return {"statusCode": 200, "body": message}
