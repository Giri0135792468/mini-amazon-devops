output "db_endpoint" {
  description = "RDS MySQL endpoint"
  value       = aws_db_instance.mysql.address
}


output "security_group_id" {
  description = "Security group ID of the RDS instance"
  value       = aws_security_group.rds.id
}