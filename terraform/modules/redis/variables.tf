variable "namespace" {
  description = "Kubernetes namespace where Redis will run"
  type        = string
  default     = "mini"
}

variable "redis_name" {
  description = "Name of the Redis Kubernetes resources"
  type        = string
  default     = "redis"
}