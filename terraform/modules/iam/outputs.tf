output "ecs_exec_role_arn" {
  description = "ARN of ECS task execution role"
  value       = aws_iam_role.ecs_exec.arn
}

output "github_actions_role_arn" {
  description = "ARN of GitHub Actions OIDC role"
  value       = aws_iam_role.github_actions.arn
}
