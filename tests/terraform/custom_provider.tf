locals {
  tf_tags = {
    "tf_owner"         = "Justin Lee",
    "tf_owner_email"   = "jlee@confluent.io",
    "tf_provenance"    = "github.com/justinrlee/private-terraform/aws/${var.region_short}",
    "tf_last_modified" = "${var.date_updated}",
    "Owner"            = "Justin Lee",
    # "owner_email"      = "jlee@confluent.io",
    # "expiration"       = "${var.expiration}"
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