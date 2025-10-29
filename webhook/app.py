from flask import Flask, request, jsonify
import subprocess
import json
import os
import datetime
import logging

# ----------------------------
# Configuration
# ----------------------------
PLAYBOOK = "/playbooks/restart_nginx.yaml"
LOG_FILE = "/tmp/alert_service.log"
CPU_THRESHOLD = 90  # %
SERVICE_KEYWORD = "nginx"

# ----------------------------
# Logging Setup
# ----------------------------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app = Flask(__name__)


# ----------------------------
# Utility Functions
# ----------------------------
def run_playbook(playbook_path: str):
    """Run the Ansible playbook locally and return the result."""
    cmd = ["ansible-playbook", playbook_path, "-i", "localhost,", "--connection", "local"]
    logging.info(f"Executing playbook: {' '.join(cmd)}")

    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120
        )
        logging.info(f"Playbook stdout:\n{proc.stdout}")
        if proc.stderr:
            logging.warning(f"Playbook stderr:\n{proc.stderr}")
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        logging.error("Ansible playbook execution timed out.")
        return 124, "Timeout"
    except Exception as e:
        logging.exception(f"Error running Ansible: {e}")
        return 1, str(e)


def evaluate_alert(payload: dict):
    """Decide whether to trigger remediation based on the alert payload."""
    alert_type = payload.get("alert_type", "unknown")
    cpu_usage = payload.get("cpu_usage", 0)
    service_status = payload.get("service_status", "unknown")

    # Rule 1: High CPU usage
    if cpu_usage and cpu_usage > CPU_THRESHOLD:
        logging.warning(f"High CPU detected: {cpu_usage}% (threshold: {CPU_THRESHOLD}%)")
        return True, f"CPU usage {cpu_usage}% > {CPU_THRESHOLD}%"

    # Rule 2: Service down
    if service_status.lower() in ("down", "failed", "inactive"):
        logging.warning(f"Service '{SERVICE_KEYWORD}' is down. Triggering restart.")
        return True, f"Service '{SERVICE_KEYWORD}' is {service_status}"

    # No issue detected
    return False, "No threshold breached"


# ----------------------------
# Routes
# ----------------------------
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()}), 200


@app.route("/alert", methods=["POST"])
def alert():
    """Receive alerts and run playbook if thresholds are breached."""
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid or empty JSON payload"}), 400

    timestamp = datetime.datetime.utcnow().isoformat()
    logging.info(f"Received alert: {json.dumps(payload, indent=2)}")

    # Save payload for debugging
    with open("/tmp/last_alert.json", "w") as f:
        json.dump(payload, f, indent=2)

    trigger, reason = evaluate_alert(payload)
    if not trigger:
        logging.info(f"No action required: {reason}")
        return jsonify({"status": "no_action", "reason": reason}), 200

    logging.info(f"Triggering remediation: {reason}")
    rc, output = run_playbook(PLAYBOOK)

    response = {
        "timestamp": timestamp,
        "trigger_reason": reason,
        "ansible_rc": rc,
        "ansible_output": output.strip(),
    }

    if rc == 0:
        response["status"] = "success"
        return jsonify(response), 200
    else:
        response["status"] = "failed"
        return jsonify(response), 500


# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

