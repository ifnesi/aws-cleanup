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
import logging
import json
import datetime
import collections
from utils.result import Result


def determine_action(
    d_run_date: datetime,
    idn_action_date: datetime,
    i_default_days: int,
    i_max_days: int,
    idn_notification: dict,
    notify_messages_config: dict,
):
    """
    Takes the following:
    - d_run_date (datetime.date): evaluation date
    - idn_action_date (datetime.date): currently configured action date
    - i_default_days: default number of days
    - i_max_days: maximum number of days
    - idn_notification: (dict > dict): mapping of notification tags to dict containing:
        {
            "old" (datetime.date): <current tag value>,
            "days" (int): <number of days for notification>,
        }
    - notify_messages_config (dict > string): mapping of result types to message templates
    Returns dict with the following:
    - odn_notification: (dict> dict): mapping of notification tags to dict containing:
        {
            "old" (datetime.date): <current tag value>,
            "days" (int): <number of days for notification>,
            "new" (datetime.date): <new tag value>,
        }
    - odn_action_date (datetime.date): new action date
    - result: Result enum
    All actual changes (tags and/or instance modification) occurs in calling code, not here.

    Sample `idn_notification`:
    idn_notification = {
        "aws_cleaner/terminate/notifications/1": {"old": datetime.date(2024, 7, 22),"days": 15},
        "aws_cleaner/terminate/notifications/2": {"old": None, "days": 8},
        "aws_cleaner/terminate/notifications/3": {"old": None, "days": 2}
    }
    """
    # Sort by notification days (in descending order)
    # Store in OrderedDict (not necessary in Python 3.7+, but used for clarity)
    idn_xnotification = collections.OrderedDict(
        sorted(idn_notification.items(),
               key=lambda item: item[1]["days"],
               reverse=True))

    # Same as idn_notification, but with "new" set to None (used to reset notifications)
    odn_xnotif_none = collections.OrderedDict()
    # Same as idn_notification, but with "new" set to same value as "old" (no change)
    odn_xnotif_same = collections.OrderedDict()

    for k,v in idn_xnotification.items():
        odn_xnotif_none[k] = v | {"new": None}
        odn_xnotif_same[k] = v | {"new": v["old"]}

    if idn_action_date is None:
        # Result: Set Unset date
        return {
            "odn_notification": odn_xnotif_none,
            "odn_action_date": d_run_date + datetime.timedelta(days=i_default_days),
            "result": Result.ADD_ACTION_DATE,
            "message": notify_messages_config.get(Result.ADD_ACTION_DATE),
        }

    elif idn_action_date - d_run_date > datetime.timedelta(days=i_max_days):
        # Result: Set date to max
        return {
            "odn_notification": odn_xnotif_none,
            "odn_action_date": d_run_date + datetime.timedelta(days=i_max_days),
            "result": Result.RESET_ACTION_DATE,
            "message": notify_messages_config.get(Result.RESET_ACTION_DATE),
        }

    elif idn_action_date <= d_run_date:
        # Action date in the past: one of two actions:
        # If we're missing a notification, notify and bump action date
        # Otherwise, complete action
        notifications_sent = len([v["old"] for k,v in idn_xnotification.items() if v["old"] is not None])
        if notifications_sent < len(idn_xnotification):
            # Take 'same' result and update "new" to new value
            # Note: as of Python 3.7, dictionaries _are_ ordered.
            odn_xnotif_same[list(idn_xnotification)[notifications_sent]]["new"] = d_run_date

            # Bump action date by number of missing notifications
            return {
                "odn_notification": odn_xnotif_same,
                "odn_action_date": d_run_date
                + datetime.timedelta(days=len(idn_xnotification) - notifications_sent),
                "result": Result.PAST_BUMP_NOTIFICATION,
                "message": notify_messages_config.get(
                    Result.PAST_BUMP_NOTIFICATION
                ).replace("__N__", str(notifications_sent + 1)),
            }
        return {
            "odn_notification": odn_xnotif_same,
            "odn_action_date": d_run_date,
            "result": Result.COMPLETE_ACTION,
            "message": notify_messages_config.get(Result.COMPLETE_ACTION),
        }

    else:
        # Action date is in the future, but not too far in the future, three potential options:
        # * Send regular notification (if in notification period)
        # * Reset notifications (if notifications have been sent, but date has manually been pushed back)
        # * No notification

        # For each notification, notification date is action date - # of days (notify if past this date)
        for n,(tag,config) in enumerate(idn_xnotification.items()):
            if config["old"] is None and d_run_date > idn_action_date - datetime.timedelta(config["days"]):
                odn_xnotif_same[tag]["new"] = d_run_date
                return {
                    "odn_notification": odn_xnotif_same,
                    "odn_action_date": idn_action_date,
                    "result": Result.SEND_NOTIFICATION,
                    "message": notify_messages_config.get(
                        Result.SEND_NOTIFICATION
                    ).replace("__N__", str(n + 1)),
                }

        remaining_days = idn_action_date - d_run_date
        first_notification = list(idn_xnotification.values())[0]["days"]
        if (remaining_days > datetime.timedelta(days = first_notification)
            and (len([c for c in idn_xnotification.values() if c["old"] is not None]) > 0)):
            # Reset notifications if there are any notifications but shouldn't be
            return {
                "odn_notification": odn_xnotif_none,
                "odn_action_date": idn_action_date,
                "result": Result.RESET_NOTIFICATIONS,
                "message": notify_messages_config.get(Result.RESET_NOTIFICATIONS)
            }
        
        
        # Result: Log without notification
        return {
            "odn_notification": odn_xnotif_same,
            "odn_action_date": idn_action_date,
            "result": Result.LOG_NO_NOTIFICATION,
            "message": notify_messages_config.get(Result.LOG_NO_NOTIFICATION),
        }


def iso_format(date: str):
    try:
        if date:
            result = datetime.date.fromisoformat(date)
        else:
            result = None
    except Exception:
        raise ValueError("Invalid ISO date format, please try yyyy-mm-dd")
    return result


# # Arbitrary sort order, primarily for cleanliness in output:
# # * Email
# # * Type
# # * Region
# # * Action
# # * Result
# # * Name
# def sort_key(x):
#     return " ".join(
#         [
#             x["email"],
#             x["instance_type"],
#             x["region"],
#             x["action"],
#             x["result"],
#             x["instance_name"],
#         ]
#     )


def date_or_none(
    tags,
    tag,
):
    """
    Convert to a datetime.date on the way (or return None)
    """
    try:
        return datetime.date.fromisoformat(tags.get(tag))
    except Exception:
        return None


def sys_exc(exc_info):
    """
    Capture exception type, class and line number
    """
    exc_type, exc_obj, exc_tb = exc_info
    return "{} | {} | {}".format(
        exc_type,
        exc_tb.tb_lineno,
        exc_obj,
    )


def datetime_handler(o):
    if isinstance(
        o,
        (
            datetime.datetime,
            datetime.date,
            datetime.time,
            bytes,
        ),
    ):
        return str(o)

def log_item(item):
    logging.info(
        json.dumps(
            item,
            indent=3,
            default=datetime_handler,
        )
    )