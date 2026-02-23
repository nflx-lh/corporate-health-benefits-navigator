variable "project" {
  description = "Project name prefix"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_ids" {
  description = "Public subnet IDs for ECS tasks"
  type        = list(string)
}

variable "alb_sg_id" {
  description = "Security group ID of the ALB"
  type        = string
}

variable "execution_role_arn" {
  description = "ARN of the ECS task execution role"
  type        = string
}

variable "api_image" {
  description = "ECR image URL for the API (without tag)"
  type        = string
}

variable "web_image" {
  description = "ECR image URL for the web frontend (without tag)"
  type        = string
}

variable "jwt_secret_arn" {
  description = "ARN of the JWT_SECRET SSM parameter"
  type        = string
}

variable "openai_api_key_arn" {
  description = "ARN of the OPENAI_API_KEY SSM parameter"
  type        = string
}

variable "api_target_group_arn" {
  description = "ARN of the API target group"
  type        = string
}

variable "web_target_group_arn" {
  description = "ARN of the web target group"
  type        = string
}

variable "database_url" {
  description = "PostgreSQL connection string. When set, REPO_MODE switches to db_first."
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_rds" {
  description = "Whether RDS is enabled (controls REPO_MODE)"
  type        = bool
  default     = false
}
