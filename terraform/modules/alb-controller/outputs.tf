output "role_arn" {
  description = "IAM Role ARN for AWS Load Balancer Controller"
  value       = aws_iam_role.alb_controller.arn
}