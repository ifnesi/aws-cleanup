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
import datetime
from .result import Result


def determine_action(
    idn_action_date: datetime,
    idn_notification: list,
    i_default_days: int,
    i_max_days: int,
    notify_messages_config: dict,
    d_run_date: datetime,
):
    """
    Takes the following:
    - idn_action_date: Currently set action date
    - idn_notification: (list) Current dn_notification [(tag_name_value_1, days_1, tag_name_1), (tag_name_value_2, days_2, tag_name_2), ..., (tag_name_value_n, days_n, tag_name_n)]
    - i_default_days: Default number of days
    - i_max_days: Max number of days
    - notify_messages_config: As per config (notify_messages)
    - d_run_date: run date
    Returns dict with the following:
    - odn_notification_1: New dn_notification_1
    - odn_notification_2: New dn_notification_2
    - ...
    - odn_notification_n: New dn_notification_n
    - odn_action_date
    - result: enum
    - n: notification number (or -1 if not applicable)
    All actual changes (tags and/or instance modification) occurs in calling code, not here.
    """
    odn_notif = dict()
    odn_notif_none = dict()
    for n, notif in enumerate(idn_notification):
        odn_notif["odn_notification_{}".format(n + 1)] = notif[0]
        odn_notif_none["odn_notification_{}".format(n + 1)] = None

    logging.debug(
        "idn_action_date:[{idn_action_date}], {idn_notifications}, i_default_days:[{i_default_days}], i_max_days:[{i_max_days}]".format(
            idn_action_date=idn_action_date,
            idn_notifications=", ".join(
                [
                    "{}:[{}]".format(
                        key,
                        value,
                    )
                    for key, value in odn_notif.items()
                ]
            ),
            i_default_days=i_default_days,
            i_max_days=i_max_days,
        )
    )

    if idn_action_date is None:
        # Result: Set Unset date
        return {
            **odn_notif_none,
            "odn_action_date": d_run_date + datetime.timedelta(days=i_default_days),
            "result": Result.ADD_ACTION_DATE,
            "message": notify_messages_config.get(Result.ADD_ACTION_DATE),
        }

    elif idn_action_date - d_run_date > datetime.timedelta(days=i_max_days):
        # Result: Set date to max
        return {
            **odn_notif_none,
            "odn_action_date": d_run_date + datetime.timedelta(days=i_max_days),
            "result": Result.RESET_ACTION_DATE,
            "message": notify_messages_config.get(Result.RESET_ACTION_DATE),
        }

    elif idn_action_date <= d_run_date:
        max_notif_days = len(idn_notification)
        odn_notif_aux = dict(odn_notif_none)  # Make copy of dictionary
        for n, notif in enumerate(idn_notification):
            odn_notif_aux[
                "odn_notification_{}".format(
                    n + 1,
                )
            ] = d_run_date
            if n > 0:
                odn_notif_aux["odn_notification_{}".format(n)] = idn_notification[
                    n - 1
                ][0]
            if notif[0] is None:
                # Bumpo and set stop date to today + N (missing notifications)
                # Kind of prefer using String `replace()` rather than passing back a variable just for this condition
                return {
                    **odn_notif_aux,
                    "odn_action_date": d_run_date
                        + datetime.timedelta(days=max_notif_days - n),
                    "result": Result.PAST_BUMP_NOTIFICATION,
                    "message": notify_messages_config.get(Result.PAST_BUMP_NOTIFICATION).replace("__N__", str(n + 1)),
                }

        # Result: Complete action
        odn_notif_aux[
            "odn_notification_{}".format(len(idn_notification))
        ] = idn_notification[-1][0]
        return {
            **odn_notif_aux,
            "odn_action_date": d_run_date,
            "result": Result.COMPLETE_ACTION,
            "message": notify_messages_config.get(Result.COMPLETE_ACTION),
        }

    else:
        remaining_days = idn_action_date - d_run_date
        odn_notif_aux = dict(odn_notif_none)  # Make copy of dictionary
        for n, notif in enumerate(idn_notification):
            odn_notif_aux[
                "odn_notification_{}".format(
                    n + 1,
                )
            ] = d_run_date
            if n > 0:
                odn_notif_aux["odn_notification_{}".format(n)] = idn_notification[
                    n - 1
                ][0]
            if notif[0] is None and remaining_days <= datetime.timedelta(days=notif[1]):
                # Result: Send nth notification
                return {
                    **odn_notif_aux,
                    "odn_action_date": idn_action_date,
                    "result": Result.SEND_NOTIFICATION,
                    "message": notify_messages_config.get(Result.SEND_NOTIFICATION).replace("__N__", str(n + 1)),
                }

        # Result: Log without notification
        odn_notif_aux[
            "odn_notification_{}".format(len(idn_notification))
        ] = idn_notification[-1][0]
        return {
            **odn_notif_aux,
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


# Arbitrary sort order, primarily for cleanliness in output:
# * Email
# * Type
# * Region
# * Action
# * Result
# * Name
def sort_key(x):
    return " ".join(
        [
            x["email"],
            x["instance_type"],
            x["region"],
            x["action"],
            x["result"],
            x["instance_name"],
        ]
    )

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
