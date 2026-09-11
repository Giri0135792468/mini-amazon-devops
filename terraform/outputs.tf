output "vpc_id" {
  description = "Mini Amazon VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "rds_endpoint" {
  description = "RDS MySQL endpoint"
  value       = module.rds.db_endpoint
}

output "dynamodb_table_name" {
  description = "Products DynamoDB table name"
  value       = module.dynamodb.table_name
}

output "s3_bucket_name" {
  description = "Product images S3 bucket name"
  value       = module.s3.bucket_name
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS Kubernetes API endpoint"
  value       = module.eks.cluster_endpoint
}

output "product_service_role_arn" {
  description = "Product Service IAM Role ARN"
  value       = module.iam.product_service_role_arn
}