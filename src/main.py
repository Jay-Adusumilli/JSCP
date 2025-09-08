from os import getenv

from flask import Flask, request, abort, jsonify
from dotenv import load_dotenv

from exceptions.exceptions import SignatureError
from payload.payload_parser import parse_github_webhook
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

    # Raw body (bytes) for signature verification inside parser
    body_bytes = request.get_data() or b""

    # Parsed JSON payload
    payload = request.get_json(silent=True)
    if not payload:
        Logs.error("Invalid JSON payload received")
        abort(400, "Invalid JSON payload")

    secret_token = getenv("WEBHOOK_SECRET") or ""
    if not secret_token:
        Logs.error("WEBHOOK_SECRET not configured")
        abort(500, "Server not configured")

    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        Logs.error("Signature header not provided")
        abort(403, "Signature header not provided")

    try:
        parsed_payload = parse_github_webhook(
            payload=payload,
            payload_body=body_bytes,
            secret_token=secret_token,
            signature_header=signature_header,
        )
    except SignatureError:
        Logs.error(f"Invalid signature header: {signature_header}")
        abort(403, "Invalid signature header")
    except Exception as e:
        Logs.error(f"Error parsing payload: {str(e)}")
        abort(400, f"Error parsing payload: {str(e)}")

    return jsonify(parsed_payload.to_dict()), 200


if __name__ == "__main__":
    load_dotenv()

    Logs.info("Starting JSCP server...")

    # Run the Flask app
    app.run(host="0.0.0.0", port=8080)
