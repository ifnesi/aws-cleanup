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
import enum


class Result(str, enum.Enum):
    ADD_ACTION_DATE = "ADD_ACTION_DATE"
    RESET_ACTION_DATE = "RESET_ACTION_DATE"
    COMPLETE_ACTION = "COMPLETE_ACTION"
    TRANSITION_ACTION = "TRANSITION_ACTION"

    PAST_BUMP_NOTIFICATION = "PAST_BUMP_NOTIFICATION"
    SEND_NOTIFICATION = "SEND_NOTIFICATION"

    LOG_NO_NOTIFICATION = "LOG_NO_NOTIFICATION"

    IGNORE_OTHER_STATES = "IGNORE_OTHER_STATES"
    IGNORE_ASG = "IGNORE_ASG"
    SKIP_EXCEPTION = "SKIP_EXCEPTION"
