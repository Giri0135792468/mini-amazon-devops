resource "aws_db_subnet_group" "main" {
  name = "mini-amazon-rds-subnet-group"

  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "mini-amazon-rds-subnet-group"
  }
}





resource "aws_db_instance" "mysql" {
  identifier = "mini-amazon-mysql"

  engine         = "mysql"
  engine_version = "8.0"

  instance_class        = "db.t3.micro"
  allocated_storage     = 20
  max_allocated_storage = 50

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible    = false
  multi_az               = false
  skip_final_snapshot    = true

  tags = {
    Name = "mini-amazon-mysql"
  }
}






resource "aws_security_group" "rds" {
  name        = "mini-amazon-rds-sg"
  description = "Security group for Mini Amazon RDS MySQL"
  vpc_id      = var.vpc_id

  ingress {
    description = "MySQL from EKS"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"

    security_groups = [
      var.eks_security_group_id
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "mini-amazon-rds-sg"
  }
}