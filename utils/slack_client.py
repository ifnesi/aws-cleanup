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
        self._url_dm = slack_config.get("user_lookup_endpoint")
        self._url_text = slack_config.get("chat_post_message_endpoint")
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
            self.headers = {"Authorization": "Bearer {}".format(self.token)}
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
        channel_id: str = None,  # will default to self.channel_id if None
    ):
        response = requests.post(
            url=self._url_text,
            headers=self.headers,
            json={
                "channel": self.channel_id if channel_id is None else channel_id,
                "text": text,
            },
        )
        logging.debug("[SLACK POST RESPONSE] {}".format(response.text))
        return response

    def send_dm(
        self,
        text: str,
        email: str,
    ):
        user_id = self.user_map.get(email)
        if not user_id:
            r = requests.post(
                url=self._url_dm,
                headers=self.headers,
                # User lookup doesn't support json, has to be data
                data={
                    "email": email,
                },
            )
            logging.debug("[SLACK EMAIL LOOKUP RESPONSE] {}".format(r.text))
            user_id = r.json().get("user", dict()).get("id")
            if user_id:
                self.user_map[email] = user_id

        if user_id:
            return self.send_text(
                "{} [Details: <#{}>]".format(text, self.channel_id),
                channel_id=user_id,
            )

        else:
            # For now, instances where we can't find the user will be dumped to the main channel
            return self.send_text(
                "USER NOT FOUND ({}): Not notified for {}".format(
                    email,
                    text,
                )
            )
