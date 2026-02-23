output "repository_urls" {
  description = "Map of repo name to URL"
  value       = { for k, v in aws_ecr_repository.this : k => v.repository_url }
}

output "repository_arns" {
  description = "Map of repo name to ARN"
  value       = { for k, v in aws_ecr_repository.this : k => v.arn }
}
