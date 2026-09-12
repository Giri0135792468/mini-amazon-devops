output "redis_service_name" {
  description = "Kubernetes Service name used by the Cart Service to reach Redis"
  value       = kubernetes_service.redis.metadata[0].name
}

output "redis_port" {
  description = "Redis service port"
  value       = 6379
}