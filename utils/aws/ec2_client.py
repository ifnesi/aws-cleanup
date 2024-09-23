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
from .aws_client import AWSClient
from .generic_instance import GenericInstance

class EC2Client(AWSClient):
    def get_instances(
            self, 
            instance_config
    ):
        instances = list()
        params = {
            "MaxResults": self._max_results,
            "Filters": instance_config.get("filters") or list(),
        }
        exceptions_config = instance_config.get("exceptions") or list()
        while True:
            describe_instances = self.client.describe_instances(**params)
            for reservation in describe_instances.get("Reservations", list()):
                for instance in reservation.get("Instances", list()):
                    if "Tags" not in instance:
                        tags = dict()
                    else:
                        tags = {tag["Key"]: tag["Value"] for tag in instance["Tags"]}

                    # Get tags matching any of the exception tags; if any exist, don't process.
                    # returns a list of tuples; each tuple is ('tag', 'value')
                    # using a list becuase it's ordered
                    exceptions = [(e_tag, tags.get(e_tag)) for e_tag in exceptions_config if tags.get(e_tag)]
                    emails = [tags.get(tag) for tag in self._email_tags]

                    instance = GenericInstance(
                        type="ec2",
                        id=instance["InstanceId"],
                        region=self._region_name,
                        name=tags.get("Name"),
                        email=next((email for email in emails if email), None), # List coalesce to None
                        state=instance["State"]["Name"],
                        exceptions=exceptions,
                        tags=tags,
                    )

                    instances.append(instance)

            # Pagination
            next_token = describe_instances.get("NextToken")
            if next_token:
                params["NextToken"] = next_token
            else:
                break

        return instances
    
    def update_tags(
            self,
            id,
            name,
            updated_tags,
            **kwargs
    ):
        for tag, values in updated_tags.items():
            logging.info(
                "{}Updating tag on {} [{}] in region {}: changing {} from {} to {}".format(
                    self._dry_run_label,
                    name,
                    id,
                    self._region_name,
                    tag,
                    values["old"],
                    values["new"],
                )
            )
        formatted_tags = [{"Key": tag, "Value": str(values["new"])} for tag, values in updated_tags.items()]
        if not self._dry_run:
            # This is super sloppy; right now we're relying on the fact that this is called after ec2_client has created for the relevant region
            # Later could either pass it in, or create an array of clients for regions
            # str(value) takes care of converting datetime.date to string in isoformat '2024-01-01'
            self.client.create_tags(
                Resources=[id],
                Tags=formatted_tags,
            )

    def do_action(
        self,
        action: str,
        type: str,
        id: str,
        name: str,
        **kwargs, # Ignore extra args
    ):
        if action == "stop":
            self.stop(
                id=id,
                name=name,
            )
        elif action == "terminate":
            self.terminate(
                id=id,
                name=id,
            )
    
    def stop(
        self,
        id: str,
        name: str,
    ):
        logging.info(
            "{}Stopping ec2 instance {} [{}] in region {}".format(
                self._dry_run_label,
                name,
                id,
                self._region_name,
            )
        )
        if not self._dry_run:
            self.client.stop_instances(InstanceIds=[id])
    
    def terminate(
        self,
        id: str,
        name: str,
    ):
        logging.info(
            "{}Terminating ec2 instance {} [{}] in region {}".format(
                self._dry_run_label,
                name,
                id,
                self._region_name,
            )
        )
        if not self._dry_run:
            try:
                self.client.terminate_instances(InstanceIds=[id])
            except:
                logging.info(
                    "Exception terminating ec2 instance {} [{}] in region {}".format(
                        name,
                        id,
                        self._region_name,
                    )
                )