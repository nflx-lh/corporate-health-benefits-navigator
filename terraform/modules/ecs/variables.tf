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
  description = "Full ECR image URI with tag (e.g. 123456.dkr.ecr.region.amazonaws.com/chbn-api:sha)"
  type        = string

  validation {
    condition     = can(regex(".+:.+", var.api_image))
    error_message = "api_image must include a tag (e.g. :abc123). Tagless images are not allowed."
  }
}

variable "web_image" {
  description = "Full ECR image URI with tag (e.g. 123456.dkr.ecr.region.amazonaws.com/chbn-web:sha)"
  type        = string

  validation {
    condition     = can(regex(".+:.+", var.web_image))
    error_message = "web_image must include a tag (e.g. :abc123). Tagless images are not allowed."
  }
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

variable "database_url_arn" {
  description = "ARN of the DATABASE_URL SSM parameter (SecureString)"
  type        = string
  default     = ""
}

variable "enable_rds" {
  description = "Whether RDS is enabled (controls REPO_MODE)"
  type        = bool
  default     = false
}
