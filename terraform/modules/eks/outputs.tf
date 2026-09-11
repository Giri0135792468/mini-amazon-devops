output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = aws_eks_cluster.main.name
}





output "cluster_endpoint" {
  description = "Endpoint of the EKS Kubernetes API server"
  value       = aws_eks_cluster.main.endpoint
}






output "oidc_provider_arn" {
  description = "ARN of the EKS OIDC provider"
  value       = aws_iam_openid_connect_provider.eks.arn
}






output "node_role_arn" {
  description = "ARN of the EKS worker node IAM role"
  value       = aws_iam_role.node.arn
}





output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
}



output "cluster_oidc_issuer" {
  description = "OIDC issuer URL of the EKS cluster"
  value       = aws_eks_cluster.main.identity[0].oidc[0].issuer
}