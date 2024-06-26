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
import json
import boto3
import logging
import requests


class SlackClient:
    def __init__(
        self,
        slack_config: dict,
    ) -> None:
        self.token = None
        self.channel_id = None
        self.user_map = dict()
        self._slack_config = slack_config
        aws_secret_client = boto3.client(
            service_name="secretsmanager",
            region_name=slack_config.get("token_secret_region"),
        )
        try:
            get_secret_value_response = aws_secret_client.get_secret_value(
                SecretId=slack_config.get("token_secret_name"),
            )
            self.token = json.loads(get_secret_value_response.get("SecretString")).get(
                slack_config.get("token_secret_key")
            )
            self.channel_id = json.loads(
                get_secret_value_response.get("SecretString")
            ).get(slack_config.get("channel_key"))
            self.headers = {
                "Authorization": "Bearer {}".format(self.token)
            }
        except:
            logging.error(
                "Unable to retrieve Slack token from AWS Secret Manager object {}, key {}, region {}".format(
                    slack_config.get("token_secret_name"),
                    slack_config.get("token_secret_key"),
                    slack_config.get("token_secret_region"),
                )
            )
        else:
            logging.debug(
                "Using Slack token {}, and generic notification chanenl {}".format(
                    self.token,
                    self.channel_id,
                )
            )

    def send_text(
        self,
        text: str,
    ):
        response = requests.post(
            url=self._slack_config.get("chat_post_message_endpoint"),
            headers=self.headers,
            json={
                "channel": self.channel_id,
                "text": text,
            },
        )
        logging.debug("[SLACK POST RESPONSE] {}".format(response.text))
        return response

    def send_dm(
            self,
            text: str,
            email: str
    ):
        if email not in self.user_map:
            d = {"email": email}
            r = requests.post(
                url=self._slack_config.get("user_lookup_endpoint"),
                headers=self.headers,
                data=d
            )
            logging.debug("[SLACK EMAIL LOOKUP RESPONSE] {}".format(r.text))
            # Will result in 'None'
            try:
                self.user_map[email] = r.json()["user"]["id"]
            except:
                self.user_map[email] = None
        if self.user_map[email]:
            response = requests.post(
                url=self._slack_config.get("chat_post_message_endpoint"),
                headers=self.headers,
                json={
                    "channel": self.user_map[email],
                    "text": text,
                },
            )
            return response
        else:
            # For now, instances where we can't find the user will be dumped to the main channel
            response = requests.post(
                url=self._slack_config.get("chat_post_message_endpoint"),
                headers=self.headers,
                json={
                    "channel": self.channel_id,
                    "text": "USER NOT FOUND: {}: Not notified for {}".format(email, text),
                },
            )