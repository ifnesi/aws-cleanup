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

import boto3
import logging
# import datetime
# from utils.generic_instance import GenericInstance

class AWSClient:
    def __init__(
        self,
        region_name: str,
        dry_run: bool = True,
        max_results: int = 100,
        service_name: str = "ec2",
        email_tags: list = None,
        notify_messages_config: dict = None,
    ) -> None:
        self._service_name = service_name
        self._region_name = region_name
        self._email_tags = email_tags
        self._max_results = max_results
        self._notify_messages_config = notify_messages_config
        self._dry_run = dry_run
        self._dry_run_label = "[DRY RUN] " if dry_run else ""

        self.client = boto3.client(
            service_name,
            region_name=region_name,
        )

    def get_regions(self):
        logging.info("Getting regions")
        return [
            region["RegionName"] for region in self.client.describe_regions()["Regions"]
        ]
    
    def get_instances(self, instance_config):
        return []
    
    def update_tags(self, id, name, updated_tags, **kwargs):
        pass

    def do_action(
        self,
        action: str,
        type: str,
        id: str,
        name: str,
        **kwargs, # Ignore extra args
    ):
        pass