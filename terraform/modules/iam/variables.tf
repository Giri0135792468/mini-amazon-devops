variable "eks_oidc_issuer" {
  description = "OIDC issuer URL of the EKS cluster"
  type        = string
}

variable "eks_oidc_provider_arn" {
  description = "ARN of the EKS OIDC provider"
  type        = string
}

variable "product_service_namespace" {
  description = "Kubernetes namespace for the Product Service"
  type        = string
  default     = "mini"
}

variable "product_service_service_account" {
  description = "Kubernetes ServiceAccount used by Product Service"
  type        = string
  default     = "product-service-sa"
}

variable "s3_bucket_arn" {
  description = "ARN of the product images S3 bucket"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN of the products DynamoDB table"
  type        = string
}