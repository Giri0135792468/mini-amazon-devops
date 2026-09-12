variable "aws_region" {
  description = "AWS region for Mini Amazon infrastructure"
  type        = string
  default     = "ap-south-2"
}

variable "vpc_cidr" {
  description = "CIDR block for Mini Amazon VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability Zones for Mini Amazon"
  type        = list(string)
  default     = ["ap-south-2a", "ap-south-2b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "db_name" {
  description = "MySQL database name"
  type        = string
  default     = "mini_amazon"
}

variable "db_username" {
  description = "MySQL master username"
  type        = string
  default     = "admin"
}

variable "db_password" {
  description = "MySQL master password"
  type        = string
  sensitive   = true
}

variable "cluster_name" {
  description = "Name of the Mini Amazon EKS cluster"
  type        = string
  default     = "mini-amazon-eks"
}

variable "kubernetes_version" {
  description = "Kubernetes version for EKS"
  type        = string
  default     = "1.33"
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS worker nodes"
  type        = string
  default     = "t3.small"
}

variable "node_desired_size" {
  description = "Desired number of EKS worker nodes"
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum number of EKS worker nodes"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of EKS worker nodes"
  type        = number
  default     = 3
}

variable "dynamodb_table_name" {
  description = "Name of the Mini Amazon products DynamoDB table"
  type        = string
  default     = "mini-amazon-products"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for Mini Amazon product images"
  type        = string
  default     = "mini-amazon-product-images"
}