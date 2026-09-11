resource "aws_iam_policy" "product_service" {
  name        = "mini-amazon-product-service-policy"
  description = "Allows Product Service to access product images in S3 and products in DynamoDB"

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]

        Resource = var.dynamodb_table_arn
      },
      {
        Effect = "Allow"

        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]

        Resource = "${var.s3_bucket_arn}/*"
      }
    ]
  })
}



resource "aws_iam_role" "product_service" {
  name = "mini-amazon-product-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Federated = var.eks_oidc_provider_arn
        }

        Action = "sts:AssumeRoleWithWebIdentity"

        Condition = {
          StringEquals = {
            "${replace(var.eks_oidc_issuer, "https://", "")}:sub" = "system:serviceaccount:${var.product_service_namespace}:${var.product_service_service_account}"

            "${replace(var.eks_oidc_issuer, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Name = "mini-amazon-product-service-role"
  }
}



resource "aws_iam_role_policy_attachment" "product_service" {
  role       = aws_iam_role.product_service.name
  policy_arn = aws_iam_policy.product_service.arn
}