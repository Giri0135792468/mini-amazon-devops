import os
import requests
import mysql.connector

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from functools import wraps
import jwt


load_dotenv()

app = Flask(__name__)
CORS(app)


# =========================
# Environment Variables
# =========================

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL")

JWT_SECRET = os.getenv("JWT_SECRET")


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

        if response.status_code != 200:

            return None

        return response.json()

    except requests.RequestException:

        return None


# =========================
# Health Check
# =========================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "Payment Service is running"
    }), 200


# =========================
# Create Payment
# =========================

@app.route("/payments", methods=["POST"])
def create_payment():

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "Request body is required"
        }), 400

    if "order_id" not in data:

        return jsonify({
            "error": "order_id is required"
        }), 400

    if "user_id" not in data:

        return jsonify({
            "error": "user_id is required"
        }), 400

    if "amount" not in data:

        return jsonify({
            "error": "amount is required"
        }), 400

    try:

        amount = float(data["amount"])

    except (TypeError, ValueError):

        return jsonify({
            "error": "Invalid amount"
        }), 400

    if amount <= 0:

        return jsonify({
            "error": "Amount must be greater than 0"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO payments
            (order_id, user_id, amount, status)
            VALUES (%s, %s, %s, %s)
            """,
            (
                data["order_id"],
                data["user_id"],
                amount,
                "PENDING"
            )
        )

        connection.commit()

        payment_id = cursor.lastrowid

    except mysql.connector.Error as e:

        connection.rollback()

        return jsonify({
            "error": "Failed to create payment",
            "details": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()

    return jsonify({

        "message": "Payment created successfully",
        "payment_id": payment_id,
        "order_id": data["order_id"],
        "status": "PENDING"

    }), 201


# =========================
# Get Payment
# =========================

@app.route("/payments/<int:payment_id>", methods=["GET"])
@token_required
def get_payment(payment_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM payments
        WHERE id = %s
        """,
        (payment_id,)
    )

    payment = cursor.fetchone()

    cursor.close()
    connection.close()

    if payment is None:

        return jsonify({
            "error": "Payment not found"
        }), 404

    # Make sure the payment belongs to the logged-in user
    if payment["user_id"] != request.user_id:

        return jsonify({
            "message": "You are not authorized to access this payment"
        }), 403

    return jsonify({

        "payment": payment

    }), 200


# =========================
# Process Payment
# =========================

@app.route(
    "/payments/<int:payment_id>/process",
    methods=["PUT"]
)
def process_payment(payment_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM payments
        WHERE id = %s
        """,
        (payment_id,)
    )

    payment = cursor.fetchone()

    if payment is None:

        cursor.close()
        connection.close()

        return jsonify({
            "error": "Payment not found"
        }), 404

    if payment["status"] != "PENDING":

        cursor.close()
        connection.close()

        return jsonify({
            "error": f"Payment is already {payment['status']}"
        }), 409

    cursor.execute(
        """
        UPDATE payments
        SET status = %s
        WHERE id = %s
        """,
        (
            "SUCCESS",
            payment_id
        )
    )

    connection.commit()

    cursor.close()
    connection.close()

    # -------------------------
    # Send Notification
    # -------------------------

    notification = send_notification(
        payment["user_id"],
        f"Payment successful for Order #{payment['order_id']}!"
    )

    # -------------------------
    # Response
    # -------------------------

    return jsonify({

        "message": "Payment processed successfully",
        "payment_id": payment_id,
        "order_id": payment["order_id"],
        "status": "SUCCESS",
        "notification": notification

    }), 200




# =========================
# Initialize Database
# =========================

def init_db():

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            user_id INT NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            status VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        port=5005
    )