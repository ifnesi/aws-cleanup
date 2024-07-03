variable "date_updated" {}
variable "region" {}
variable "owner_email" {}
variable "subnet_id" {}

# Useful for adding tags to instances (e.g. for test filter)
variable "additional_tags" {
  default = {
    "aws_cleaner/filter" = "justin"
  }
}