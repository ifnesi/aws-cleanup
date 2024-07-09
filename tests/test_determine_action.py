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
import yaml
import pytest
import datetime
import os

# from utils.slack_client import SlackClient
# from utils.aws import AWSClient
from utils import determine_action,Result

config_file = os.path.join("config", "default_config.yaml")

with open(config_file, "r") as f:
    config = yaml.safe_load(f)

notify_config = config.get("notify_messages")

d_today = datetime.date.today()
d_1  = datetime.date.today() + datetime.timedelta(days = 1)
d_2  = datetime.date.today() + datetime.timedelta(days = 2)
d_3  = datetime.date.today() + datetime.timedelta(days = 3)
d_5  = datetime.date.today() + datetime.timedelta(days = 5)
d_8  = datetime.date.today() + datetime.timedelta(days = 8)
d_20 = datetime.date.today() + datetime.timedelta(days = 20)
d_31 = datetime.date.today() + datetime.timedelta(days = 31)
d_40 = datetime.date.today() + datetime.timedelta(days = 40)
d_62 = datetime.date.today() + datetime.timedelta(days = 62)
d_80 = datetime.date.today() + datetime.timedelta(days = 80)

d_p1 = datetime.date.today() - datetime.timedelta(days = 1)

t_n1 = "aws_cleaner/notifications/1"
t_n2 = "aws_cleaner/notifications/2"
t_n3 = "aws_cleaner/notifications/3"

i_default = {
    "i_default_days": 31,
    "i_max_days": 62,
    "notify_messages_config": notify_config,
    "d_run_date": d_today,
}

# Basic functionality test
def test_determine_action_hello_world():
    idn_notification = {
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": d_p1, "days":  7},
        t_n3: {"old": d_p1, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": d_p1},
        t_n2: {"old": d_p1, "days":  7, "new": d_p1},
        t_n3: {"old": d_p1, "days":  2, "new": d_p1},
    }

    result = determine_action(
        idn_action_date= d_today,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.COMPLETE_ACTION
    assert result["odn_action_date"] == d_today
    assert result["odn_notification"] == odn_notification

def test_missing_action_date():
    # Missing action date, should add one (also, reset notifications to none)
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": d_p1, "days":  7},
        t_n3: {"old": d_p1, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": None},
        t_n2: {"old": d_p1, "days":  7, "new": None},
        t_n3: {"old": d_p1, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date= None,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.ADD_ACTION_DATE
    assert result["odn_action_date"] == d_31
    assert result["odn_notification"] == odn_notification

def test_future_action_date_too_far():
    # Future action date too far in the future, should pull it in (also, reset notifications to none)
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": d_p1, "days":  7},
        t_n3: {"old": d_p1, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": None},
        t_n2: {"old": d_p1, "days":  7, "new": None},
        t_n3: {"old": d_p1, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date= d_80,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.RESET_ACTION_DATE
    assert result["odn_action_date"] == d_62
    assert result["odn_notification"] == odn_notification

def test_future_action_date():
    # Future action date, should do nothing
    idn_notification ={
        t_n1: {"old": None, "days": 15},
        t_n2: {"old": None, "days":  7},
        t_n3: {"old": None, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": None, "days": 15, "new": None},
        t_n2: {"old": None, "days":  7, "new": None},
        t_n3: {"old": None, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date= d_31,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.LOG_NO_NOTIFICATION
    assert result["odn_action_date"] == d_31
    assert result["odn_notification"] == odn_notification

def test_past_0_notifications_sent():
    ## action date in the past, no notifications sent; should bump to today + 3 days (and send first notification)
    idn_notification ={
        t_n1: {"old": None, "days": 15},
        t_n2: {"old": None, "days":  7},
        t_n3: {"old": None, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": None, "days": 15, "new": d_today},
        t_n2: {"old": None, "days":  7, "new": None},
        t_n3: {"old": None, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date= d_p1,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.PAST_BUMP_NOTIFICATION
    assert result["odn_action_date"] == d_3
    assert result["odn_notification"] == odn_notification
    assert result["message"] == notify_config[Result.PAST_BUMP_NOTIFICATION].replace("__N__", str(1))

def test_past_1_notifications_sent():
    ## action date in the past, 1 notifications sent; should bump to today + 2 days (and send second notification)
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": None, "days":  7},
        t_n3: {"old": None, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": d_p1},
        t_n2: {"old": None, "days":  7, "new": d_today},
        t_n3: {"old": None, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date= d_p1,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.PAST_BUMP_NOTIFICATION
    assert result["odn_action_date"] == d_2
    assert result["odn_notification"] == odn_notification
    assert result["message"] == notify_config[Result.PAST_BUMP_NOTIFICATION].replace("__N__", str(2))

def test_past_2_notifications_sent():
    ## action date in the past, 2 notifications sent; should bump to today + 1 day (and send third notification)
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": d_p1, "days":  7},
        t_n3: {"old": None, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": d_p1},
        t_n2: {"old": d_p1, "days":  7, "new": d_p1},
        t_n3: {"old": None, "days":  2, "new": d_today},
    }

    result = determine_action(
        idn_action_date= d_p1,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.PAST_BUMP_NOTIFICATION
    assert result["odn_action_date"] == d_1
    assert result["odn_notification"] == odn_notification
    assert result["message"] == notify_config[Result.PAST_BUMP_NOTIFICATION].replace("__N__", str(3))

def test_past_3_notifications_sent():
    ## action date in the past, 3 notifications; should action
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": d_p1, "days":  7},
        t_n3: {"old": d_p1, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": d_p1},
        t_n2: {"old": d_p1, "days":  7, "new": d_p1},
        t_n3: {"old": d_p1, "days":  2, "new": d_p1},
    }

    result = determine_action(
        idn_action_date= d_p1,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.COMPLETE_ACTION
    assert result["odn_action_date"] == d_today
    assert result["odn_notification"] == odn_notification

def test_future_notification_1():
    ## action date coming up, should send 1st notification
    idn_notification ={
        t_n1: {"old": None, "days": 15},
        t_n2: {"old": None, "days":  7},
        t_n3: {"old": None, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": None, "days": 15, "new": d_today},
        t_n2: {"old": None, "days":  7, "new": None},
        t_n3: {"old": None, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date= d_8,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.SEND_NOTIFICATION
    assert result["odn_action_date"] == d_8
    assert result["odn_notification"] == odn_notification
    assert result["message"] == notify_config[Result.SEND_NOTIFICATION].replace("__N__", str(1))

def test_future_notification_2():
    ## action date coming up, should send 2nd notification
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": None, "days":  7},
        t_n3: {"old": None, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": d_p1},
        t_n2: {"old": None, "days":  7, "new": d_today},
        t_n3: {"old": None, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date= d_5,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.SEND_NOTIFICATION
    assert result["odn_action_date"] == d_5
    assert result["odn_notification"] == odn_notification
    assert result["message"] == notify_config[Result.SEND_NOTIFICATION].replace("__N__", str(2))

def test_future_notification_3():
    ## action date coming up, should send 3rd notification
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": d_p1, "days":  7},
        t_n3: {"old": None, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": d_p1},
        t_n2: {"old": d_p1, "days":  7, "new": d_p1},
        t_n3: {"old": None, "days":  2, "new": d_today},
    }

    result = determine_action(
        idn_action_date= d_1,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.SEND_NOTIFICATION
    assert result["odn_action_date"] == d_1
    assert result["odn_notification"] == odn_notification
    assert result["message"] == notify_config[Result.SEND_NOTIFICATION].replace("__N__", str(3))

def test_future_1_notifications_sent():
    ## action date coming up, notification already sent
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": None, "days":  7},
        t_n3: {"old": None, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": d_p1},
        t_n2: {"old": None, "days":  7, "new": None},
        t_n3: {"old": None, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date= d_8,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.LOG_NO_NOTIFICATION
    assert result["odn_action_date"] == d_8
    assert result["odn_notification"] == odn_notification

def test_future_2_notifications_sent():
    ## action date coming up, notification already sent
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": d_p1, "days":  7},
        t_n3: {"old": None, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": d_p1},
        t_n2: {"old": d_p1, "days":  7, "new": d_p1},
        t_n3: {"old": None, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date= d_5,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.LOG_NO_NOTIFICATION
    assert result["odn_action_date"] == d_5
    assert result["odn_notification"] == odn_notification

def test_future_3_notifications_sent():
    ## action date coming up, notification already sent
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": d_p1, "days":  7},
        t_n3: {"old": d_p1, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": d_p1},
        t_n2: {"old": d_p1, "days":  7, "new": d_p1},
        t_n3: {"old": d_p1, "days":  2, "new": d_p1},
    }

    result = determine_action(
        idn_action_date= d_1,
        idn_notification=idn_notification,
        **i_default,
    )

    assert result["result"] == Result.LOG_NO_NOTIFICATION
    assert result["odn_action_date"] == d_1
    assert result["odn_notification"] == odn_notification

def test_reset_notifications():
    # user has been sent at least one notification but action date is > first notification date
    # indicates user manually pushed out dates
    # should reset notifications
    idn_notification ={
        t_n1: {"old": d_p1, "days": 15},
        t_n2: {"old": d_p1, "days":  7},
        t_n3: {"old": d_p1, "days":  2},
    }

    odn_notification = {
        t_n1: {"old": d_p1, "days": 15, "new": None},
        t_n2: {"old": d_p1, "days":  7, "new": None},
        t_n3: {"old": d_p1, "days":  2, "new": None},
    }

    result = determine_action(
        idn_action_date=d_31,
        idn_notification=idn_notification,
        **i_default,
    )
    assert result["result"] == Result.RESET_NOTIFICATIONS
    assert result["odn_action_date"] == d_31
    assert result["odn_notification"] == odn_notification