output "bucket_name" {
  description = "Name of the product images S3 bucket"
  value       = aws_s3_bucket.product_images.bucket
}



output "bucket_arn" {
  description = "ARN of the product images S3 bucket"
  value       = aws_s3_bucket.product_images.arn
}