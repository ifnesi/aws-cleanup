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

    parser = argparse.ArgumentParser(description="EKS Deleter")
    parser.add_argument(
        "--region",
        help="Specify region to use",
        default = "us-east-2",
        dest="region",
    )

    parser.add_argument(
        "--name",
        help="Specify EKS cluster to delete",
        dest="name",
    )

    args = parser.parse_args()

    eks = boto3.client(
        service_name = "eks",
        region_name = args.region
    )

    # print(eks.list_clusters())

    cluster = eks.describe_cluster(
        name = args.name
    ).get("cluster")

    vpcId = cluster.get("resourcesVpcConfig").get("vpcId")
    
    print(vpcId)

    profiles = eks.list_fargate_profiles(
        clusterName = args.name
    ).get("fargateProfileNames", list())

    print(profiles)

    if len(profiles) > 0:
        for profile in profiles:
            print("Deleting profile {}".format(profile))
            eks.delete_fargate_profile(
                clusterName = args.name,
                fargateProfileName= profile,
            )
            while profile in eks.list_fargate_profiles(
                clusterName = args.name,
            ).get("fargateProfileNames"):
                print("Waiting for fargateProfileName deletion: {}".format(profile))
                time.sleep(30)


    nodegroups = eks.list_nodegroups(
        clusterName = args.name
    ).get("nodegroups", list())

    print(nodegroups)

    if len(nodegroups) > 0:
        for nodeGroup in nodegroups:
            print("Deleting nodeGroup {}".format(nodeGroup))
            eks.delete_nodegroup(
                clusterName=args.name,
                nodegroupName=nodeGroup,
            )

    # while eks.list_fargate_profiles(clusterName = args.name).get("fargateProfileNames"):
    #     print("Waiting for fargateProfileName deletion")
    #     print(eks.list_fargate_profiles(clusterName = args.name).get("fargateProfileNames"))
    #     time.sleep(30)

    while eks.list_nodegroups(clusterName = args.name).get("nodegroups"):
        print("Waiting for nodegroup deletion")
        print(eks.list_nodegroups(clusterName = args.name).get("nodegroups"))
        time.sleep(30)

    eks.delete_cluster(
        name = args.name
    )