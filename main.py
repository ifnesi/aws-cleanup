#!/usr/bin/python3
# BY DEFAULT, WILL ONLY RUN AGAINST TEST INSTANCES
# MUST USE --full FLAG TO RUN AGAINST WHOLE ACCOUNT

# On fresh Ubuntu instance, install prereqs:
# sudo apt-get update; sudo apt-get install -y python3-pip;
# python3 -m pip install -r requirements.txt
import os
import sys
import json
import yaml
import logging
import argparse
import datetime

from utils import (
    determine_action,
    sort_key,
    add_to_log,
    date_or_none,
    sys_exc,
    iso_format,
    datetime_handler,
)
from utils.aws import AWSInstance
from utils.slack_client import SlackClient


###############################
# Global and System Variables #
###############################
D_TODAY = datetime.date.today()


###############
# Main thread #
###############
if __name__ == "__main__":

    # Parse Arguments
    parser = argparse.ArgumentParser(description="AWS Cleanup Script")
    parser.add_argument(
        "--config",
        help="Set YAML configuration file (default is `config/default_config.yaml`)",
        dest="config",
        type=str,
        default=os.path.join("config", "default_config.yaml"),
    )
    parser.add_argument(
        "--run-date",
        help="Set run date (ISO format i.e., yyyy-mm-dd)",
        type=iso_format,
        dest="run_date",
    )
    parser.add_argument(
        "--dry-run",
        help="Dry run, no tag changes of stop/terminate instances",
        action="store_true",
        dest="dry_run",
    )
    parser.add_argument(
        "--full",
        help="Go through all AWS regions (if not set it will use YAML config `override.test_region_override`)",
        action="store_true",
        dest="full",
    )
    parser.add_argument(
        "--override-stop-date",
        help="Override stop date (Not implemented yet)",
        action="store_true",
        dest="override_stop_date",
    )
    parser.add_argument(
        "--debug",
        help="Set logging as DEBUG (default is INFO)",
        action="store_true",
        dest="debug",
    )
    args = parser.parse_args()

    # Set log level
    logging.basicConfig(
        format=f"%(asctime)s.%(msecs)03d [%(levelname)s]: %(message)s",
        level=logging.DEBUG if args.debug else logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        # Load config file (YAML)
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)

        slack_config = config.get("slack", dict())
        override_config = config.get("override", dict())
        general_config = config.get("general", dict())
        tags_config = config.get("tags", dict())
        notify_messages_config = config.get("notify_messages", dict())
        test_region_override = override_config.get("test_region_override", list())

        # Desc sort tags notifications by value (day)
        tags_notifications_config = tags_config.get("notifications", dict())
        tags_notifications = sorted(
            tags_notifications_config.items(),
            key=lambda n: n[1],
            reverse=True,
        )  # [(tag_name_1: days_1), (tag_name_2: days_2), ..., (tag_name_n: days_n)]

        if args.run_date:
            d_run_date = args.run_date
        else:
            d_run_date = D_TODAY

        # Slack notification
        # Question: if we are unable to retrieve the Slack token (and maybe send a test message), should we kill the entire process?
        slack_client = SlackClient(slack_config)

        # We won't send most stuff to Slack, but use this to validate that connection is okay and indicate the script is starting
        start_text = (
            "Running cleaner on {}".format(d_run_date)
            if d_run_date == D_TODAY
            else "Running cleaner on simulated run date of {}".format(d_run_date)
        )
        logging.info(start_text)
        slack_client.send_text(start_text)

        if not args.full:
            # use test region filter
            regions = test_region_override
            logging.info("Using test regions")
        else:
            aws_client = AWSInstance(
                "us-east-1",
                args=args,
            )
            regions = aws_client.get_regions()

        logging.info("Using regions: {}".format(", ".join(regions)))

        detailed_log = list()
        for region in regions:
            logging.info("Processing region {}".format(region))
            aws_client = AWSInstance(
                region,
                notify_messages_config=notify_messages_config,
                args=args,
                search_filter=override_config.get("test_filter"),
            )
            ec2_instances = aws_client.get_instances()

            # https://confluentinc.atlassian.net/wiki/spaces/~457145999/pages/3318745562/Cloud+Spend+Reduction+Proposal+AWS+Solutions+Engineering+Account
            for instance in ec2_instances:
                state = instance["State"]["Name"]
                instance_id = instance["InstanceId"]

                logging.info(
                    "Processing {} instance {} in region {}".format(
                        state,
                        instance_id,
                        region,
                    )
                )

                if "Tags" not in instance:
                    tags = dict()
                else:
                    tags = {tag["Key"]: tag["Value"] for tag in instance["Tags"]}

                autoscaling_group = tags.get(tags_config.get("t_autoscaling_group"))
                exception = tags.get(tags_config.get("t_exception"))
                instance_name = tags.get(tags_config.get("t_name"))

                # 'dn_' means 'either a Datetime.date or None'
                dn_stop_date = date_or_none(
                    tags,
                    tags_config.get("t_stop_date"),
                )
                dn_terminate_date = date_or_none(
                    tags,
                    tags_config.get("t_terminate_date"),
                )
                dn_notification = (
                    list()
                )  # [(tag_name_value_1, days_1, tag_name_1), (tag_name_value_2, days_2, tag_name_2), ..., (tag_name_value_n, days_n, tag_name_n)]
                for tag_name, days in tags_notifications:
                    dn_notification.append(
                        [
                            date_or_none(
                                tags,
                                tag_name,
                            ),
                            days,
                            tag_name,
                        ]
                    )

                # Rough equivalent to coalesce
                owner_email = (
                    tags.get(tags_config.get("t_owner_email"))
                    or tags.get(tags_config.get("t_email"))
                    or tags.get(tags_config.get("t_divvy_owner"))
                    or tags.get(tags_config.get("t_divvy_last_modified_by"))
                )

                logging.info(
                    "{} is {}".format(
                        instance_name,
                        state,
                    )
                )

                if autoscaling_group is None:
                    if exception is None:
                        if state == "running":
                            if True:
                                # Returns dict with the following:
                                # odn_notification_1: New dn_notification_1
                                # odn_notification_2: New dn_notification_2
                                # ...
                                # odn_notification_n: New dn_notification_n
                                # odn_action_date
                                # result ENUM
                                # n: Notification number (if any)

                                r = determine_action(
                                    idn_action_date=dn_stop_date,
                                    idn_notification=dn_notification,
                                    i_default_days=general_config.get(
                                        "default_stop_days"
                                    ),
                                    i_max_days=general_config.get("max_stop_days"),
                                    notify_messages_config=notify_messages_config,
                                    d_run_date=d_run_date,
                                )

                                # Update all tags that have changed
                                tags_changed = [
                                    (
                                        tags_config.get("t_stop_date"),
                                        dn_stop_date,
                                        r["odn_action_date"],
                                    )
                                ]
                                for n, notif in enumerate(dn_notification):
                                    tags_changed.append(
                                        (
                                            notif[2],  # tag_name_n
                                            notif[0],  # tag_name_value_n
                                            r["odn_notification_{}".format(n + 1)],
                                        )
                                    )
                                for tag in tags_changed:
                                    if tag[1] != tag[2]:
                                        aws_client.update_tag(
                                            instance_id,
                                            instance_name,
                                            tag[0],  # tag_name_value_n
                                            tag[2],  # tag_name_n
                                            tag[1],  # days_n
                                        )

                                message = r["result"].format(
                                    instance_type="EC2",
                                    instance_name=instance_name,
                                    instance_id=instance_id,
                                    region=region,
                                    action="stop",
                                    tag=tags_config.get("t_stop_date"),
                                    old_date=dn_stop_date,
                                    new_date=r["odn_action_date"],
                                    state=state,
                                    n=r.get("n"),
                                )

                                detailed_log.append(
                                    add_to_log(
                                        email=owner_email,
                                        instance_type="EC2",
                                        instance_name=instance_name,
                                        instance_id=instance_id,
                                        region=region,
                                        action="stop",
                                        tag=tags_config.get("t_stop_date"),
                                        result=r["result"],
                                        old_date=dn_stop_date,
                                        new_date=r["odn_action_date"],
                                        message=message,
                                    )
                                )

                                if r["result"] == "complete_action":
                                    # On complete:
                                    # Up till now, have:
                                    # * Left notification tags alone (tags are from stop notifications)
                                    # * Added a STOP/COMPLETE ACTION log
                                    # Now need to do the following: # TODO FIX THIS LOGIC, something is missing here
                                    # * Stop the instance
                                    # * TODO: Add "Summary stop tag"
                                    # * Add a termination date
                                    # * Set notification tags back to None
                                    # * Add a TERMINATE/TRANSITION log
                                    # * Add a TERMINATE/Add tag log?
                                    aws_client.stop(
                                        instance_id,
                                        instance_name,
                                    )

                                    aws_client.update_tag(
                                        instance_id,
                                        instance_name,
                                        tags_config.get("t_terminate_date"),
                                        d_run_date
                                        + datetime.timedelta(
                                            days=general_config.get(
                                                "default_terminate_days"
                                            )
                                        ),
                                        None,
                                    )

                                    # Summary stop log
                                    aws_client.update_tag(
                                        instance_id,
                                        instance_name,
                                        tags_config.get("t_stop_logs"),
                                        "notified:{};stopped:{}".format(
                                            ",".join(
                                                notif[0] for notif in dn_notification
                                            ),
                                            d_run_date,
                                        ),
                                        None,
                                    )

                                    message = notify_messages_config[
                                        "transition_action"
                                    ].format(
                                        instance_type="EC2",
                                        instance_name=instance_name,
                                        instance_id=instance_id,
                                        region=region,
                                        action="terminate",
                                        tag=tags_config.get("t_terminate_date"),
                                        old_date=d_run_date,  # Date of transition, not new terminate date
                                        new_date=d_run_date
                                        + datetime.timedelta(
                                            days=general_config.get(
                                                "default_terminate_days"
                                            )
                                        ),  # New terminate date
                                        state="stopped",  # Have just stopped the instance
                                    )

                                    detailed_log.append(
                                        add_to_log(
                                            email=owner_email,
                                            instance_type="EC2",
                                            instance_name=instance_name,
                                            instance_id=instance_id,
                                            region=region,
                                            action="terminate",
                                            tag=tags_config.get("t_terminate_date"),
                                            result="transition_action",
                                            old_date=None,
                                            new_date=d_run_date
                                            + datetime.timedelta(
                                                days=general_config.get(
                                                    "default_terminate_days"
                                                )
                                            ),
                                            message=message,
                                        )
                                    )

                                    for tag in dn_notification:
                                        aws_client.update_tag(
                                            instance_id,
                                            instance_name,
                                            tag[2],
                                            None,
                                            tag[0],
                                        )
                            else:
                                pass  # Placeholder for 'override' behavior

                        elif state == "stopped":
                            if True:
                                # Returns dict with the following:
                                # odn_notification_1: New dn_notification_1
                                # odn_notification_2: New dn_notification_2
                                # ...
                                # odn_notification_n: New dn_notification_n
                                # odn_action_date
                                # result ENUM

                                r = determine_action(
                                    idn_action_date=dn_terminate_date,
                                    idn_notification=dn_notification,
                                    i_default_days=general_config.get(
                                        "default_terminate_days"
                                    ),
                                    i_max_days=general_config.get("max_terminate_days"),
                                    notify_messages_config=notify_messages_config,
                                    d_run_date=d_run_date,
                                )

                                # Update all tags that have changed
                                tags_changed = [
                                    (
                                        tags_config.get("t_terminate_date"),
                                        dn_terminate_date,
                                        r["odn_action_date"],
                                    )
                                ]
                                for n, notif in enumerate(dn_notification):
                                    tags_changed.append(
                                        (
                                            notif[2],
                                            notif[0],
                                            r["odn_notification_{n}".format(n=n + 1)],
                                        )
                                    )
                                for tag in tags_changed:
                                    if tag[1] != tag[2]:
                                        aws_client.update_tag(
                                            instance_id,
                                            instance_name,
                                            tag[0],
                                            tag[2],
                                            tag[1],
                                        )

                                message = r["result"].format(
                                    instance_type="EC2",
                                    instance_name=instance_name,
                                    instance_id=instance_id,
                                    region=region,
                                    action="terminate",
                                    tag=tags_config.get("t_stop_date"),
                                    old_date=dn_terminate_date,
                                    new_date=r["odn_action_date"],
                                    state=state,
                                    n=r.get("n"),
                                )

                                detailed_log.append(
                                    add_to_log(
                                        email=owner_email,
                                        instance_type="EC2",
                                        instance_name=instance_name,
                                        instance_id=instance_id,
                                        region=region,
                                        action="terminate",
                                        tag=tags_config.get("t_terminate_date"),
                                        result=r["result"],
                                        old_date=dn_terminate_date,
                                        new_date=r["odn_action_date"],
                                        message=message,
                                    )
                                )

                                if r["result"] == "complete_action":
                                    # On complete, terminate the instance
                                    aws_client.terminate(
                                        instance_id,
                                        instance_name,
                                    )

                                    # Summary stop log
                                    aws_client.update_tag(
                                        instance_id,
                                        instance_name,
                                        tags_config.get("t_terminate_logs"),
                                        "notified:{};terminated:{}".format(
                                            ",".join(
                                                notif[0] for notif in dn_notification
                                            ),
                                            d_run_date,
                                        ),
                                        None,
                                    )
                                    # TODO: Add additional log for this?
                            else:
                                pass  # Placeholder for 'override' behavior

                        else:  # State is not running or stopped
                            message = notify_messages_config[
                                "ignore_other_states"
                            ].format(
                                instance_type="EC2",
                                instance_name=instance_name,
                                instance_id=instance_id,
                                region=region,
                                action="ignore",
                                tag=state,  # This is a hack
                                old_date=d_run_date,
                                new_date=d_run_date,
                                state=state,
                            )

                            detailed_log.append(
                                add_to_log(
                                    email=owner_email,
                                    instance_type="EC2",
                                    instance_name=instance_name,
                                    instance_id=instance_id,
                                    region=region,
                                    action="ignore",
                                    tag=state,  # again, this is a hack
                                    result="ignore_other_states",
                                    old_date=d_run_date,
                                    new_date=d_run_date,
                                    message=message,
                                )
                            )

                    else:  # Exception exists, add to notify list
                        message = notify_messages_config["skip_exception"].format(
                            instance_type="EC2",
                            instance_name=instance_name,
                            instance_id=instance_id,
                            region=region,
                            action="skip_exception",
                            tag=exception,
                            old_date=d_run_date,
                            new_date=d_run_date,
                            state=state,
                        )

                        detailed_log.append(
                            add_to_log(
                                email=owner_email,
                                instance_type="EC2",
                                instance_name=instance_name,
                                instance_id=instance_id,
                                region=region,
                                action="skip_exception",
                                tag=exception,  # This is a hack
                                result="skip_exception",
                                old_date=d_run_date,
                                new_date=d_run_date,
                                message=message,
                            )
                        )

                else:  # In autoscaling group
                    logging.info(
                        "Instance {} is in ASG {}, skipping".format(
                            instance_id,
                            autoscaling_group,
                        )
                    )
                    # TODO: Add log for these

        logging.info("Today is {}".format(d_run_date))
        # logging.info("Notification List:")

        # Arbitrary sort order, primarily for cleanliness in output:
        # * Email
        # * Type
        # * Region
        # * Action
        # * Result
        # * Name

        actions = ["ignore", "stop", "terminate"]
        for action in [*actions, [actions]]:
            if isinstance(action, str):  # actions
                action_list = sorted(
                    [x for x in detailed_log if x["action"] == action],
                    key=sort_key,
                )
                logging.info(
                    "{} List:".format(
                        action.upper(),
                    )
                )
            else:  # ALTERNATE (not in any action)
                action_list = sorted(
                    [x for x in detailed_log if x["action"] not in action],
                    key=sort_key,
                )
                logging.info("ALTERNATE List:")

            for item in action_list:
                logging.info(
                    json.dumps(
                        item,
                        indent=3,
                        default=datetime_handler,
                    )
                )
                slack_client.send_text(
                    "{}{}: {}".format(
                        "[DRY RUN] " if args.dry_run else "",
                        item["email"],
                        item["message"],
                    ),
                )

    except Exception:
        logging.error(sys_exc(sys.exc_info()))
