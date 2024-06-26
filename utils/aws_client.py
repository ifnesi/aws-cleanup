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


class AWSClient:
    def __init__(
        self,
        region_name: str,
        dry_run: bool = True,
        max_results: int = 100,
        service_name: str = "ec2",
        search_filter: list = None,
        notify_messages_config: dict = None,
    ) -> None:
        self._service_name = service_name
        self._region_name = region_name
        self._search_filter = search_filter
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

    def get_instances(self):
        instances = list()
        params = {
            "MaxResults": self._max_results,
            "Filters": self._search_filter,
        }
        while True:
            describe_instances = self.client.describe_instances(**params)
            for reservation in describe_instances.get("Reservations", list()):
                instances += reservation.get("Instances", list())

            # Pagination
            next_token = describe_instances.get("NextToken")
            if next_token:
                params["NextToken"] = next_token
            else:
                break

        logging.info(
            "Total {} instances found: {}".format(
                self._service_name,
                len(instances),
            )
        )
        return instances

    def update_tag(
        self,
        instance_id,
        instance_name,
        tag,
        new_value,
        old_value,
    ):
        # TODO: In the future, could batch this up, for now doing it one at a time
        logging.info(
            "{}Updating of tag on {} [{}] in region {}: setting {} from {} to {}".format(
                self._dry_run_label,
                instance_name,
                instance_id,
                self._region_name,
                tag,
                old_value,
                new_value,
            )
        )
        if not self._dry_run:
            # This is super sloppy; right now we're relying on the fact that this is called after ec2_client has created for the relevant region
            # Later could either pass it in, or create an array of clients for regions
            # str(value) takes care of converting datetime.date to string in isoformat '2024-01-01'
            self.client.create_tags(
                Resources=[instance_id],
                Tags=[
                    {
                        "Key": tag,
                        "Value": str(new_value),
                    }
                ],
            )

    def do_action(
        self,
        action: str,
        instance_type: str,
        instance_id: str,
        instance_name: str,
    ):
        if action == "stop":
            self.stop(
                instance_id=instance_id,
                instance_name=instance_name,
            )
        elif action == "terminate":
            self.terminate(
                instance_id=instance_id,
                instance_name=instance_name,
            )

    def stop(
        self,
        instance_id: str,
        instance_name: str,
    ):
        logging.info(
            "{}Stopping instance {} [{}] in region {}".format(
                self._dry_run_label,
                instance_name,
                instance_id,
                self._region_name,
            )
        )
        if not self._dry_run:
            self.client.stop_instances(InstanceIds=[instance_id])

    def terminate(
        self,
        instance_id: str,
        instance_name: str,
    ):
        logging.info(
            "{}Terminating instance {} [{}] in region {}".format(
                self._dry_run_label,
                instance_name,
                instance_id,
                self._region_name,
            )
        )
        if not self._dry_run:
            self.client.terminate_instances(InstanceIds=[instance_id])
