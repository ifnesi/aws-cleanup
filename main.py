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
    log_item,
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
        instances_config = config.get("instances", dict())
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

        # detailed_log = list()
        for region in regions:
            logging.info("Processing region {}".format(region))

            for instance_type, instance_config in instances_config.items():
                aws_client = AWSClient(
                    region,
                    dry_run=args.dry_run,
                    service_name=instance_type,
                    notify_messages_config=notify_messages_config,
                    search_filter=override_config.get("test_filter"),
                )

                logging.info("Retrieving {} instances from region {}".format(instance_type, region))
                instances = aws_client.get_instances()

                # https://confluentinc.atlassian.net/wiki/spaces/~457145999/pages/3318745562/Cloud+Spend+Reduction+Proposal+AWS+Solutions+Engineering+Account
                for instance in instances:
                    state = instance["State"]["Name"]

                    instance_details = {
                        "instance_type": instance_type,
                        "instance_id": instance["InstanceId"],
                        "region": region,
                    }

                    logging.info(
                        "Processing {state} {instance_type} instance {instance_id} in region {region}".format(
                            state=state,
                            instance_type=instance_type,
                            instance_id=instance_details["instance_id"],
                            region=region,
                        )
                    )

                    if "Tags" not in instance:
                        instance_tags = dict()
                    else:
                        instance_tags = {tag["Key"]: tag["Value"] for tag in instance["Tags"]}

                    # Get tags matching any of the exception tags; if any exist, don't process.
                    # returns a list of tuples; each tuple is ('tag', 'value')
                    # using a list becuase it's ordered
                    exceptions = [(e_tag, instance_tags.get(e_tag)) for e_tag in instance_config.get("exception_tags") if instance_tags.get(e_tag)]

                    state_map = instance_config.get("states")

                    instance_details["instance_name"] = instance_tags.get(tags_config.get("t_name"))

                    # 'dn_' means 'either a Datetime.date or None'
                    dn_notification = (
                        list()
                    )  # [(tag_name_value_1, days_1, tag_name_1), (tag_name_value_2, days_2, tag_name_2), ..., (tag_name_value_n, days_n, tag_name_n)]
                    for tag_name, days in tags_notifications:
                        dn_notification.append(
                            [
                                date_or_none(
                                    instance_tags,
                                    tag_name,
                                ),
                                days,
                                tag_name,
                            ]
                        )

                    # Rough equivalent to coalesce
                    instance_details["email"] = (
                        instance_tags.get(tags_config.get("t_owner_email"))
                        or instance_tags.get(tags_config.get("t_email"))
                        or instance_tags.get(tags_config.get("t_divvy_owner"))
                        or instance_tags.get(tags_config.get("t_divvy_last_modified_by"))
                    )

                    # TODO: combine ASG and exception test
                    if len(exceptions) == 0:
                        if state in state_map:
                            state_config = state_map[state]
                            action = state_config["action"]
                            action_tag = state_config["action_tag"]
                            complete_logs_tag = state_config["action_log_tag"]
                            action_default_days = state_config["default_days"]
                            action_max_days = state_config["max_days"]

                            next_state = state_config.get("next_state")

                            # Current value of action date
                            action_current_date = date_or_none(
                                instance_tags, action_tag
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
                            tags_changed = {
                                action_tag: {
                                    "old": action_current_date,
                                    "new": r["odn_action_date"],
                                }
                            }
                            for n, notif in enumerate(dn_notification):
                                tags_changed[notif[2]] = {
                                    "old": notif[0],
                                    "new": r["odn_notification_{}".format(n + 1)],
                                }

                            if r["result"] == Result.COMPLETE_ACTION:
                                # If we have a 'complete' action, do all of the following
                                # (before tag updates and Slack notification)
                                # * Perform the action (stop/terminate)
                                # * Add an action complete log (including notifications)
                                # * Clear individual notification tags
                                # * If there's a next action:
                                    # * Add a next action date tag - done
                                    # * Send a transition notification
                                    # TODO: Right now the transition notification occurs before the complete notification; is this okay?

                                aws_client.do_action(
                                    action=action,
                                    **instance_details,
                                )

                                tags_changed[complete_logs_tag] = {
                                    "old": None,
                                    "new": "notified:{};{}:{}".format(
                                        ",".join(
                                            str(notif[0]) for notif in dn_notification
                                        ),
                                        action,
                                        d_run_date,
                                    )
                                }

                                # Clear notification tags (set back to None)
                                for n, notif in enumerate(dn_notification):
                                    tags_changed[notif[2]] = {
                                        "old": notif[0],
                                        "new": None,
                                    }
                                
                                if next_state:

                                    next_state_config = state_map[next_state]

                                    tags_changed[next_state_config["action_tag"]] = {
                                        "old": None,
                                        "new": d_run_date + datetime.timedelta(days=next_state_config["default_days"]),
                                    }

                                    transition_message_details = dict(message_details)
                                    transition_message_details["action"] = next_state_config["action"]
                                    transition_message_details["tag"] = next_state_config["action_tag"]
                                    transition_message_details["old_date"] = None
                                    transition_message_details["new_date"] = d_run_date + datetime.timedelta(days=next_state_config["default_days"])
                                    transition_message_details["state"] = "stopped"
                                    transition_message_details["result"] = Result.TRANSITION_ACTION
                                    transition_message_details["message"] = notify_messages_config.get(Result.TRANSITION_ACTION).format(**transition_message_details)

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

                            # Filter by tags that have new values
                            updated_tags = {
                                tag: values for tag,values in tags_changed.items() if values["old"] != values["new"]
                            }
                            
                            if(len(updated_tags) > 0):
                                aws_client.update_tags(
                                    **instance_details,
                                    updated_tags=updated_tags,
                                )

                            message_details = {
                                **instance_details,
                                "action": action,
                                "tag": action_tag,
                                "old_date": action_current_date,
                                "new_date": r["odn_action_date"],
                                "state": state,
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
                        else:  # State not in state_map
                            message_details = {
                                **instance_details,
                                "action": "ignore",
                                "tag": state,  # again, this is a hack
                                "result": Result.IGNORE_OTHER_STATES,
                                "old_date": d_run_date,
                                "new_date": d_run_date,
                                "state": state,
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

                    else: # In ASG or has an exception (exception takes precedence for notification)
                        message_details = {
                            **instance_config,
                            "action": Result.SKIP_EXCEPTION,
                            "tag": exceptions[0][0],  # See if this is right, I think this is wrong
                            "result": Result.SKIP_EXCEPTION,
                            "old_date": d_run_date,
                            "new_date": exceptions[0][1],
                            "state": state,
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

        # actions = ["ignore", "stop", "terminate"]
        # for action in actions:
        #     logging.info(
        #         "{} List:".format(
        #             action.upper(),
        #         )
        #     )
        #     action_list = sorted(
        #         [x for x in detailed_log if x["action"] == action],
        #         key=sort_key,
        #     )

        #     for item in action_list:
        #         logging.info(
        #             json.dumps(
        #                 item,
        #                 indent=3,
        #                 default=datetime_handler,
        #             )
        #         )
        # # This is basically the list of items that weren't processed because they were in an unknown state
        # logging.info("UNPROCESSED List:")
        # action_list = sorted(
        #     [x for x in detailed_log if x["action"] not in actions],
        #     key=sort_key,
        # )
        # for item in action_list:
        #     logging.info(
        #         json.dumps(
        #             item,
        #             indent=3,
        #             default=datetime_handler,
        #         )
        #     )

    except KeyboardInterrupt:
        logging.info("Aborted by user!")
