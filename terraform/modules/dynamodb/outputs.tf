output "table_name" {
  description = "Name of the products DynamoDB table"
  value       = aws_dynamodb_table.products.name
}


output "table_arn" {
  description = "ARN of the products DynamoDB table"
  value       = aws_dynamodb_table.products.arn
}