output "alb_dns_name" {
  description = "Public DNS name of the ALB — use this to access the app"
  value       = module.alb.alb_dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "api_service_name" {
  description = "ECS API service name"
  value       = module.ecs.api_service_name
}

output "web_service_name" {
  description = "ECS web service name"
  value       = module.ecs.web_service_name
}

output "rds_endpoint" {
  description = "RDS endpoint (only when enable_rds=true)"
  value       = var.enable_rds ? module.rds[0].endpoint : null
}

output "rds_db_name" {
  description = "RDS database name"
  value       = var.enable_rds ? module.rds[0].db_name : null
}
