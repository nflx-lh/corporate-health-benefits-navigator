output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "api_service_name" {
  value = aws_ecs_service.api.name
}

output "web_service_name" {
  value = aws_ecs_service.web.name
}

output "ecs_sg_id" {
  description = "Security group ID of ECS tasks"
  value       = aws_security_group.ecs.id
}
