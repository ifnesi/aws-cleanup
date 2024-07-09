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

class ASGClient(AWSClient):
    def get_instances(
            self, 
            instance_config
    ):
        instances = list()
        params = {
            "MaxRecords": self._max_results,
            "Filters": instance_config.get("filters") or list(),
        }

        prefixes = instance_config.get("prefixes")
        exceptions_config = instance_config.get("exceptions") or list()
        
        while True:
            describe_asgs = self.client.describe_auto_scaling_groups(**params)
            for instance in describe_asgs.get("AutoScalingGroups", list()):
                # for instance in reservation.get("Instances", list()):
                if "Tags" not in instance:
                    tags = dict()
                else:
                    tags = {tag["Key"]: tag["Value"] for tag in instance["Tags"]}

                # Get tags matching any of the exception tags; if any exist, don't process.
                # returns a list of tuples; each tuple is ('tag', 'value')
                # using a list becuase it's ordered
                exceptions = [(e_tag, tags.get(e_tag)) for e_tag in exceptions_config if tags.get(e_tag)]
                emails = [tags.get(tag) for tag in self._email_tags]

                is_eks_managed = False
                is_eks = False
                for prefix in prefixes.get("managed", list()):
                    for tag in tags:
                        if tag.startswith(prefix):
                            is_eks_managed = True
                for prefix in prefixes.get("eks", list()):
                    for tag in tags:
                        if tag.startswith(prefix):
                            is_eks = True

                if is_eks_managed:
                    state = "eks:managed"
                elif is_eks:
                    state = "eks:unmanaged"
                else:
                    if instance["DesiredCapacity"] == 0:
                        state = "standalone:scaledtozero"
                    else:
                        state = "standalone:running"

                instance = GenericInstance(
                    type="asg",
                    id=instance["AutoScalingGroupARN"],
                    region=self._region_name,
                    name=instance["AutoScalingGroupName"],
                    email=next((email for email in emails if email), None), # List coalesce to None
                    state=state,
                    exceptions=exceptions,
                    tags=tags,
                )
                
                instances.append(instance)

            # Pagination
            next_token = describe_asgs.get("NextToken")
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
    
    def stop(
        self,
        id: str,
        name: str,
    ):
        pass
    
    def terminate(
        self,
        id: str,
        name: str,
    ):
        pass