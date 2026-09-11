import os
from functools import wraps

import jwt
import redis
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
CORS(app)


# =========================
# Environment Variables
# =========================

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")

JWT_SECRET = os.getenv("JWT_SECRET")


# =========================
# Redis Connection
# =========================

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)


# =========================
# Cart Key
# =========================

def get_cart_key(user_id):
    return f"cart:user:{user_id}"


# =========================
# Product Service
# =========================

def get_product(product_id):

    try:

        response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=5
        )

        if response.status_code != 200:
            return None

        return response.json().get("product")

    except requests.RequestException:
        return None


# =========================
# JWT Authentication
# =========================

def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:

            return jsonify({
                "message": "Authorization token is required"
            }), 401

        try:

            parts = auth_header.split(" ")

            if len(parts) != 2 or parts[0] != "Bearer":

                return jsonify({
                    "message": "Authorization header must be Bearer <token>"
                }), 401

            token = parts[1]

            decoded = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=["HS256"]
            )

            request.user_id = decoded["user_id"]

        except jwt.ExpiredSignatureError:

            return jsonify({
                "message": "Token has expired"
            }), 401

        except (jwt.InvalidTokenError, KeyError):

            return jsonify({
                "message": "Invalid token"
            }), 401

        return f(*args, **kwargs)

    return decorated


# =========================
# Add Product To Cart
# =========================

@app.route("/cart/<int:user_id>/items", methods=["POST"])
@token_required
def add_to_cart(user_id):

    if request.user_id != user_id:

        return jsonify({
            "message": "You are not authorized to access this cart"
        }), 403

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "Request body is required"
        }), 400

    if "product_id" not in data:

        return jsonify({
            "error": "product_id is required"
        }), 400

    if "quantity" not in data:

        return jsonify({
            "error": "quantity is required"
        }), 400

    try:

        quantity = int(data["quantity"])

        if quantity <= 0:

            return jsonify({
                "error": "Quantity must be greater than 0"
            }), 400

    except (TypeError, ValueError):

        return jsonify({
            "error": "Quantity must be a valid number"
        }), 400

    product_id = data["product_id"]

    cart_key = get_cart_key(user_id)

    redis_client.hset(
        cart_key,
        product_id,
        quantity
    )

    return jsonify({

        "message": "Product added to cart",
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity

    }), 201


# =========================
# Get Cart
# =========================

@app.route("/cart/<int:user_id>", methods=["GET"])
@token_required
def get_cart(user_id):

    if request.user_id != user_id:

        return jsonify({
            "message": "You are not authorized to access this cart"
        }), 403

    cart_key = get_cart_key(user_id)

    cart_items = redis_client.hgetall(cart_key)

    items = []

    for product_id, quantity in cart_items.items():

        product = get_product(product_id)

        item = {
            "product_id": product_id,
            "quantity": int(quantity)
        }

        if product:

            item["name"] = product.get("name")
            item["description"] = product.get("description")
            item["price"] = product.get("price")
            item["image_key"] = product.get("image_key")
            item["image_url"] = product.get("image_url")

        items.append(item)

    return jsonify({

        "user_id": user_id,
        "items": items

    }), 200


# =========================
# Update Cart Item
# =========================

@app.route(
    "/cart/<int:user_id>/items/<product_id>",
    methods=["PUT"]
)
@token_required
def update_cart_item(user_id, product_id):

    if request.user_id != user_id:

        return jsonify({
            "message": "You are not authorized to access this cart"
        }), 403

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "Request body is required"
        }), 400

    if "quantity" not in data:

        return jsonify({
            "error": "quantity is required"
        }), 400

    try:

        quantity = int(data["quantity"])

        if quantity <= 0:

            return jsonify({
                "error": "Quantity must be greater than 0"
            }), 400

    except (TypeError, ValueError):

        return jsonify({
            "error": "Quantity must be a valid number"
        }), 400

    cart_key = get_cart_key(user_id)

    if not redis_client.hexists(cart_key, product_id):

        return jsonify({
            "error": "Product is not in the cart"
        }), 404

    redis_client.hset(
        cart_key,
        product_id,
        quantity
    )

    return jsonify({

        "message": "Cart item updated successfully",
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity

    }), 200


# =========================
# Remove Product From Cart
# =========================

@app.route(
    "/cart/<int:user_id>/items/<product_id>",
    methods=["DELETE"]
)
@token_required
def remove_from_cart(user_id, product_id):

    if request.user_id != user_id:

        return jsonify({
            "message": "You are not authorized to access this cart"
        }), 403

    cart_key = get_cart_key(user_id)

    if not redis_client.hexists(cart_key, product_id):

        return jsonify({
            "error": "Product is not in the cart"
        }), 404

    redis_client.hdel(
        cart_key,
        product_id
    )

    return jsonify({

        "message": "Product removed from cart",
        "user_id": user_id,
        "product_id": product_id

    }), 200


# =========================
# Clear Cart
# =========================

@app.route(
    "/cart/<int:user_id>",
    methods=["DELETE"]
)
@token_required
def clear_cart(user_id):

    if request.user_id != user_id:

        return jsonify({
            "message": "You are not authorized to access this cart"
        }), 403

    cart_key = get_cart_key(user_id)

    if not redis_client.exists(cart_key):

        return jsonify({
            "error": "Cart is already empty"
        }), 404

    redis_client.delete(cart_key)

    return jsonify({

        "message": "Cart cleared successfully",
        "user_id": user_id

    }), 200


# =========================
# Health Check
# =========================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({

        "status": "healthy",
        "service": "cart-service"

    }), 200


# =========================
# Run Application
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5002
    )