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
    parser = argparse.ArgumentParser(description="RDS Deleter")
    parser.add_argument(
        "--region",
        help="Specify region to use",
        default = "us-east-2",
        dest="region",
    )

    parser.add_argument(
        "--name",
        help="Specify RDS Instance to delete",
        dest="name",
    )

    args = parser.parse_args()

    rds = boto3.client(
        service_name = "rds",
        region_name = args.region
    )

    rds.delete_db_instance(
        DBInstanceIdentifier=args.name,
        SkipFinalSnapshot=False,
        FinalDBSnapshotIdentifier="{}-delete-{}".format(
            args.name,
            datetime.date.today(),
        )[:63],
        DeleteAutomatedBackups=False,
    )
