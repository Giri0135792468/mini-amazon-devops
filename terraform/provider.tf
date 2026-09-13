provider "aws" {
  region = var.aws_region
}

data "aws_eks_cluster" "main" {
  name = module.eks.cluster_name

  depends_on = [
    module.eks
  ]
}

data "aws_eks_cluster_auth" "main" {
  name = module.eks.cluster_name

  depends_on = [
    module.eks
  ]
}

