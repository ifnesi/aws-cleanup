# Test 'running' scenarios:
# stop_missing_stop_date: Missing stop date, should add one
# stop_malformed_stop_date: Malformed stop date, should add one

# stop_future_stop_date_too_far: Future stop date too far in the future, should pull it in
# stop_future_stop_date: Future stop date, should do nothing

# stop_past_0_notifications_sent: Stop date in the past, no notifications; should bump 3 days
# stop_past_1_notifications_sent: Stop date in the past, 1 notifications; should bump 2 days
# stop_past_2_notifications_sent: Stop date in the past, 2 notifications; should bump 1 days
# stop_past_3_notifications_sent: Stop date in the past, 3 notifications; should stop

# stop_future_notification_1: Stop date coming up, should send 1st notification
# stop_future_notification_2: Stop date coming up, should send 2nd notification
# stop_future_notification_3: Stop date coming up, should send 3rd notification

# stop_future_1_notifications_sent: Stop date coming up, notification already sent
# stop_future_2_notifications_sent: Stop date coming up, notification already sent
# stop_future_3_notifications_sent: Stop date coming up, notification already sent

############################################################

resource "aws_instance" "stop_missing_stop_date" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    "Name" = "stop_missing_stop_date"
    },
  )
}
resource "aws_ec2_instance_state" "stop_missing_stop_date" {
  instance_id = aws_instance.stop_missing_stop_date.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_malformed_stop_date" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = "xxx"
    "Name" = "stop_malformed_stop_date"
    },
  )
}
resource "aws_ec2_instance_state" "stop_malformed_stop_date" {
  instance_id = aws_instance.stop_malformed_stop_date.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_future_stop_date_too_far" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_80
    "Name" = "stop_future_stop_date_too_far"
    },
  )
}
resource "aws_ec2_instance_state" "stop_future_stop_date_too_far" {
  instance_id = aws_instance.stop_future_stop_date_too_far.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_future_stop_date" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_20
    "Name" = "stop_future_stop_date"
    },
  )
}
resource "aws_ec2_instance_state" "stop_future_stop_date" {
  instance_id = aws_instance.stop_future_stop_date.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_past_0_notifications_sent" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_p1
    "Name" = "stop_past_0_notifications_sent"
    },
  )
}
resource "aws_ec2_instance_state" "stop_past_0_notifications_sent" {
  instance_id = aws_instance.stop_past_0_notifications_sent.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_past_1_notifications_sent" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_p1
    (local.t_notification_1) = local.d_p1
    "Name" = "stop_past_1_notifications_sent"
    },
  )
}
resource "aws_ec2_instance_state" "stop_past_1_notifications_sent" {
  instance_id = aws_instance.stop_past_1_notifications_sent.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_past_2_notifications_sent" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_p1
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    "Name" = "stop_past_2_notifications_sent"
    },
  )
}
resource "aws_ec2_instance_state" "stop_past_2_notifications_sent" {
  instance_id = aws_instance.stop_past_2_notifications_sent.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_past_3_notifications_sent" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_p1
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    (local.t_notification_3) = local.d_p1
    "Name" = "stop_past_3_notifications_sent"
    },
  )
}
resource "aws_ec2_instance_state" "stop_past_3_notifications_sent" {
  instance_id = aws_instance.stop_past_3_notifications_sent.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_future_notification_1" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_8
    "Name" = "stop_future_notification_1"
    },
  )
}
resource "aws_ec2_instance_state" "stop_future_notification_1" {
  instance_id = aws_instance.stop_future_notification_1.id
  state = "running"
}



############################################################

resource "aws_instance" "stop_future_notification_2" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_3
    "Name" = "stop_future_notification_2"
    },
  )
}
resource "aws_ec2_instance_state" "stop_future_notification_2" {
  instance_id = aws_instance.stop_future_notification_2.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_future_notification_3" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_1
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    "Name" = "stop_future_notification_3"
    },
  )
}
resource "aws_ec2_instance_state" "stop_future_notification_3" {
  instance_id = aws_instance.stop_future_notification_3.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_future_1_notifications_sent" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_8
    (local.t_notification_1) = local.d_p1
    "Name" = "stop_future_1_notifications_sent"
    },
  )
}
resource "aws_ec2_instance_state" "stop_future_1_notifications_sent" {
  instance_id = aws_instance.stop_future_1_notifications_sent.id
  state = "running"
}

############################################################

resource "aws_instance" "stop_future_2_notifications_sent" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_3
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    "Name" = "stop_future_2_notifications_sent"
    },
  )
}
resource "aws_ec2_instance_state" "stop_future_2_notifications_sent" {
  instance_id = aws_instance.stop_future_2_notifications_sent.id
  state = "running"
}



############################################################

resource "aws_instance" "stop_future_3_notifications_sent" {
  ami   = var.x_ami
  instance_type = "t3.nano"
  key_name                    = var.key_name
  subnet_id                   = local.subnet_id

  root_block_device { volume_size = 10 }
  tags = merge({
    "justin" = "test"
    "owner_email" = "jlee@confluent.io"
    (local.t_stop_date) = local.d_1
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    (local.t_notification_3) = local.d_p1
    "Name" = "stop_future_3_notifications_sent"
    },
  )
}
resource "aws_ec2_instance_state" "stop_future_3_notifications_sent" {
  instance_id = aws_instance.stop_future_3_notifications_sent.id
  state = "running"
}


