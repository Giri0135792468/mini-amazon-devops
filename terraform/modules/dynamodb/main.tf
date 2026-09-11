resource "aws_dynamodb_table" "products" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "product_id"

  attribute {
    name = "product_id"
    type = "S"
  }

  tags = {
    Name = "mini-amazon-products"
  }
}



