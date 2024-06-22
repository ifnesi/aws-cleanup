#!/usr/bin/env python
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

from utils.slack_client import SlackClient
from utils.aws_client import AWSClient


def test_aws_connection(config):
    aws_client = AWSClient("us-east-1")
    assert aws_client.client._exceptions == None


def test_slack_connection(config):
    # Load config file (YAML)
    with open(config, "r") as f:
        config_data = yaml.safe_load(f)

    slack_config = config_data.get("slack", dict())
    slack_client = SlackClient(slack_config)
    response = slack_client.send_text("PyTest at {}".format(datetime.datetime.now()))
    response_json = response.json()
    assert response_json.get("ok") == True
