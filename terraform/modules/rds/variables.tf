variable "eks_security_group_id" {
  description = "Security group ID used by EKS nodes"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the RDS security group"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the RDS subnet group"
  type        = list(string)
}

variable "db_name" {
  description = "MySQL database name"
  type        = string
}

variable "db_username" {
  description = "MySQL master username"
  type        = string
}

variable "db_password" {
  description = "MySQL master password"
  type        = string
  sensitive   = true
}