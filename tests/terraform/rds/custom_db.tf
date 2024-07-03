resource "aws_db_instance" "r1" {
  allocated_storage    = 5
  db_name              = "mydb"
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t3.micro"
  username             = "foo"
  password             = "foobarbaz"
  parameter_group_name = "default.mysql8.0"
  skip_final_snapshot  = true
  identifier_prefix = "cleaner-test-1"

  tags = {
    (local.t_stop_date) = local.d_p1
  }
}

resource "aws_db_instance" "r2" {
  allocated_storage    = 5
  db_name              = "mydb"
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t3.micro"
  username             = "foo"
  password             = "foobarbaz"
  parameter_group_name = "default.mysql8.0"
  identifier_prefix = "cleaner-test-2"

  tags = {
    (local.t_stop_date)      = local.d_3
    (local.t_stop_notification_1) = local.d_p1    
  }
}

resource "aws_db_instance" "r3" {
  allocated_storage    = 5
  db_name              = "mydb"
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t3.micro"
  username             = "foo"
  password             = "foobarbaz"
  parameter_group_name = "default.mysql8.0"
  identifier_prefix = "cleaner-test-3"

  tags = {
    (local.t_stop_date)      = local.d_p1
    (local.t_stop_notification_1) = local.d_p1
    (local.t_stop_notification_2) = local.d_p1
    (local.t_stop_notification_3) = local.d_p1
  }
}