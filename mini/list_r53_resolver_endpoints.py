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
# BY DEFAULT, WILL ONLY RUN AGAINST TEST INSTANCES
# MUST USE --full FLAG TO RUN AGAINST WHOLE ACCOUNT

# On fresh Ubuntu instance, install prereqs:
# sudo apt-get update; sudo apt-get install -y python3-pip;
# python3 -m pip install -r requirements.txt
#
import os
import sys
import json
import yaml
import logging
import argparse
import datetime
import boto3
import time

if __name__ == "__main__":
    region_client = boto3.client(
        service_name = "ec2"
    )

    regions = [region.get("RegionName") for region in region_client.describe_regions().get("Regions")]

    for region in regions:
        ec2client = boto3.client(
            service_name = "ec2",
            region_name = region
        )

        r53client = boto3.client(
            service_name = "route53resolver",
            region_name = region
        )

        endpoints = r53client.list_resolver_endpoints(
            MaxResults = 100,
        ).get("ResolverEndpoints")

        for endpoint in endpoints:
            vpc_id = endpoint.get('HostVPCId')
            vpc_info = ec2client.describe_vpcs(
                Filters = [
                    {
                        'Name': 'vpc-id',
                        'Values': [vpc_id]
                    }
                ]
            ).get('Vpcs')[0]

            tags = dict([(t.get('Key'),t.get('Value')) for t in vpc_info.get('Tags')])

            print("{};{};{};{};{};{};{}".format(
                region,
                endpoint.get('Name'),
                endpoint.get('Id'),
                endpoint.get('Direction'),
                endpoint.get('CreationTime'),
                vpc_info.get('VpcId'),
                str(tags)
            ))

# To delete:
# aws route53resolver delete-resolver-endpoint --region x --resolver-endpoint-id y
