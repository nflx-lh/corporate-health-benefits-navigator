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

variable "env" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "github_repo" {
  description = "GitHub repo (owner/name)"
  type        = string
  default     = "nflx-lh/corporate-health-benefits-navigator"
}

variable "create_github_oidc" {
  description = "Set to false if GitHub OIDC provider already exists in your account"
  type        = bool
  default     = true
}
