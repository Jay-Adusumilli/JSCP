import traceback
import atexit
from os import getenv
from threading import Lock, Thread

from flask import Flask, request, abort, jsonify, make_response
from dotenv import load_dotenv
from watchdog.observers import Observer

from config.config_parser import ConfigManager, _ConfigReloadHandler
from exceptions.exceptions import SignatureError
from payload.payload_parser import parse_github_webhook
from logger.logger import Logs
from engine.actions_engine import run_configured_actions


load_dotenv()

Logs.info("Starting JSCP server...")

# Load the configurations from environment variables.
CONFIGS_LOCATION = getenv("CONFIGS_LOCATION") or "./configs"

CONFIG_LOCK = Lock()

with CONFIG_LOCK:
    CONFIGS = ConfigManager(folder_path=CONFIGS_LOCATION)


def _reload_configs():
    global CONFIGS
    with CONFIG_LOCK:
        CONFIGS = ConfigManager(folder_path=CONFIGS_LOCATION)
    Logs.info("Configuration files reloaded successfully")


# Start a background observer to watch the config directory
_observer = Observer()
_handler = _ConfigReloadHandler(_reload_configs)
_observer.schedule(_handler, CONFIGS_LOCATION, recursive=True)
_observer.start()
Logs.info(f"Watching for config changes in: {CONFIGS_LOCATION}")

@atexit.register
def _stop_observer():
    try:
        _observer.stop()
        _observer.join(timeout=2)
    except Exception:
        pass

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
        abort_json(400, "Invalid JSON payload")

    secret_token = getenv("WEBHOOK_SECRET") or ""
    if not secret_token:
        Logs.error("WEBHOOK_SECRET not configured")
        abort_json(400, "WEBHOOK_SECRET not configured")

    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        Logs.error("Signature header not provided")
        abort_json(400, "Signature header not provided")

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

    # Trigger actions engine in the background so the webhook returns quickly
    try:
        with CONFIG_LOCK:
            cfg_snapshot = CONFIGS.get_configs()
        Thread(
            target=run_configured_actions,
            args=(cfg_snapshot, parsed_payload),
            daemon=True,
        ).start()
    except Exception as e:
        Logs.error(f"Failed to start actions engine thread: {e}")

    return jsonify({"StatusMessage": "Success!"}), 200


def abort_json(status_code: int, message: str):
    abort(make_response(jsonify(error=message, status=status_code), status_code))


@app.errorhandler(500)
def handle_500(e):
    Logs.error(f"Internal server error: {str(e)}")
    Logs.debug(traceback.format_exc())
    return jsonify(error="Internal server error", status=500), 500
