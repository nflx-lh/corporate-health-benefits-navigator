variable "project" {
  description = "Project name prefix"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for RDS placement"
  type        = list(string)
}

variable "ecs_sg_id" {
  description = "Security group ID of ECS tasks (allowed to connect on 5432)"
  type        = string
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "chbn"
}

variable "db_username" {
  description = "Master DB username"
  type        = string
  default     = "chbn"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Storage in GB"
  type        = number
  default     = 20
}
