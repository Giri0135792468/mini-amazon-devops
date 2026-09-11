output "product_service_role_arn" {
  description = "IAM Role ARN for the Product Service"
  value       = aws_iam_role.product_service.arn
}



output "product_service_role_name" {
  description = "IAM Role name for the Product Service"
  value       = aws_iam_role.product_service.name
}