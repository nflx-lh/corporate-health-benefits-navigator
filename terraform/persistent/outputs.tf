output "ecr_api_url" {
  description = "ECR repository URL for the API image"
  value       = module.ecr.repository_urls["${var.project}-api"]
}

output "ecr_web_url" {
  description = "ECR repository URL for the web image"
  value       = module.ecr.repository_urls["${var.project}-web"]
}

output "ecs_exec_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = module.iam.ecs_exec_role_arn
}

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions OIDC role"
  value       = module.iam.github_actions_role_arn
}

output "jwt_secret_arn" {
  description = "ARN of JWT secret SSM parameter"
  value       = module.ssm.jwt_secret_arn
}

output "openai_api_key_arn" {
  description = "ARN of OpenAI API key SSM parameter"
  value       = module.ssm.openai_api_key_arn
}
