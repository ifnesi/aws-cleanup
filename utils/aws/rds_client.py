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
from .aws_client import AWSClient
from .generic_instance import GenericInstance

class RDSClient(AWSClient):
    def get_instances(
            self, 
            instance_config
    ):
        instances = list()
        params = {
            "MaxRecords": self._max_results,
        }
        tags_config = instance_config.get("tags")
        exceptions_config = instance_config.get("exceptions") or list()
        filters = instance_config.get("filters") or list()
        while True:
            describe_db_instances = self.client.describe_db_instances(**params)
            for instance in describe_db_instances.get("DBInstances", list()):
                # for instance in reservation.get("Instances", list()):
                if "TagList" not in instance:
                    tags = dict()
                else:
                    tags = {tag["Key"]: tag["Value"] for tag in instance["TagList"]}

                # Get tags matching any of the exception tags; if any exist, don't process.
                # returns a list of tuples; each tuple is ('tag', 'value')
                # using a list becuase it's ordered
                exceptions = [(e_tag, tags.get(e_tag)) for e_tag in exceptions_config if tags.get(e_tag)]
                emails = [tags.get(tag) for tag in self._email_tags]

                if instance.get("DBClusterIdentifier") is None:
                    if instance["DBInstanceStatus"] == "stopped" or (
                        instance["DBInstanceStatus"] == "available" and tags.get(tags_config.get("t_standalone_stopped"))
                    ):
                        state = "standalone:stopped"
                    elif instance["DBInstanceStatus"] == "available":
                        state = "standalone:available"
                    else:
                        state = "standalone:{}".format(instance["DBInstanceStatus"])
                else:
                    state = "clustered"

                instance = GenericInstance(
                    type="rds",
                    id=instance["DBInstanceArn"],
                    region=self._region_name,
                    name=instance["DBInstanceIdentifier"],
                    email=next((email for email in emails if email), None), # List coalesce to None
                    state=state,
                    exceptions=exceptions,
                    tags=tags,
                )
                if len(filters) > 0:
                    add = False
                    for filter in filters:
                        if tags.get(filter.get("Name").removeprefix("tag:")) in filter.get("Values"):
                            add = True
                else:
                    add = True
                if add:
                    instances.append(instance)

            # Pagination
            next_token = describe_db_instances.get("NextToken")
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
            self.client.add_tags_to_resource(
                ResourceName=id,
                Tags=formatted_tags,
            )

    def do_action(
        self,
        action: str,
        # type: str,
        id: str,
        name: str,
        **kwargs, # Ignore extra args
    ):
        if action == "stop":
            self.stop(
                id=id,
                name=name,
            )
        elif action == "delete":
            self.delete(
                id=id,
                name=name,
            )

    def stop(
        self,
        id: str,
        name: str,
        **kwargs,
    ):
        logging.info(
            "{}Stopping rds instance {} [{}] in region {}".format(
                self._dry_run_label,
                name,
                id,
                self._region_name,
            )
        )
        if not self._dry_run:
            self.client.stop_db_instance(
                DBInstanceIdentifier=name,
                DBSnapshotIdentifier="{}-stop-{}".format(name,datetime.date.today()),
            )

    def delete(
        self,
        id: str,
        name: str,
    ):
        logging.info(
            "{}Deleting rds instance {} [{}] in region {}".format(
                self._dry_run_label,
                name,
                id,
                self._region_name,
            )
        )
        print("{}-delete-snapshot-{}".format(
                    name,
                    datetime.date.today(),
                )[:63])
        if not self._dry_run:
            try:
                self.client.delete_db_instance(
                    DBInstanceIdentifier=name,
                    SkipFinalSnapshot=False,
                    FinalDBSnapshotIdentifier="{}-delete-{}".format(
                        name,
                        datetime.date.today(),
                    )[:63],
                    DeleteAutomatedBackups=False,
                )
            except:
                logging.info(
                    "Exception terminating rds instance {} [{}] in region {}".format(
                        name,
                        id,
                        self._region_name,
                    )
                )