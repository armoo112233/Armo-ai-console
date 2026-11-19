
import os
from flask import Flask, request, jsonify, session, render_template
from mcrcon import MCRcon

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "change-this-secret")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
RCON_HOST = os.getenv("RCON_HOST", "")
RCON_PORT = int(os.getenv("RCON_PORT", "25575"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD", "")

ALLOWED_COMMANDS = {
    "list", "say", "time", "weather", "gamemode",
    "tp", "give", "effect", "difficulty", "whitelist",
    "kick", "ban", "pardon", "op", "deop",
    "lp", "eco", "money", "bal", "team", "scoreboard"
}

def run_command(command):
    if not RCON_HOST or not RCON_PASSWORD:
        raise Exception("اطلاعات RCON تنظیم نشده است")

    with MCRcon(
        RCON_HOST,
        RCON_PASSWORD,
        port=RCON_PORT,
        timeout=10
    ) as client:
        return client.command(command)

def allowed(command):
    command = command.strip().lstrip("/")
    if not command or "\n" in command:
        return False
    first = command.split()[0].lower()
    return first in ALLOWED_COMMANDS

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    if ADMIN_PASSWORD and data.get("password") == ADMIN_PASSWORD:
        session["logged_in"] = True
        return jsonify({"ok": True})
    return jsonify({"error": "رمز اشتباه است"}), 401

@app.route("/api/status")
def status():
    if not session.get("logged_in"):
        return jsonify({"error": "ابتدا وارد شوید"}), 401
    try:
        return jsonify({"ok": True, "result": run_command("list")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/execute", methods=["POST"])
def execute():
    if not session.get("logged_in"):
        return jsonify({"error": "ابتدا وارد شوید"}), 401

    data = request.get_json(silent=True) or {}
    command = str(data.get("command", "")).strip()

    if not allowed(command):
        return jsonify({"error": "این دستور مجاز نیست"}), 403

    try:
        result = run_command(command.lstrip("/"))
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/chat", methods=["POST"])
def chat():
    if not session.get("logged_in"):
        return jsonify({"error": "ابتدا وارد شوید"}), 401

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip().lower()

    if "وضعیت" in message or "بازیکن" in message:
        command = "list"
        reply = "برای بررسی وضعیت و تعداد بازیکنان، دستور list پیشنهاد می‌شود."
    elif "شب" in message:
        command = "time set night"
        reply = "برای شب کردن زمان سرور، این دستور پیشنهاد می‌شود."
    elif "روز" in message:
        command = "time set day"
        reply = "برای روز کردن زمان سرور، این دستور پیشنهاد می‌شود."
    else:
        command = ""
        reply = "فعلاً دستیار هوشمند غیرفعال است. می‌توانی دستورات سرور را از بخش اجرای دستور وارد کنی."

    return jsonify({
        "ok": True,
        "reply": reply,
        "command": command
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
