variable "project" {
  description = "Project name prefix"
  type        = string
}

variable "ssm_param_arns" {
  description = "List of SSM parameter ARNs the ECS task can read"
  type        = list(string)
}

variable "ecr_repo_arns" {
  description = "List of ECR repo ARNs GitHub Actions can push to"
  type        = list(string)
}

variable "github_repo" {
  description = "GitHub repo in owner/name format"
  type        = string
}

variable "create_github_oidc" {
  description = "Whether to create the GitHub OIDC provider (false if it already exists)"
  type        = bool
  default     = true
}
