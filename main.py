#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 Confluent Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# BY DEFAULT, WILL ONLY RUN AGAINST TEST INSTANCES
# MUST USE --full FLAG TO RUN AGAINST WHOLE ACCOUNT

# On fresh Ubuntu instance, install prereqs:
# sudo apt-get update; sudo apt-get install -y python3-pip;
# python3 -m pip install -r requirements.txt
#
import os
import sys
import json
import yaml
import logging
import argparse
import datetime

from utils import (
    determine_action,
    date_or_none,
    sys_exc,
    iso_format,
    datetime_handler,
    log_item,
)

# from utils.aws.generic_instance import GenericInstance
from utils.aws import *
from utils.aws.aws_client import AWSClient
from utils.aws.rds_client import RDSClient
from utils.aws.ec2_client import EC2Client
from utils.aws.asg_client import ASGClient
# I don't know why I have to explicitly import ASGClient, but not RDSClient or EC2Client
from utils.slack_client import SlackClient
from utils.result import Result


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
        help="Set YAML configuration file (default is: config/default_config.yaml)",
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
        "--region",
        help="Specify region to use",
        action="append",
        dest="region",
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
        global_config = config.get("global", dict()) or dict()
        instances_config = config.get("instances", dict())
        tags_config = config.get("tags", dict())
        notify_messages_config = config.get("notify_messages", dict())
        email_tags_config = config.get("email_tags", list())
        regions = global_config.get("regions", list())

        if args.run_date:
            d_run_date = args.run_date
        else:
            d_run_date = D_TODAY

        if args.region:
            regions = args.region

        slack_client = SlackClient(slack_config)

        # We won't send most stuff to Slack, but use this to validate that connection is okay and indicate the script is starting
        start_text = (
            "Running cleaner on {}".format(d_run_date)
            if d_run_date == D_TODAY
            else "Running cleaner on simulated run date of {}".format(d_run_date)
        )
        slack_client.send_text_and_log(start_text)

        if regions:
            # use test region filter
            logging.info("Using regions provided in global.regions")
        else:
            aws_client = AWSClient("us-east-1")
            regions = aws_client.get_regions()

        slack_client.send_text_and_log("Using regions: {}".format(", ".join(regions)))

        for region in regions:
            slack_client.send_text_and_log("Processing {} in region {}".format(
                ", ".join([instance_type for instance_type, type_config in instances_config.items() if type_config.get("enabled")]),
                region,
                ))

            # Instance type is EC2, RDS, etc.
            for instance_type, type_config in instances_config.items():
                if type_config.get("enabled"):
                    slack_client.send_text_and_log("Retrieving {} instances from region {}".format(instance_type, region))
                    instance_config = type_config.get("config")

                    if instance_type == 'ec2':
                        aws_client = EC2Client(
                            region,
                            dry_run=args.dry_run,
                            service_name=instance_type,
                            notify_messages_config=notify_messages_config,
                            email_tags=email_tags_config,
                        )
                    elif instance_type == 'rds':
                        aws_client = RDSClient(
                            region,
                            dry_run=args.dry_run,
                            service_name=instance_type,
                            notify_messages_config=notify_messages_config,
                            email_tags=email_tags_config,
                        )
                    elif instance_type == 'autoscaling':
                        aws_client = ASGClient(
                            region,
                            dry_run=args.dry_run,
                            service_name=instance_type,
                            notify_messages_config=notify_messages_config,
                            email_tags=email_tags_config,
                        )
                    else:
                        aws_client = AWSClient(
                            region,
                            dry_run=args.dry_run,
                            service_name=instance_type,
                            notify_messages_config=notify_messages_config,
                            email_tags=email_tags_config,
                        )

                    instances = aws_client.get_instances(instance_config=instance_config)

                    state_map = type_config.get("states")

                    included = [instance["state"] for instance in instances if instance["state"] in state_map]
                    excluded = [instance["state"] for instance in instances if instance["state"] not in state_map]
                    included_states = set(included)
                    excluded_states = set(excluded)

                    included_state_counts = {
                        state: sum([1 for instance in instances if state == instance.state])
                        for state in included_states
                    }
                    excluded_state_counts = {
                        state: sum([1 for instance in instances if state == instance.state])
                        for state in excluded_states
                    }

                    total_text = "Total {type} instances found: {total}".format(
                        total=len(instances),
                        type=instance_type,
                        )
                    
                    included_text = "{total} will be processed: {c}".format(
                        total=len(included),
                        c=", ".join(
                            ["{} {}".format(v, k) for k,v in included_state_counts.items()]
                        )
                    )
                    excluded_text = "{total} will not be processed (not currently handled by script): {c}".format(
                        total=len(excluded),
                        c=", ".join(
                            ["{} {}".format(v, k) for k,v in excluded_state_counts.items()]
                        )
                    )

                    slack_client.send_text_and_log(total_text)
                    if len(included) > 0:
                        slack_client.send_text_and_log(included_text)
                    if len(excluded) > 0:
                        slack_client.send_text_and_log(excluded_text)

                    # States are started, stopped, scaled, etc.
                    for state in state_map:
                        state_config = state_map[state]

                        action = state_config["action"]
                        action_tag = state_config["action_tag"]
                        complete_logs_tag = state_config["action_log_tag"]
                        action_default_days = state_config["default_days"]
                        action_max_days = state_config["max_days"]

                        next_state = state_config.get("next_state")

                        state_notification_tags = state_config.get("notifications")
                        # Results in list of tuples:
                        # [
                        #   ("aws_cleaner/notifications/1": 15),
                        #   (tag_name_2: days_2),
                        #   ...,
                        #   (tag_name_n: days_n)
                        # ]
                        # (sorted by days, in descending order)
                        state_notifications = sorted(
                            state_notification_tags.items(),
                            key=lambda n: n[1],
                            reverse=True
                        )

                        state_instances = [instance for instance in instances if state == instance.state]

                        # Process in order by state; exceptions are processed with their state rather than separate
                        for instance in state_instances:

                            logging.info(
                                "Processing {state} {type} instance {id} in region {region}".format(**instance)
                            )

                            if len(instance.exceptions) == 0:

                                # Current value of action date
                                action_current_date = date_or_none(
                                    instance.tags, action_tag
                                )

                                dn_notification = dict()
                                for notification_tag, days in state_notifications:
                                    dn_notification[notification_tag] = {
                                        "old": date_or_none(instance.tags, notification_tag),
                                        "days": days,
                                    }
                                # dn_notification = {
                                #     <tag>: {"old": <current tag value>, "days": >notification days>},
                                #     'aws_cleaner/terminate/notifications/1': {"old": datetime.date(2024, 7, 22),"days": 15},
                                #     'aws_cleaner/terminate/notifications/2': {"old": None, "days": 8},
                                #     'aws_cleaner/terminate/notifications/3': {"old": None, "days": 2}
                                # }

                                r = determine_action(
                                    idn_action_date=action_current_date,
                                    idn_notification=dn_notification,
                                    i_default_days=action_default_days,
                                    i_max_days=action_max_days,
                                    notify_messages_config=notify_messages_config,
                                    d_run_date=d_run_date,
                                )

                                # Update all tags that have changed
                                tags = {
                                    action_tag: {
                                        "old": action_current_date,
                                        "new": r["odn_action_date"],
                                    }
                                }
                                tags |= r["odn_notification"]

                                if r["result"] == Result.COMPLETE_ACTION:
                                    # If we have a 'complete' action, do all of the following (before tag updates and Slack notification)
                                    # * Perform the action (stop/terminate)
                                    # * Add an action complete log (including notifications) tag
                                    # * If there's a next action:
                                        # * Add a next action date tag - done
                                        # * Send a transition notification

                                    aws_client.do_action(
                                        action=action,
                                        **instance,
                                    )

                                    tags[complete_logs_tag] = {
                                        "old": None,
                                        "new": "/".join(
                                            ["notified:{}".format(v["new"]) for k,v in r["odn_notification"].items()]
                                            + ["{}:{}".format(action, d_run_date)]
                                        )
                                    }
                                    
                                    if next_state:
                                        next_state_config = state_map[next_state]

                                        tags[next_state_config["action_tag"]] = {
                                            "old": None,
                                            "new": d_run_date + datetime.timedelta(days=next_state_config["default_days"]),
                                        }

                                        transition_message_details = dict(instance)
                                        transition_message_details["action"] = next_state_config["action"]
                                        transition_message_details["tag"] = next_state_config["action_tag"]
                                        transition_message_details["old_date"] = None
                                        transition_message_details["new_date"] = d_run_date + datetime.timedelta(days=next_state_config["default_days"])
                                        transition_message_details["state"] = "stopped" # TODO FIX
                                        transition_message_details["result"] = Result.TRANSITION_ACTION
                                        transition_message_details["message"] = notify_messages_config.get(Result.TRANSITION_ACTION).format(**transition_message_details)
                                        # transition_message_details is populated here, but used later so transition notification occurs after action complete action

                                        for tag in next_state_config["notifications"]:
                                            tags[tag] = {
                                                "old": date_or_none(instance.tags, tag),
                                                "new": None,
                                            }

                                # Filter by tags that have new values
                                updated_tags = {
                                    tag: values for tag,values in tags.items() if values["old"] != values["new"]
                                }
                                
                                if(len(updated_tags) > 0):
                                    aws_client.update_tags(
                                        **instance,
                                        updated_tags=updated_tags,
                                    )

                                message_details = {
                                    **instance,
                                    "action": action,
                                    "tag": action_tag,
                                    "old_date": action_current_date,
                                    "new_date": r["odn_action_date"],
                                    "state": instance.state,
                                    "result": r["result"],
                                }

                                # Add message to message_details
                                message_details["message"] = r["message"].format(**message_details)

                                # detailed_log.append(message_details)
                                log_item(message_details)

                                slack_client.send_text(
                                    "{}{} [{}]: {}".format(
                                        "[DRY RUN] " if args.dry_run else "",
                                        message_details["email"],
                                        message_details["result"],
                                        message_details["message"],
                                    ),
                                )

                                if message_details["email"] and message_details["result"] not in (
                                    Result.LOG_NO_NOTIFICATION,
                                ) and not args.dry_run:
                                    slack_client.send_dm(
                                        email = message_details["email"],
                                        text = message_details["message"],
                                    )

                                if r["result"] == Result.COMPLETE_ACTION and next_state:
                                    # detailed_log.append(transition_message_details)
                                    log_item(transition_message_details)

                                    slack_client.send_text(
                                        "{}{} [{}]: {}".format(
                                            "[DRY RUN] " if args.dry_run else "",
                                            transition_message_details["email"],
                                            transition_message_details["result"],
                                            transition_message_details["message"],
                                        ),
                                    )

                                    if transition_message_details["email"] and not args.dry_run:
                                        slack_client.send_dm(
                                            email = transition_message_details["email"],
                                            text = transition_message_details["message"],
                                        )

                            else: # Exception list is not empty
                                message_details = {
                                    **instance,
                                    "action": Result.SKIP_EXCEPTION,
                                    "tag": instance.exceptions[0][0],  # TODO verify this is right, I think this is wrong
                                    "result": Result.SKIP_EXCEPTION,
                                    "old_date": d_run_date,
                                    "new_date": instance.exceptions[0][1],
                                    "state": instance.state,
                                }
                                message_text = notify_messages_config.get(
                                    Result.SKIP_EXCEPTION
                                ).format(**message_details)

                                message_details["message"] = message_text

                                # detailed_log.append(message_details)
                                log_item(message_details)

                                slack_client.send_text(
                                    "{}{} [{}]: {}".format(
                                        "[DRY RUN] " if args.dry_run else "",
                                        message_details["email"],
                                        message_details["result"],
                                        message_details["message"],
                                    ),
                                )

                    for instance in [i for i in instances if i.state not in state_map]:
                        message_details = {
                            **instance,
                            "action": "ignore",
                            "tag": instance.state,  # again, this is a hack
                            "result": Result.IGNORE_OTHER_STATES,
                            "old_date": d_run_date,
                            "new_date": d_run_date,
                            "state": instance.state,
                        }

                        message_text = notify_messages_config.get(Result.IGNORE_OTHER_STATES).format(**message_details)

                        message_details["message"] = message_text

                        # detailed_log.append(message_details)
                        log_item(message_details)

                        slack_client.send_text(
                            "{}{} [{}]: {}".format(
                                "[DRY RUN] " if args.dry_run else "",
                                message_details["email"],
                                message_details["result"],
                                message_details["message"],
                            ),
                        )
                else:
                    logging.info("Skipping {} instances in region {}".format(instance_type, region))

        # We won't send most stuff to Slack, but use this to validate that connection is okay and indicate the script is starting
        end_text = (
            "Finished running cleaner on {}".format(d_run_date)
            if d_run_date == D_TODAY
            else "Finished running cleaner on simulated run date of {}".format(d_run_date)
        )
        slack_client.send_text_and_log(end_text)

    except KeyboardInterrupt:
        logging.info("Aborted by user!")
