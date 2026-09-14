variable "namespace" {
  description = "Kubernetes namespace"
  type        = string
}

variable "rds_endpoint" {
  description = "RDS MySQL endpoint"
  type        = string
}

variable "db_name" {
  description = "MySQL database name"
  type        = string
}

variable "db_username" {
  description = "MySQL username"
  type        = string
}

variable "db_password" {
  description = "MySQL password"
  type        = string
  sensitive   = true
}

variable "dynamodb_table_name" {
  description = "DynamoDB product table name"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 product image bucket"
  type        = string
}

variable "product_service_role_arn" {
  description = "IAM role ARN for Product Service IRSA"
  type        = string
}

variable "jwt_secret" {
  type      = string
  sensitive = true
}