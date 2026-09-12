# Mini Amazon AWS infrastructure

module "vpc" {
  source = "./modules/vpc"
  cluster_name = var.cluster_name
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}



module "rds" {
  source = "./modules/rds"

  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  eks_security_group_id = module.eks.cluster_security_group_id

  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password
}




module "dynamodb" {
  source = "./modules/dynamodb"

  table_name = var.dynamodb_table_name
}


module "s3" {
  source = "./modules/s3"

  bucket_name = var.s3_bucket_name
}


module "eks" {
  source = "./modules/eks"

  cluster_name       = var.cluster_name
  kubernetes_version = var.kubernetes_version

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  node_instance_type = var.node_instance_type
  node_desired_size  = var.node_desired_size
  node_min_size      = var.node_min_size
  node_max_size      = var.node_max_size
}




module "iam" {
  source = "./modules/iam"

  eks_oidc_issuer      = module.eks.cluster_oidc_issuer
  eks_oidc_provider_arn = module.eks.oidc_provider_arn

  product_service_namespace       = "mini"
  product_service_service_account = "product-service-sa"

  s3_bucket_arn      = module.s3.bucket_arn
  dynamodb_table_arn = module.dynamodb.table_arn
}



module "k8s" {
  source = "./modules/k8s"

  namespace = "mini"

  depends_on = [
    module.eks
  ]
}