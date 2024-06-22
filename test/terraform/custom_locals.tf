
locals {
    d_today = formatdate("YYYY-MM-DD", timestamp())
    d_1 = formatdate("YYYY-MM-DD", timeadd(timestamp(), "24h"))
    d_3 = formatdate("YYYY-MM-DD", timeadd(timestamp(), "72h"))
    d_8 = formatdate("YYYY-MM-DD", timeadd(timestamp(), "192h"))
    d_20 = formatdate("YYYY-MM-DD", timeadd(timestamp(), "480h"))
    d_40 = formatdate("YYYY-MM-DD", timeadd(timestamp(), "960h"))
    d_80 = formatdate("YYYY-MM-DD", timeadd(timestamp(), "1920h"))

    d_p1 = formatdate("YYYY-MM-DD", timeadd(timestamp(), "-24h"))

    t_exception = "aws_cleaner/cleanup_exception"
    t_stop_date = "aws_cleaner/stop_date"
    t_terminate_date = "aws_cleaner/terminate_date"

    t_notification_1 = "aws_cleaner/notifications/1"
    t_notification_2 = "aws_cleaner/notifications/2"
    t_notification_3 = "aws_cleaner/notifications/3"

    subnet_id = module.main.subnets["az1"].id
}

# Diff between custom_instances_stop_test and custom_instances_terminate_test
# * Replace 'stop' with 'terminate'
# * Replace 'running' with 'stopped'