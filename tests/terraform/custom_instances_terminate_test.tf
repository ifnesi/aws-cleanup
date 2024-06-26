# Test 'stopped' scenarios:
# terminate_missing_terminate_date: Missing terminate date, should add one
# terminate_malformed_terminate_date: Malformed terminate date, should add one

# terminate_future_terminate_date_too_far: Future terminate date too far in the future, should pull it in
# terminate_future_terminate_date: Future terminate date, should do nothing

# terminate_past_0_notifications_sent: terminate date in the past, no notifications; should bump 3 days
# terminate_past_1_notifications_sent: terminate date in the past, 1 notifications; should bump 2 days
# terminate_past_2_notifications_sent: terminate date in the past, 2 notifications; should bump 1 days
# terminate_past_3_notifications_sent: terminate date in the past, 3 notifications; should terminate

# terminate_future_notification_1: terminate date coming up, should send 1st notification
# terminate_future_notification_2: terminate date coming up, should send 2nd notification
# terminate_future_notification_3: terminate date coming up, should send 3rd notification

# terminate_future_1_notifications_sent: terminate date coming up, notification already sent
# terminate_future_2_notifications_sent: terminate date coming up, notification already sent
# terminate_future_3_notifications_sent: terminate date coming up, notification already sent

############################################################

resource "aws_instance" "terminate_missing_terminate_date" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email" = (var.owner_email)
    "Name"        = "terminate_missing_terminate_date"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_missing_terminate_date" {
  instance_id = aws_instance.terminate_missing_terminate_date.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_malformed_terminate_date" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"       = (var.owner_email)
    (local.t_terminate_date) = "xxx"
    "Name"              = "terminate_malformed_terminate_date"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_malformed_terminate_date" {
  instance_id = aws_instance.terminate_malformed_terminate_date.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_future_terminate_date_too_far" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"       = (var.owner_email)
    (local.t_terminate_date) = local.d_80
    "Name"              = "terminate_future_terminate_date_too_far"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_future_terminate_date_too_far" {
  instance_id = aws_instance.terminate_future_terminate_date_too_far.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_future_terminate_date" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"       = (var.owner_email)
    (local.t_terminate_date) = local.d_20
    "Name"              = "terminate_future_terminate_date"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_future_terminate_date" {
  instance_id = aws_instance.terminate_future_terminate_date.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_past_0_notifications_sent" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"       = (var.owner_email)
    (local.t_terminate_date) = local.d_p1
    "Name"              = "terminate_past_0_notifications_sent"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_past_0_notifications_sent" {
  instance_id = aws_instance.terminate_past_0_notifications_sent.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_past_1_notifications_sent" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"            = (var.owner_email)
    (local.t_terminate_date)      = local.d_p1
    (local.t_notification_1) = local.d_p1
    "Name"                   = "terminate_past_1_notifications_sent"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_past_1_notifications_sent" {
  instance_id = aws_instance.terminate_past_1_notifications_sent.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_past_2_notifications_sent" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"            = (var.owner_email)
    (local.t_terminate_date)      = local.d_p1
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    "Name"                   = "terminate_past_2_notifications_sent"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_past_2_notifications_sent" {
  instance_id = aws_instance.terminate_past_2_notifications_sent.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_past_3_notifications_sent" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"            = (var.owner_email)
    (local.t_terminate_date)      = local.d_p1
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    (local.t_notification_3) = local.d_p1
    "Name"                   = "terminate_past_3_notifications_sent"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_past_3_notifications_sent" {
  instance_id = aws_instance.terminate_past_3_notifications_sent.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_future_notification_1" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"       = (var.owner_email)
    (local.t_terminate_date) = local.d_8
    "Name"              = "terminate_future_notification_1"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_future_notification_1" {
  instance_id = aws_instance.terminate_future_notification_1.id
  state       = "stopped"
}



############################################################

resource "aws_instance" "terminate_future_notification_2" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"       = (var.owner_email)
    (local.t_terminate_date) = local.d_3
    (local.t_notification_1) = local.d_p1
    "Name"              = "terminate_future_notification_2"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_future_notification_2" {
  instance_id = aws_instance.terminate_future_notification_2.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_future_notification_3" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"            = (var.owner_email)
    (local.t_terminate_date)      = local.d_1
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    "Name"                   = "terminate_future_notification_3"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_future_notification_3" {
  instance_id = aws_instance.terminate_future_notification_3.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_future_1_notifications_sent" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"            = (var.owner_email)
    (local.t_terminate_date)      = local.d_8
    (local.t_notification_1) = local.d_p1
    "Name"                   = "terminate_future_1_notifications_sent"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_future_1_notifications_sent" {
  instance_id = aws_instance.terminate_future_1_notifications_sent.id
  state       = "stopped"
}

############################################################

resource "aws_instance" "terminate_future_2_notifications_sent" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"            = (var.owner_email)
    (local.t_terminate_date)      = local.d_3
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    "Name"                   = "terminate_future_2_notifications_sent"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_future_2_notifications_sent" {
  instance_id = aws_instance.terminate_future_2_notifications_sent.id
  state       = "stopped"
}



############################################################

resource "aws_instance" "terminate_future_3_notifications_sent" {
  ami           = local.ami
  instance_type = "t4g.nano"
  subnet_id     = local.subnet_id

  tags = merge({
    "owner_email"            = (var.owner_email)
    (local.t_terminate_date)      = local.d_1
    (local.t_notification_1) = local.d_p1
    (local.t_notification_2) = local.d_p1
    (local.t_notification_3) = local.d_p1
    "Name"                   = "terminate_future_3_notifications_sent"
    },
    var.additional_tags,
  )
}
resource "aws_ec2_instance_state" "terminate_future_3_notifications_sent" {
  instance_id = aws_instance.terminate_future_3_notifications_sent.id
  state       = "stopped"
}


