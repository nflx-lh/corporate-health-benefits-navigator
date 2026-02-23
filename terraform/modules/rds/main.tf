# --- Random password for DB master user ---

resource "random_password" "db" {
  length  = 24
  special = false # avoid shell-escaping headaches in DATABASE_URL
}

# --- DB Subnet Group (private subnets) ---

resource "aws_db_subnet_group" "this" {
  name       = "${var.project}-db-subnets"
  subnet_ids = var.private_subnet_ids

  tags = { Name = "${var.project}-db-subnets" }
}

# --- Security Group: Postgres 5432 from ECS only ---

resource "aws_security_group" "rds" {
  name_prefix = "${var.project}-rds-"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Postgres from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-rds-sg" }
}

# --- RDS Postgres Instance ---

resource "aws_db_instance" "this" {
  identifier     = "${var.project}-postgres"
  engine         = "postgres"
  engine_version = "16.12"
  instance_class = var.instance_class

  allocated_storage = var.allocated_storage
  storage_type      = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible = false
  multi_az            = false

  skip_final_snapshot     = true
  deletion_protection     = false
  backup_retention_period = 0 # no automated backups for demo

  tags = { Name = "${var.project}-postgres" }
}
