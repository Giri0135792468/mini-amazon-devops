from decimal import Decimal, InvalidOperation
import uuid
import os
import boto3

from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)


# -------------------------
# AWS CONFIGURATION
# -------------------------

AWS_REGION = os.getenv("AWS_REGION")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")
S3_BUCKET = os.getenv("S3_BUCKET")

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION
)

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com"
)


# -------------------------
# DYNAMODB TABLE
# -------------------------

def get_product_table():
    return dynamodb.Table(DYNAMODB_TABLE)


# -------------------------
# GENERATE IMAGE URL
# -------------------------

def generate_image_url(image_key):

    if not image_key:
        return None

    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": image_key
        },
        ExpiresIn=3600
    )


# -------------------------
# CREATE PRODUCT
# -------------------------

@app.route("/products", methods=["POST"])
def create_product():

    data = request.get_json()

    if not data:
        return {
            "error": "Request body is required"
        }, 400

    required_fields = [
        "name",
        "price",
        "description"
    ]

    for field in required_fields:

        if field not in data:
            return {
                "error": f"{field} is required"
            }, 400

    if not isinstance(data["name"], str) or not data["name"].strip():
        return {
            "error": "Product name cannot be empty"
        }, 400

    if not isinstance(data["description"], str) or not data["description"].strip():
        return {
            "error": "Product description cannot be empty"
        }, 400

    try:
        price = Decimal(
            str(data["price"])
        )

        if price <= 0:
            return {
                "error": "Price must be greater than 0"
            }, 400

    except (
        TypeError,
        ValueError,
        InvalidOperation
    ):
        return {
            "error": "Price must be a valid number"
        }, 400

    # Create product ID
    product_id = str(uuid.uuid4())

    # Create product object
    product = {
        "id": product_id,
        "name": data["name"].strip(),
        "price": price,
        "description": data["description"].strip()
    }

    # Get DynamoDB table
    table = get_product_table()

    # Save product to DynamoDB
    table.put_item(
        Item=product
    )

    return {
        "message": "Product created successfully",
        "product": product
    }, 201


# -------------------------
# GET PRODUCT
# -------------------------

@app.route("/products/<product_id>", methods=["GET"])
def get_product(product_id):

    table = get_product_table()

    response = table.get_item(
        Key={
            "id": product_id
        }
    )

    if "Item" not in response:
        return {
            "error": "Product not found"
        }, 404

    product = response["Item"]

    if "image_key" in product:
        product["image_url"] = generate_image_url(
            product["image_key"]
        )

    return {
        "product": product
    }, 200


# -------------------------
# GET ALL PRODUCTS
# -------------------------

@app.route("/products", methods=["GET"])
def get_products():

    table = get_product_table()

    response = table.scan()

    products = response.get(
        "Items",
        []
    )

    for product in products:

        if "image_key" in product:
            product["image_url"] = generate_image_url(
                product["image_key"]
            )

    return {
        "products": products
    }, 200


# -------------------------
# UPLOAD PRODUCT IMAGE
# -------------------------

@app.route("/products/<product_id>/image", methods=["POST"])
def upload_product_image(product_id):

    # Check whether product exists
    response = get_product_table().get_item(
        Key={
            "id": product_id
        }
    )

    if "Item" not in response:
        return {
            "error": "Product not found"
        }, 404

    # Check whether image was uploaded
    if "image" not in request.files:
        return {
            "error": "Image file is required"
        }, 400

    image = request.files["image"]

    if image.filename == "":
        return {
            "error": "Image filename is required"
        }, 400

    # Create S3 object key
    image_key = (
        f"products/{product_id}/{image.filename}"
    )

    # Upload image to S3
    s3.upload_fileobj(
    image,
    S3_BUCKET,
    image_key,
    ExtraArgs={
        "ContentType": image.mimetype
    }
)

    # Save image key in DynamoDB
    get_product_table().update_item(
        Key={
            "id": product_id
        },
        UpdateExpression="SET image_key = :image_key",
        ExpressionAttributeValues={
            ":image_key": image_key
        }
    )

    return {
        "message": "Product image uploaded successfully",
        "product_id": product_id,
        "image_key": image_key
    }, 200


# -------------------------
# UPDATE PRODUCT
# -------------------------

@app.route("/products/<product_id>", methods=["PUT"])
def update_product(product_id):

    data = request.get_json()

    if not data:
        return {
            "error": "Request body is required"
        }, 400

    table = get_product_table()

    existing = table.get_item(
        Key={
            "id": product_id
        }
    )

    if "Item" not in existing:
        return {
            "error": "Product not found"
        }, 404

    update_fields = {}

    # Update name
    if "name" in data:

        if (
            not isinstance(data["name"], str)
            or not data["name"].strip()
        ):
            return {
                "error": "Product name cannot be empty"
            }, 400

        update_fields["name"] = data["name"].strip()

    # Update description
    if "description" in data:

        if (
            not isinstance(data["description"], str)
            or not data["description"].strip()
        ):
            return {
                "error": "Product description cannot be empty"
            }, 400

        update_fields["description"] = data["description"].strip()

    # Update price
    if "price" in data:

        try:
            price = Decimal(
                str(data["price"])
            )

            if price <= 0:
                return {
                    "error": "Price must be greater than 0"
                }, 400

            update_fields["price"] = price

        except (
            TypeError,
            ValueError,
            InvalidOperation
        ):
            return {
                "error": "Price must be a valid number"
            }, 400

    if not update_fields:
        return {
            "error": "No valid fields provided for update"
        }, 400

    # Build DynamoDB update expression
    update_expression = "SET " + ", ".join(
        f"#{field} = :{field}"
        for field in update_fields
    )

    expression_attribute_names = {
        f"#{field}": field
        for field in update_fields
    }

    expression_attribute_values = {
        f":{field}": value
        for field, value in update_fields.items()
    }

    response = table.update_item(
        Key={
            "id": product_id
        },
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
        ReturnValues="ALL_NEW"
    )

    product = response["Attributes"]

    if "image_key" in product:
        product["image_url"] = generate_image_url(
            product["image_key"]
        )

    return {
        "message": "Product updated successfully",
        "product": product
    }, 200


# -------------------------
# DELETE PRODUCT
# -------------------------

@app.route("/products/<product_id>", methods=["DELETE"])
def delete_product(product_id):

    table = get_product_table()

    # Get existing product
    existing = table.get_item(
        Key={
            "id": product_id
        }
    )

    if "Item" not in existing:
        return {
            "error": "Product not found"
        }, 404

    product = existing["Item"]

    # Delete associated S3 image if one exists
    image_key = product.get("image_key")

    if image_key:

        try:
            s3.delete_object(
                Bucket=S3_BUCKET,
                Key=image_key
            )

        except Exception as e:

            return {
                "error": "Failed to delete product image from S3",
                "details": str(e)
            }, 500

    # Delete product from DynamoDB
    table.delete_item(
        Key={
            "id": product_id
        }
    )

    return {
        "message": "Product deleted successfully",
        "product_id": product_id
    }, 200


# -------------------------
# HEALTH
# -------------------------

@app.route("/health", methods=["GET"])
def health():

    return {
        "status": "healthy",
        "service": "product-service"
    }, 200


# -------------------------
# START APPLICATION
# -------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5001
    )