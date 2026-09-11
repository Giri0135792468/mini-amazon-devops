from functools import wraps
import jwt
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
print(
    "JWT SECRET HASH:",
    hashlib.sha256(JWT_SECRET.encode()).hexdigest()
)
print("JWT SECRET LENGTH:", len(JWT_SECRET) if JWT_SECRET else "NOT SET")
app = Flask(__name__)
CORS(app)


# -------------------------
# DATABASE CONNECTION
# -------------------------

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


# -------------------------
# JWT TOKEN DECORATOR
# -------------------------

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({
                "message": "Authorization token is required"
            }), 401

        try:
            # Expected format:
            # Authorization: Bearer <token>

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


# -------------------------
# HEALTH
# -------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "user-service",
        "status": "healthy"
    }), 200


# -------------------------
# REGISTER
# -------------------------

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({
            "message": "Name, email and password are required"
        }), 400

    password_hash = generate_password_hash(password)

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
        """

        cursor.execute(
            query,
            (name, email, password_hash)
        )

        connection.commit()

        user_id = cursor.lastrowid

        cursor.close()
        connection.close()

        return jsonify({
            "message": "User registered successfully",
            "user_id": user_id
        }), 201

    except mysql.connector.IntegrityError:
        return jsonify({
            "message": "Email already exists"
        }), 409

    except Exception as e:
        return jsonify({
            "message": "Registration failed",
            "error": str(e)
        }), 500


# -------------------------
# LOGIN
# -------------------------

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "message": "Email and password are required"
        }), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT id, name, email, password
            FROM users
            WHERE email = %s
        """

        cursor.execute(query, (email,))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if not user:
            return jsonify({
                "message": "Invalid email or password"
            }), 401

        if not check_password_hash(user["password"], password):
            return jsonify({
                "message": "Invalid email or password"
            }), 401

        token = jwt.encode(
            {
                "user_id": user["id"],
                "email": user["email"],
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)
            },
            JWT_SECRET,
            algorithm="HS256"
        )

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"]
            }
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Login failed",
            "error": str(e)
        }), 500


# -------------------------
# PROFILE - JWT PROTECTED
# -------------------------

@app.route("/profile", methods=["GET"])
@token_required
def profile():

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, created_at
            FROM users
            WHERE id = %s
            """,
            (request.user_id,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if not user:
            return jsonify({
                "message": "User not found"
            }), 404

        return jsonify(user), 200

    except Exception as e:
        return jsonify({
            "message": "Failed to get profile",
            "error": str(e)
        }), 500


# -------------------------
# GET USER
# -------------------------

@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if not user:
            return jsonify({
                "message": "User not found"
            }), 404

        return jsonify(user), 200

    except Exception as e:
        return jsonify({
            "message": "Failed to get user",
            "error": str(e)
        }), 500


# -------------------------
# UPDATE USER
# -------------------------

@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")

    if not name or not email:
        return jsonify({
            "message": "Name and email are required"
        }), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            UPDATE users
            SET name = %s, email = %s
            WHERE id = %s
        """

        cursor.execute(
            query,
            (name, email, user_id)
        )

        if cursor.rowcount == 0:
            cursor.close()
            connection.close()

            return jsonify({
                "message": "User not found"
            }), 404

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "message": "User updated successfully"
        }), 200

    except mysql.connector.IntegrityError:
        return jsonify({
            "message": "Email already exists"
        }), 409

    except Exception as e:
        return jsonify({
            "message": "Update failed",
            "error": str(e)
        }), 500


# -------------------------
# DELETE USER
# -------------------------

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM users WHERE id = %s",
            (user_id,)
        )

        if cursor.rowcount == 0:
            cursor.close()
            connection.close()

            return jsonify({
                "message": "User not found"
            }), 404

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "message": "User deleted successfully"
        }), 200

    except Exception as e:
        return jsonify({
            "message": "Delete failed",
            "error": str(e)
        }), 500





def init_db():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
    """)

    connection.commit()

    cursor.close()
    connection.close()




# -------------------------
# START APPLICATION
# -------------------------

if __name__ == "__main__":
    init_db()
    app.run(
        host="0.0.0.0",
        port=5000
    )