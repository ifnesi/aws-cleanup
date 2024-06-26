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
    sort_key,
    date_or_none,
    sys_exc,
    iso_format,
    datetime_handler,
)
from utils.aws_client import AWSClient
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
            aws_client = AWSClient("us-east-1")
            regions = aws_client.get_regions()

        logging.info("Using regions: {}".format(", ".join(regions)))

        detailed_log = list()
        for region in regions:
            logging.info("Processing region {}".format(region))
            aws_client = AWSClient(
                region,
                dry_run=args.dry_run,
                notify_messages_config=notify_messages_config,
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

                # TODO: combine ASG and exception test
                if autoscaling_group is None:
                    if exception is None:
                        state_map = {
                            "running": {
                                "action": "stop",
                                "action_tag_field_name": "t_stop_date",
                                "default_field_name": "default_stop_days",
                                "max_field_name": "max_stop_days",
                                "action_complete_logs_tag_field_name": "t_stop_logs",
                                "next_action": "terminate",
                                "next_action_tag_field_name": "t_terminate_date",
                                "next_action_default_field_name": "default_terminate_days",
                            },
                            "stopped": {
                                "action": "terminate",
                                "action_tag_field_name": "t_terminate_date",
                                "default_field_name": "default_terminate_days",
                                "max_field_name": "max_terminate_days",
                                "action_complete_logs_tag_field_name": "t_terminate_logs",
                                "next_action": None,
                                "next_action_tag_field_name": None,
                                "next_action_default_field_name": None,
                            },
                        }
                        if state in state_map:
                            action = state_map[state]["action"]
                            action_tag = tags_config.get(
                                state_map[state]["action_tag_field_name"]
                            )
                            # Current value of action date
                            action_current_date = date_or_none(
                                tags, action_tag
                            )
                            action_default_days = general_config.get(
                                state_map[state]["default_field_name"]
                            )
                            action_max_days = general_config.get(
                                state_map[state]["max_field_name"]
                            )
                            complete_logs_tag = tags_config.get(
                                state_map[state]["action_complete_logs_tag_field_name"]
                            )
                            next_action = state_map[state]["next_action"]
                            next_action_tag = tags_config.get(
                                state_map[state]["next_action_tag_field_name"]
                            )
                            next_action_default_days = general_config.get(
                                state_map[state]["next_action_default_field_name"]
                            )

                            r = determine_action(
                                idn_action_date=action_current_date,
                                idn_notification=dn_notification,
                                i_default_days=action_default_days,
                                i_max_days=action_max_days,
                                notify_messages_config=notify_messages_config,
                                d_run_date=d_run_date,
                            )

                            # Update all tags that have changed
                            tags_changed = [
                                (
                                    action_tag,
                                    action_current_date,
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
                                        instance_id=instance_id,
                                        instance_name=instance_name,
                                        tag=tag[0],  # key
                                        new_value=tag[2],  # value
                                        old_value=tag[1],  # days_n
                                    )

                            message_details = {
                                "email": owner_email,
                                "instance_type": "EC2",
                                "instance_name": instance_name,
                                "instance_id": instance_id,
                                "region": region,
                                "action": action,
                                "tag": action_tag,
                                "old_date": action_current_date,
                                "new_date": r["odn_action_date"],
                                "state": state,
                                "result": r["result"],
                            }

                            # Add message to message_details
                            message_details["message"] = r["message"].format(**message_details)

                            detailed_log.append(message_details)

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

                            if r["result"] == Result.COMPLETE_ACTION:
                                # TODO: Right now, the slack notification for this is sent before the completion events are run; do we need to send Slack notification again later?
                                
                                # Now need to do the following: # TODO FIX THIS LOGIC, something is missing here
                                # * Stop the instance
                                # * Add a termination date - done
                                # * Add a TERMINATE/TRANSITION log - done
                                # * TODO: Add "Summary stop tag" - done
                                # * Clear notifications - done
                                aws_client.do_action(
                                    action=action,
                                    instance_type="EC2",
                                    instance_id=instance_id,
                                    instance_name=instance_name,
                                )

                                # Populate completion logs tag
                                aws_client.update_tag(
                                    instance_id=instance_id,
                                    instance_name=instance_name,
                                    tag=complete_logs_tag,
                                    new_value="notified:{};{}:{}".format(
                                        ",".join(
                                            str(notif[0]) for notif in dn_notification
                                        ),
                                        action,
                                        d_run_date,
                                    ),
                                    old_value=None,
                                )

                                # Clear notification tags
                                for tag in dn_notification:
                                    aws_client.update_tag(
                                        instance_id=instance_id,
                                        instance_name=instance_name,
                                        tag=tag[2],
                                        new_value=None,
                                        old_value=tag[0],
                                    )

                                if next_action:
                                    # Create next action tag
                                    aws_client.update_tag(
                                        instance_id=instance_id,
                                        instance_name=instance_name,
                                        tag=next_action_tag,
                                        new_value=d_run_date + datetime.timedelta(days=next_action_default_days),
                                        old_value=None
                                    )

                                    transition_message_details = dict(message_details)
                                    transition_message_details["action"] = next_action
                                    transition_message_details["tag"] = next_action_tag
                                    transition_message_details["old_date"] = None
                                    transition_message_details["new_date"] = d_run_date + datetime.timedelta(days=next_action_default_days)
                                    transition_message_details["state"] = "stopped"
                                    transition_message_details["result"] = Result.TRANSITION_ACTION
                                    transition_message_details["message"] = notify_messages_config.get(Result.TRANSITION_ACTION).format(**transition_message_details)

                                    detailed_log.append(transition_message_details)

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

                        else:  # State not in state_map
                            message_details = {
                                "email": owner_email,
                                "instance_type": "EC2",
                                "instance_name": instance_name,
                                "instance_id": instance_id,
                                "region": region,
                                "action": "ignore",
                                "tag": state,  # again, this is a hack
                                "result": Result.IGNORE_OTHER_STATES,
                                "old_date": d_run_date,
                                "new_date": d_run_date,
                                "state": state,
                            }

                            message_text = notify_messages_config.get(Result.IGNORE_OTHER_STATES).format(**message_details)

                            message_details["message"] = message_text

                            detailed_log.append(message_details)

                            slack_client.send_text(
                                "{}{} [{}]: {}".format(
                                    "[DRY RUN] " if args.dry_run else "",
                                    message_details["email"],
                                    message_details["result"],
                                    message_details["message"],
                                ),
                            )

                    else:  # Exception exists, add to notify list
                        message_details = {
                            "email": owner_email,
                            "instance_type": "EC2",
                            "instance_name": instance_name,
                            "instance_id": instance_id,
                            "region": region,
                            "action": "skip_exception",
                            "tag": exception,  # See if this is right, I think this is wrong
                            "result": Result.SKIP_EXCEPTION,
                            "old_date": d_run_date,
                            "new_date": d_run_date,
                            "state": state,
                        }
                        message_text = notify_messages_config.get(Result.SKIP_EXCEPTION).format(**message_details)

                        message_details["message"] = message_text
                        
                        detailed_log.append(message_details)

                        slack_client.send_text(
                            "{}{} [{}]: {}".format(
                                "[DRY RUN] " if args.dry_run else "",
                                message_details["email"],
                                message_details["result"],
                                message_details["message"],
                            ),
                        )

                else:  # In autoscaling group
                    logging.info(
                        "Instance {} is in ASG {}, skipping".format(
                            instance_id,
                            autoscaling_group,
                        )
                    )
                    # TODO: Add log for these


        # Start output and notifications
        # TODO: Move Slack notifications closer to actual events
        logging.info("Today is {}".format(d_run_date))

        actions = ["ignore", "stop", "terminate"]
        for action in actions:
            logging.info(
                "{} List:".format(
                    action.upper(),
                )
            )
            action_list = sorted(
                [x for x in detailed_log if x["action"] == action],
                key=sort_key,
            )

            for item in action_list:
                logging.info(
                    json.dumps(
                        item,
                        indent=3,
                        default=datetime_handler,
                    )
                )
                # slack_client.send_text(
                #     "{}{} [{}]: {}".format(
                #         "[DRY RUN] " if args.dry_run else "",
                #         item["email"],
                #         item["result"],
                #         item["message"],
                #     ),
                # )
                # if item["email"] and item["result"] not in (
                #     Result.IGNORE_OTHER_STATES,
                #     Result.LOG_NO_NOTIFICATION,
                #     Result.SKIP_EXCEPTION,
                # ) and not args.dry_run:
                #     slack_client.send_dm(
                #         email = item["email"],
                #         text = item["message"],
                #     )
        # This is basically the list of items that weren't processed because they were in an unknown state
        logging.info("UNPROCESSED List:")
        action_list = sorted(
            [x for x in detailed_log if x["action"] not in actions],
            key=sort_key,
        )
        for item in action_list:
            logging.info(
                json.dumps(
                    item,
                    indent=3,
                    default=datetime_handler,
                )
            )
            # slack_client.send_text(
            #     "{}{}: {}".format(
            #         "[DRY RUN] " if args.dry_run else "",
            #         item["email"],
            #         item["message"],
            #     ),
            # )

    # except Exception:
    #     logging.error(sys_exc(sys.exc_info()))

    except KeyboardInterrupt:
        logging.info("Aborted by user!")
