variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-1"
}

variable "project" {
  description = "Project name prefix"
  type        = string
  default     = "chbn"
}

# --- Persistent stack references ---

variable "ecr_api_url" {
  description = "ECR repo URL for API image (from persistent stack output)"
  type        = string
}

variable "ecr_web_url" {
  description = "ECR repo URL for web image (from persistent stack output)"
  type        = string
}

variable "ecs_exec_role_arn" {
  description = "ECS task execution role ARN (from persistent stack output)"
  type        = string
}

variable "jwt_secret_arn" {
  description = "SSM parameter ARN for JWT secret (from persistent stack output)"
  type        = string
}

variable "openai_api_key_arn" {
  description = "SSM parameter ARN for OpenAI API key (from persistent stack output)"
  type        = string
}

# --- Future toggle ---

variable "enable_rds" {
  description = "Enable RDS PostgreSQL for persistent data (adds ~$0.35/day)"
  type        = bool
  default     = false
}
