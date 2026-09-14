resource "kubernetes_namespace" "mini" {
  metadata {
    name = var.namespace
  }
}

resource "kubernetes_config_map" "aws_config" {
  metadata {
    name      = "aws-config"
    namespace = var.namespace
  }

 data = {
  AWS_REGION      = "ap-south-2"
  DYNAMODB_TABLE  = var.dynamodb_table_name
  S3_BUCKET_NAME  = var.s3_bucket_name
}
}

resource "kubernetes_config_map" "database_config" {
  metadata {
    name      = "database-config"
    namespace = var.namespace
  }

  data = {
    DB_HOST = var.rds_endpoint
    DB_PORT = "3306"
    DB_NAME = var.db_name
    DB_USER = var.db_username
  }
}

resource "kubernetes_secret" "database" {
  metadata {
    name      = "database-secret"
    namespace = var.namespace
  }

  type = "Opaque"

  data = {
    DB_PASSWORD = var.db_password
  }
}

resource "kubernetes_service_account" "product_service" {
  metadata {
    name      = "product-service-sa"
    namespace = var.namespace

    annotations = {
      "eks.amazonaws.com/role-arn" = var.product_service_role_arn
    }
  }
}


resource "kubernetes_secret" "application" {
  metadata {
    name      = "application-secret"
    namespace = var.namespace
  }

  type = "Opaque"

  data = {
    JWT_SECRET = var.jwt_secret
  }
}