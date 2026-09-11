import os

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

PORT = int(os.getenv("NOTIFICATION_SERVICE_PORT", 5006))
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN")



def internal_token_required(f):

    def decorated(*args, **kwargs):

        token = request.headers.get("X-Internal-Token")

        if not token:
            return jsonify({
                "message": "Internal service token is required"
            }), 401

        if token != INTERNAL_SERVICE_TOKEN:
            return jsonify({
                "message": "Invalid internal service token"
            }), 403

        return f(*args, **kwargs)

    return decorated



@app.route("/health", methods=["GET"])
def health():
    return {
        "status": "Notification Service is running"
    }, 200


@app.route("/notifications", methods=["POST"])
@internal_token_required
def send_notification():
    data = request.get_json()

    if not data:
        return {"error": "Request body is required"}, 400

    if "user_id" not in data:
        return {"error": "user_id is required"}, 400

    if "message" not in data:
        return {"error": "message is required"}, 400

    print(
        f"Notification sent to user {data['user_id']}: "
        f"{data['message']}"
    )

    return {
        "message": "Notification sent successfully",
        "user_id": data["user_id"],
        "notification": data["message"]
    }, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)