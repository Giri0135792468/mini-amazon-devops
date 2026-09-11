import os
import mysql.connector
import requests
from functools import wraps
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import jwt
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import hashlib


# =========================
# HTTP RETRY CONFIGURATION
# =========================

retry_strategy = Retry(
    total=2,
    backoff_factor=1,
    status_forcelist=[502, 503, 504],
    allowed_methods=["GET"]
)

adapter = HTTPAdapter(max_retries=retry_strategy)

http = requests.Session()
http.mount("http://", adapter)
http.mount("https://", adapter)


# =========================
# LOAD ENVIRONMENT
# =========================

load_dotenv()


# =========================
# FLASK APPLICATION
# =========================

app = Flask(__name__)
CORS(app)


# =========================
# Environment Variables
# =========================

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN")

CART_SERVICE_URL = os.getenv("CART_SERVICE_URL")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL")

JWT_SECRET = os.getenv("JWT_SECRET")


print(
    "JWT SECRET HASH:",
    hashlib.sha256(JWT_SECRET.encode()).hexdigest()
)

print(
    "JWT SECRET LENGTH:",
    len(JWT_SECRET) if JWT_SECRET else "NOT SET"
)


# =========================
# Database Connection
# =========================

def get_db_connection():

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


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
# Product Service
# =========================

def get_product(product_id):

    try:

        response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=5
        )

        if response.status_code == 200:

            return response.json().get("product")

        return None

    except requests.RequestException:

        return None


# =========================
# Payment Service
# =========================

def create_payment(order_id, user_id, amount):

    try:

        response = requests.post(
            f"{PAYMENT_SERVICE_URL}/payments",
            json={
                "order_id": order_id,
                "user_id": user_id,
                "amount": amount
            },
            timeout=5
        )

        if response.status_code == 201:

            return response.json()

        return None

    except requests.RequestException:

        return None


# =========================
# Notification Service
# =========================

def send_notification(user_id, message):

    try:

        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/notifications",
            json={
                "user_id": user_id,
                "message": message
            },
            headers={
                "X-Internal-Token": INTERNAL_SERVICE_TOKEN
            },
            timeout=5
        )

        if response.status_code == 200:

            return response.json()

        return None

    except requests.RequestException:

        return None


# =========================
# Health Check
# =========================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "Order Service is running"
    }), 200


# =========================
# Get Order By ID
# =========================

def get_order_by_id(order_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM orders
        WHERE id = %s
        """,
        (order_id,)
    )

    order = cursor.fetchone()

    cursor.close()
    connection.close()

    return order


# =========================
# Get Order Items
# =========================

def get_order_items(order_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM order_items
        WHERE order_id = %s
        """,
        (order_id,)
    )

    items = cursor.fetchall()

    cursor.close()
    connection.close()

    return items


# =========================
# Enrich Order Items
# =========================

def enrich_order_items(items):

    enriched_items = []

    for item in items:

        product = get_product(item["product_id"])

        if product:

            item["name"] = product.get("name")
            item["description"] = product.get("description")
            item["image_key"] = product.get("image_key")
            item["image_url"] = product.get("image_url")

        enriched_items.append(item)

    return enriched_items


# =========================
# Cart Service
# =========================

def get_cart(user_id):

    try:

        auth_header = request.headers.get("Authorization")

        response = http.get(
            f"{CART_SERVICE_URL}/cart/{user_id}",
            headers={
                "Authorization": auth_header
            },
            timeout=5
        )

        if response.status_code == 200:

            return response.json()

        return None

    except requests.RequestException:

        return None


# =========================
# Create Order
# =========================

@app.route("/orders", methods=["POST"])
@token_required
def create_order():

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "Request body is required"
        }), 400

    # User ID comes from JWT
    user_id = request.user_id


    # =========================
    # Get Cart
    # =========================

    cart = get_cart(user_id)

    if cart is None:

        return jsonify({
            "error": "Unable to fetch cart"
        }), 502

    items = cart.get("items", [])

    if not items:

        return jsonify({
            "error": "Cart is empty"
        }), 400


    # =========================
    # Validate Products
    # =========================

    total_amount = 0

    processed_items = []

    for item in items:

        product_id = item.get("product_id")
        quantity = item.get("quantity")

        if not product_id:

            return jsonify({
                "error": "product_id is required"
            }), 400

        if not isinstance(quantity, int) or quantity <= 0:

            return jsonify({
                "error": "quantity must be a positive integer"
            }), 400


        # =========================
        # Get Product
        # =========================

        product = get_product(product_id)

        if not product:

            return jsonify({
                "error": f"Product {product_id} not found"
            }), 404

        price = float(product.get("price", 0))

        if price <= 0:

            return jsonify({
                "error": f"Invalid price for product {product_id}"
            }), 400


        # =========================
        # Calculate Total
        # =========================

        total_amount += price * quantity

        processed_items.append({
            "product_id": product_id,
            "quantity": quantity,
            "price": price
        })


    # =========================
    # Create Order in MySQL
    # =========================

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO orders
            (user_id, total_amount, status)
            VALUES (%s, %s, %s)
            """,
            (
                user_id,
                total_amount,
                "PENDING"
            )
        )

        order_id = cursor.lastrowid


        # =========================
        # Insert Order Items
        # =========================

        for item in processed_items:

            cursor.execute(
                """
                INSERT INTO order_items
                (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["quantity"],
                    item["price"]
                )
            )

        connection.commit()

    except mysql.connector.Error as e:

        connection.rollback()

        return jsonify({
            "error": "Failed to create order",
            "details": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


    # =========================
    # Create Payment
    # =========================

    payment = create_payment(
        order_id,
        user_id,
        total_amount
    )

    if payment is None:

        return jsonify({
            "error": "Order created but payment creation failed",
            "order_id": order_id
        }), 502


    # =========================
    # Send Notification
    # =========================

    notification = send_notification(
        user_id,
        f"Order #{order_id} has been created successfully."
    )


    # =========================
    # Response
    # =========================

    return jsonify({

        "message": "Order created successfully",

        "order": {
            "id": order_id,
            "user_id": user_id,
            "total_amount": total_amount,
            "status": "PENDING"
        },

        "payment": payment,

        "notification": notification

    }), 201


# =========================
# Get Single Order
# =========================

@app.route("/orders/<int:order_id>", methods=["GET"])
@token_required
def get_order(order_id):

    order = get_order_by_id(order_id)

    if not order:

        return jsonify({
            "error": "Order not found"
        }), 404

    # Make sure user can only see their own order
    if order["user_id"] != request.user_id:

        return jsonify({
            "message": "You are not authorized to access this order"
        }), 403

    items = get_order_items(order_id)

    items = enrich_order_items(items)

    return jsonify({

        "order": order,

        "items": items

    }), 200


# =========================
# Get User Orders
# =========================

@app.route("/orders/user/<int:user_id>", methods=["GET"])
@token_required
def get_user_orders(user_id):

    if request.user_id != user_id:

        return jsonify({
            "message": "You are not authorized to access these orders"
        }), 403

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    for order in orders:

        items = get_order_items(order["id"])

        order["items"] = enrich_order_items(items)

    return jsonify({

        "user_id": user_id,

        "orders": orders

    }), 200


# =========================
# Cancel Order
# =========================

@app.route("/orders/<int:order_id>/cancel", methods=["PUT"])
@token_required
def cancel_order(order_id):

    order = get_order_by_id(order_id)

    if not order:

        return jsonify({
            "error": "Order not found"
        }), 404

    # Make sure user owns the order
    if order["user_id"] != request.user_id:

        return jsonify({
            "message": "You are not authorized to cancel this order"
        }), 403

    if order["status"] != "PENDING":

        return jsonify({
            "error": "Only PENDING orders can be cancelled"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE orders
        SET status = %s
        WHERE id = %s
        """,
        (
            "CANCELLED",
            order_id
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({

        "message": "Order cancelled successfully",

        "order": {
            "id": order_id,
            "status": "CANCELLED"
        }

    }), 200


# =========================
# Update Order Status
# =========================

@app.route("/orders/<int:order_id>/status", methods=["PUT"])
@token_required
def update_order_status(order_id):

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "Request body is required"
        }), 400

    status = data.get("status")

    if not status:

        return jsonify({
            "error": "status is required"
        }), 400

    allowed_statuses = [
        "PENDING",
        "CONFIRMED",
        "PAID",
        "SHIPPED",
        "DELIVERED",
        "CANCELLED"
    ]

    if status not in allowed_statuses:

        return jsonify({
            "error": "Invalid status",
            "allowed_statuses": allowed_statuses
        }), 400

    order = get_order_by_id(order_id)

    if not order:

        return jsonify({
            "error": "Order not found"
        }), 404

    # Make sure user owns the order
    if order["user_id"] != request.user_id:

        return jsonify({
            "message": "You are not authorized to update this order"
        }), 403

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE orders
        SET status = %s
        WHERE id = %s
        """,
        (
            status,
            order_id
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({

        "message": "Order status updated successfully",

        "order": {
            "id": order_id,
            "status": status
        }

    }), 200





# =========================
# Initialize Database
# =========================

def init_db():

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            status VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            product_id VARCHAR(255) NOT NULL,
            quantity INT NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
            ON DELETE CASCADE
        )
    """)

    connection.commit()

    cursor.close()
    connection.close()




# =========================
# Run Application
# =========================

if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5004,
        debug=True
    )