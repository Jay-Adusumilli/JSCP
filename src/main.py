from os import getenv

from flask import Flask, request, abort
from dotenv import load_dotenv

from exceptions.exceptions import SignatureError
from payload.payload_parser import parse_github_webhook
from payload.signature import verify_signature
from logger.logger import Logs

app = Flask(__name__)

@app.route("/jscp", methods=["POST"])
def jscp():
    """
    Handle incoming JSON payloads from GitHub webhooks.
    :return: JSON response with parsed event data or error.
    """

    Logs.info("Received incoming JSON payload")

    if request.method != "POST":
        abort(405)

    # Verify the request content type.
    payload = request.get_json()
    if not payload:
        Logs.error("Invalid JSON payload received")
        abort(400, "Invalid JSON payload")

    # Verify the signature of the payload.
    secret_token = getenv("WEBHOOK_SECRET")
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        Logs.error("Signature header not provided")
        abort(403, "Signature header not provided")
    try:
        verify_signature(payload, secret_token, signature_header)
    except SignatureError:
        Logs.error(f"Invalid signature header: {signature_header}")
        abort(403, "Invalid signature header")

    # Parse the payload.
    try:
        parsed_payload = parse_github_webhook(payload)
    except Exception as e:
        Logs.error(f"Error parsing payload: {str(e)}")
        abort(400, f"Error parsing payload: {str(e)}")






if __name__ == "__main__":
    load_dotenv()

    Logs.info("Starting JSCP server...")

    # Run the Flask app
    app.run(host="0.0.0.0", port=8080)
