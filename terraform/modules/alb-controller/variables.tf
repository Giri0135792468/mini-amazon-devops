variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "oidc_issuer" {
  description = "EKS OIDC issuer URL"
  type        = string
}

variable "oidc_provider_arn" {
  description = "EKS OIDC provider ARN"
  type        = string
}