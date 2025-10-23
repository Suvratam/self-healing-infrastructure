from flask import Flask, request, jsonify
import subprocess
import json
import os
import datetime

app = Flask(__name__)
PLAYBOOK = "/playbooks/restart_nginx.yaml"

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

@app.route("/alert", methods=["POST"])
def alert():
    payload = request.get_json()
    ts = datetime.datetime.utcnow().isoformat()
    print(f"[{ts}] Received alert payload: {json.dumps(payload)}")

    # optional: log payload to file
    with open("/tmp/last_alert.json", "w") as f:
        json.dump(payload, f, indent=2)

    # Run the ansible playbook locally (connection: local)
    cmd = ["ansible-playbook", PLAYBOOK, "-i", "localhost,", "--connection", "local"]
    try:
        print(f"[{ts}] Running: {' '.join(cmd)}")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
        print(f"[{ts}] Ansible stdout:\n{proc.stdout}")
        print(f"[{ts}] Ansible stderr:\n{proc.stderr}")
        rc = proc.returncode
    except Exception as e:
        print(f"[{ts}] Exception while running ansible: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

    if rc == 0:
        return jsonify({"status": "ok", "rc": rc}), 200
    else:
        return jsonify({"status": "failed", "rc": rc}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

