locals {
  tf_tags = {
    "tf_provenance"    = "github.com/ifnesi/aws-cleanup/tests/terraform",
    "tf_last_modified" = "${var.date_updated}",
  }
}

provider "aws" {
  region = var.region

  ignore_tags {
    key_prefixes = [
      "divvy",
      "confluent-infosec"
    ]
  }

  default_tags {
    tags = local.tf_tags
  }
}