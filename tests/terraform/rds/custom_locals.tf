
locals {
  d_today = formatdate("YYYY-MM-DD", timestamp())
  d_1     = formatdate("YYYY-MM-DD", timeadd(timestamp(), "24h"))
  d_3     = formatdate("YYYY-MM-DD", timeadd(timestamp(), "72h"))
  d_8     = formatdate("YYYY-MM-DD", timeadd(timestamp(), "192h"))
  d_20    = formatdate("YYYY-MM-DD", timeadd(timestamp(), "480h"))
  d_40    = formatdate("YYYY-MM-DD", timeadd(timestamp(), "960h"))
  d_80    = formatdate("YYYY-MM-DD", timeadd(timestamp(), "1920h"))

  d_p1 = formatdate("YYYY-MM-DD", timeadd(timestamp(), "-24h"))

  t_exception      = "aws_cleaner/cleanup_exception"
  t_stop_date      = "aws_cleaner/stop/date"
  t_terminate_date = "aws_cleaner/terminate/"

  t_stop_notification_1 = "aws_cleaner/stop/notifications/1"
  t_stop_notification_2 = "aws_cleaner/stop/notifications/2"
  t_stop_notification_3 = "aws_cleaner/stop/notifications/3"

  t_terminate_notification_1 = "aws_cleaner/delete/notifications/1"
  t_terminate_notification_2 = "aws_cleaner/delete/notifications/2"
  t_terminate_notification_3 = "aws_cleaner/delete/notifications/3"

  subnet_id = var.subnet_id

  # Ubuntu 20.04 release 20240614; ARM64
  ami = {
    "af-south-1"     = "ami-03d6b7d0c44d4c41b",
    "ap-east-1"      = "ami-01ec539fe1b06c0d4",
    "ap-northeast-1" = "ami-0a82eb906eb03c150",
    "ap-northeast-2" = "ami-056e78036d2636d31",
    "ap-northeast-3" = "ami-0dd971d2e037e4dcc",
    "ap-south-1"     = "ami-063e11bd144f8dd92",
    "ap-south-2"     = "ami-0b51d30ad08a1910a",
    "ap-southeast-1" = "ami-08776696f7d1ee082",
    "ap-southeast-2" = "ami-0a6c7d524ec088f91",
    "ap-southeast-3" = "ami-0024233dd5f420997",
    "ap-southeast-4" = "ami-04f72386b777d7875",
    "ca-central-1"   = "ami-0da0f1325dc0c88e5",
    "ca-west-1"      = "ami-00889c3095e5f3998",
    "cn-north-1"     = "ami-0b9d17a9bfcb49575",
    "cn-northwest-1" = "ami-0de2ee8caafd9f6d8",
    "eu-central-1"   = "ami-0f4dbe65c0ab6b772",
    "eu-central-2"   = "ami-0ff5f2c2464dbfaf4",
    "eu-north-1"     = "ami-0a051161d0615e794",
    "eu-south-1"     = "ami-0c26b3b1839387870",
    "eu-south-2"     = "ami-0cb1b140b8c2c7160",
    "eu-west-1"      = "ami-08f2ca0755caafc54",
    "eu-west-2"      = "ami-089796d8243cddd47",
    "eu-west-3"      = "ami-0b43a03c18066f226",
    "il-central-1"   = "ami-07dd6e3411732a496",
    "me-central-1"   = "ami-089dbcab309fc2b2d",
    "me-south-1"     = "ami-04987c0b05e8f1bec",
    "sa-east-1"      = "ami-019dfd78a1e75db87",
    "us-east-1"      = "ami-0653f1a3c1d940601",
    "us-east-2"      = "ami-0c39118986d33d733",
    "us-west-1"      = "ami-0423967106731e8c0",
    "us-west-2"      = "ami-03ba6b736f8a053bd",
  }[var.region]

}

# Diff between custom_instances_stop_test and custom_instances_terminate_test
# * Replace 'stop' with 'terminate'
# * Replace 'running' with 'stopped'