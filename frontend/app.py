import os
import jwt
import requests

from flask import Flask, render_template, redirect, url_for, session, request
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")


# =========================
# Environment Variables
# =========================

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")

PORT = int(os.getenv("FRONTEND_PORT", 5007))


# =========================
# Home Page
# =========================

@app.route("/")
def home():

    try:

        response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            timeout=5
        )

        if response.status_code == 200:

            data = response.json()

            products = data.get(
                "products",
                []
            )

        else:

            products = []

    except requests.RequestException:

        products = []

    return render_template(
        "index.html",
        products=products
    )


# =========================
# Health Check
# =========================

@app.route("/health")
def health():

    return {
        "service": "Mini Amazon Frontend",
        "status": "healthy"
    }, 200


# =========================
# Product Details
# =========================

@app.route("/products/<product_id>")
def product_details(product_id):

    try:

        response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=5
        )

        if response.status_code == 200:

            product = response.json().get("product")

        else:

            return "Product not found", 404

    except requests.RequestException:

        return "Product Service unavailable", 503

    return render_template(
        "product_details.html",
        product=product
    )


# =========================
# Add To Cart
# =========================

@app.route("/cart/add/<product_id>", methods=["POST"])
def add_to_cart(product_id):

    token = session.get("token")

    if not token:
        return redirect(url_for("login"))

    try:

        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )

        user_id = payload["user_id"]

        response = requests.post(
            f"{CART_SERVICE_URL}/cart/{user_id}/items",
            headers={
                "Authorization": f"Bearer {token}"
            },
            json={
                "product_id": product_id,
                "quantity": 1
            },
            timeout=5
        )

        if response.status_code in [200, 201]:

            return redirect(url_for("view_cart"))

        return f"Failed to add product to cart: {response.text}", 400

    except requests.RequestException:

        return "Cart Service unavailable", 503

    except (jwt.InvalidTokenError, KeyError):

        session.clear()

        return redirect(url_for("login"))


# =========================
# Login
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":

        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    try:

        response = requests.post(
            f"{USER_SERVICE_URL}/login",
            json={
                "email": email,
                "password": password
            },
            timeout=5
        )

        if response.status_code == 200:

            data = response.json()

            session["token"] = data["token"]
            session["email"] = email

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid email or password"
        )

    except requests.RequestException:

        return render_template(
            "login.html",
            error="User Service unavailable"
        )


# =========================
# View Cart
# =========================

@app.route("/cart")
def view_cart():

    token = session.get("token")

    if not token:
        return redirect(url_for("login"))

    try:

        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )

        user_id = payload["user_id"]

        response = requests.get(
            f"{CART_SERVICE_URL}/cart/{user_id}",
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=5
        )

        if response.status_code != 200:

            return f"Failed to load cart: {response.text}", 400

        data = response.json()

        cart_items = data.get("items", [])

        total = 0

        for item in cart_items:

            price = float(item.get("price", 0))
            quantity = int(item.get("quantity", 0))

            item["subtotal"] = price * quantity

            total += item["subtotal"]

        return render_template(
            "cart.html",
            cart_items=cart_items,
            total=total
        )

    except requests.RequestException:

        return "Cart Service unavailable", 503

    except (jwt.InvalidTokenError, KeyError):

        session.clear()

        return redirect(url_for("login"))


# =========================
# Remove From Cart
# =========================

@app.route("/cart/remove/<product_id>", methods=["POST"])
def remove_from_cart(product_id):

    token = session.get("token")

    if not token:
        return redirect(url_for("login"))

    try:

        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )

        user_id = payload["user_id"]

        response = requests.delete(
            f"{CART_SERVICE_URL}/cart/{user_id}/items/{product_id}",
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=5
        )

        if response.status_code == 200:

            return redirect(url_for("view_cart"))

        return f"Failed to remove product: {response.text}", 400

    except requests.RequestException:

        return "Cart Service unavailable", 503

    except (jwt.InvalidTokenError, KeyError):

        session.clear()

        return redirect(url_for("login"))


# =========================
# Update Cart
# =========================

@app.route("/cart/update/<product_id>", methods=["POST"])
def update_cart(product_id):

    token = session.get("token")

    if not token:
        return redirect(url_for("login"))

    try:

        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )

        user_id = payload["user_id"]

        quantity = int(
            request.form.get("quantity", 1)
        )

        if quantity < 1:

            return "Quantity must be at least 1", 400

        response = requests.put(
            f"{CART_SERVICE_URL}/cart/{user_id}/items/{product_id}",
            headers={
                "Authorization": f"Bearer {token}"
            },
            json={
                "quantity": quantity
            },
            timeout=5
        )

        if response.status_code == 200:

            return redirect(url_for("view_cart"))

        return f"Failed to update cart: {response.text}", 400

    except ValueError:

        return "Invalid quantity", 400

    except requests.RequestException:

        return "Cart Service unavailable", 503

    except (jwt.InvalidTokenError, KeyError):
        session.clear()

        return redirect(url_for("login"))


# =========================
# Register
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":

        return render_template("register.html")

    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    try:

        response = requests.post(
            f"{USER_SERVICE_URL}/register",
            json={
                "name": name,
                "email": email,
                "password": password
            },
            timeout=5
        )

        if response.status_code == 201:

            return redirect(url_for("login"))

        data = response.json()

        return render_template(
            "register.html",
            error=data.get(
                "error",
                "Registration failed"
            )
        )

    except requests.RequestException:

        return render_template(
            "register.html",
            error="User Service unavailable"
        )


# =========================
# Logout
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================
# Checkout
# =========================

@app.route("/checkout")
def checkout():

    token = session.get("token")

    if not token:
        return redirect(url_for("login"))

    try:

        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )

        user_id = payload["user_id"]

        response = requests.get(
            f"{CART_SERVICE_URL}/cart/{user_id}",
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=5
        )

        if response.status_code != 200:

            return "Unable to load cart", 400

        data = response.json()

        cart_items = data.get("items", [])

        if not cart_items:

            return "Your cart is empty", 400

        total = 0

        for item in cart_items:

            price = float(item.get("price", 0))
            quantity = int(item.get("quantity", 0))

            total += price * quantity

        return render_template(
            "checkout.html",
            total=total
        )

    except requests.RequestException:

        return "Cart Service unavailable", 503

    except (jwt.InvalidTokenError, KeyError):

        session.clear()

        return redirect(url_for("login"))


# =========================
# Place Order
# =========================

@app.route("/checkout/place-order", methods=["POST"])
def place_order():

    token = session.get("token")

    if not token:
        return redirect(url_for("login"))

    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:

        response = requests.post(
            f"{ORDER_SERVICE_URL}/orders",
            headers=headers,
            json={
                "confirm": True
            }
        )

        if response.status_code == 201:

            data = response.json()

            return render_template(
                "order_success.html",
                order=data["order"],
                payment=data.get("payment")
            )

        # Show the actual Order Service error

        try:

            error_data = response.json()

            error_message = error_data.get(
                "error",
                error_data.get(
                    "message",
                    "Failed to create order"
                )
            )

        except ValueError:

            error_message = (
                response.text
                or
                "Failed to create order"
            )

        return (
            f"Failed to create order: {error_message}",
            response.status_code
        )

    except requests.RequestException as e:

        return (
            f"Order Service unavailable: {str(e)}",
            503
        )




# =========================
# Admin - Product Management
# =========================

@app.route("/admin/products")
def admin_products():

    try:

        response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products",
            timeout=5
        )

        if response.status_code != 200:
            return "Unable to load products", 503

        data = response.json()

        products = data.get("products", [])

        return render_template(
            "admin_products.html",
            products=products
        )

    except requests.RequestException:

        return "Product Service unavailable", 503




@app.route("/admin/products/add", methods=["GET", "POST"])
def admin_add_product():

    if request.method == "GET":
        return render_template("admin_add_product.html")

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()
    image = request.files.get("image")

    # Validate required fields
    if not name or not description or not price:
        return "All required fields must be provided", 400

    # Validate price
    try:
        price = float(price)
    except ValueError:
        return "Invalid price", 400

    try:

        # ---------------------------------
        # 1. CREATE PRODUCT
        # ---------------------------------

        response = requests.post(
            f"{PRODUCT_SERVICE_URL}/products",
            json={
                "name": name,
                "description": description,
                "price": price
            },
            timeout=10
        )

        if response.status_code not in (200, 201):
            return (
                f"Product creation failed: {response.text}",
                response.status_code
            )

        data = response.json()

        # Product Service may return the product
        # directly or inside a "product" object.
        product = data.get("product", data)

        product_id = product.get("id")

        if not product_id:
            return "Product created but product ID was not returned", 500


        # ---------------------------------
        # 2. UPLOAD IMAGE IF PROVIDED
        # ---------------------------------

        if image and image.filename:

            image_response = requests.post(
                f"{PRODUCT_SERVICE_URL}/products/{product_id}/image",
                files={
                    "image": (
                        image.filename,
                        image.stream,
                        image.mimetype
                    )
                },
                timeout=30
            )

            if image_response.status_code != 200:
                return (
                    f"Product created, but image upload failed: "
                    f"{image_response.text}",
                    502
                )


        # ---------------------------------
        # 3. RETURN TO PRODUCT MANAGEMENT
        # ---------------------------------

        return redirect(url_for("admin_products"))


    except requests.RequestException as e:

        return (
            f"Product Service unavailable: {str(e)}",
            503
        )






@app.route("/admin/products/edit/<product_id>", methods=["GET", "POST"])
def admin_edit_product(product_id):

    # ---------------------------------
    # GET PRODUCT
    # ---------------------------------

    try:

        response = requests.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=5
        )

        if response.status_code != 200:
            return "Product not found", 404

        data = response.json()
        product = data.get("product", {})

    except requests.RequestException:

        return "Product Service unavailable", 503


    # ---------------------------------
    # DISPLAY EDIT FORM
    # ---------------------------------

    if request.method == "GET":

        return render_template(
            "admin_edit_product.html",
            product=product
        )


    # ---------------------------------
    # UPDATE PRODUCT
    # ---------------------------------

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()


    if not name or not description or not price:

        return "All fields are required", 400


    try:

        price = float(price)

    except ValueError:

        return "Invalid price", 400


    try:

        update_response = requests.put(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            json={
                "name": name,
                "description": description,
                "price": price
            },
            timeout=10
        )

        if update_response.status_code != 200:

            return (
                f"Product update failed: "
                f"{update_response.text}",
                update_response.status_code
            )


        return redirect(
            url_for("admin_products")
        )


    except requests.RequestException:

        return "Product Service unavailable", 503


@app.route("/admin/products/delete/<product_id>", methods=["POST"])
def admin_delete_product(product_id):

    try:

        response = requests.delete(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=10
        )

        if response.status_code != 200:
            return (
                f"Product deletion failed: {response.text}",
                response.status_code
            )

        return redirect(url_for("admin_products"))

    except requests.RequestException:

        return "Product Service unavailable", 503


    
# =========================
# Run Application
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=True
    )