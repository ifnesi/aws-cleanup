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
import datetime
from utils.generic_instance import GenericInstance

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
        # self._search_filter = search_filter
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
        if self._service_name == "ec2":
            return self.get_ec2_instances(instance_config=instance_config)
        elif self._service_name == "rds":
            return self.get_rds_instances(instance_config=instance_config)

    def get_ec2_instances(self, instance_config):
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

        logging.info(
            "Total {} instances found: {}".format(
                self._service_name,
                len(instances),
            )
        )
        return instances
    
    def get_rds_instances(self, instance_config):
        instances = list()
        params = {
            "MaxRecords": self._max_results,
        }
        tags_config = instance_config.get("tags")
        exceptions_config = instance_config.get("exceptions") or list()
        filters = instance_config.get("filters")
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

        logging.info(
            "Total {} instances found: {}".format(
                self._service_name,
                len(instances),
            )
        )
        return instances

    # def get_autoscaling_groups(self, tags_config):
    #     instances = list()
    #     params = {
    #         "MaxResults": self._max_results,
    #         "Filters": self._search_filter,
    #     }
    #     while True:
    #         describe_groups = self.client.describe_auto_scaling_groups(**params)
    #         for asg in describe_groups.get("AutoScalingGroups", list()):
    #             if "Tags" not in asg:
    #                 tags = dict()
    #             else:
    #                 tags = {tag["Key"]: tag["Value"] for tag in instance["Tags"]}

    #             # Get tags matching any of the exception tags; if any exist, don't process.
    #             # returns a list of tuples; each tuple is ('tag', 'value')
    #             # using a list becuase it's ordered
    #             exceptions = [(e_tag, tags.get(e_tag)) for e_tag in ["aws_cleaner/cleanup_exception", "aws:autoscaling:groupName"] if tags.get(e_tag)]

    #             instance = GenericInstance(
    #                 type="ec2",
    #                 id=instance["InstanceId"],
    #                 region=self._region_name,
    #                 name=tags.get(tags_config.get("t_name")),
    #                 email=tags.get(tags_config.get("t_owner_email"))
    #                     or tags.get(tags_config.get("t_email"))
    #                     or tags.get(tags_config.get("t_divvy_owner"))
    #                     or tags.get(tags_config.get("t_divvy_last_modified_by")),
    #                 state=instance["State"]["Name"],
    #                 exceptions=exceptions,
    #                 tags=tags,
    #             )

    #             instances.append(instance)

    #         # Pagination
    #         next_token = describe_instances.get("NextToken")
    #         if next_token:
    #             params["NextToken"] = next_token
    #         else:
    #             break

    #     logging.info(
    #         "Total {} instances found: {}".format(
    #             self._service_name,
    #             len(instances),
    #         )
    #     )
    #     return instances

    # tags_changed is a list of tuples, each of which is (tag, old_value, new_value)
    def update_tags(
        self,
        id,
        name,
        updated_tags,
        **kwargs, # Ignore extra args
    ):
        if self._service_name == "ec2":
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
        elif self._service_name == "rds":
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
        type: str,
        id: str,
        name: str,
        **kwargs, # Ignore extra args
    ):
        if type == "ec2":
            if action == "stop":
                self.ec2_stop(
                    id=id,
                    name=name,
                )
            elif action == "terminate":
                self.ec2_terminate(
                    id=id,
                    name=id,
                )
        elif type == "rds":
            if action == "stop":
                self.rds_stop(
                    id=id,
                    name=name,
                )
            if action == "delete":
                self.rds_delete(
                    id=id,
                    name=name,
                )

    def ec2_stop(
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

    def ec2_terminate(
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
            self.client.terminate_instances(InstanceIds=[id])

    def rds_stop(
        self,
        id: str,
        name: str,
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
                DBSnapshotIdentifier="{}-stop-snapshot-{}".format(name,datetime.date.today()),
            )

    def rds_delete(
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
        if not self._dry_run:
            self.client.delete_db_instance(
                DBInstanceIdentifier=name,
                SkipFinalSnapshot=False,
                FinalDBSnapshotIdentifier="{}-delete-snapshot-{}".format(
                    name,
                    datetime.datetime.now().isoformat(timespec='seconds').replace(":","")
                ),
                DeleteAutomatedBackups=False,
            )