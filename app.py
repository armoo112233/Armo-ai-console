
import os
import json
from flask import Flask, request, jsonify, session, render_template
from mcrcon import MCRcon
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "change-this-secret")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
RCON_HOST = os.getenv("RCON_HOST", "")
RCON_PORT = int(os.getenv("RCON_PORT", "25575"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

genai.configure(api_key=GEMINI_API_KEY)

ALLOWED_PREFIXES = (
    "list", "say ", "time ", "weather ",
    "gamemode ", "tp ", "give ", "effect ",
    "difficulty ", "whitelist ", "kick ",
    "ban ", "pardon ", "op ", "deop ",
    "lp ", "eco ", "money ", "bal ",
    "team ", "scoreboard "
)

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
    command = command.strip()
    if not command or "\n" in command:
        return False
    if command.startswith("/"):
        command = command[1:]
    return command.lower().startswith(ALLOWED_PREFIXES)

@app.route("/")
def home():
    if not session.get("logged_in"):
        return render_template("index.html")
    return render_template("index.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    if data.get("password") == ADMIN_PASSWORD and ADMIN_PASSWORD:
        session["logged_in"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "رمز اشتباه است"}), 401

@app.route("/api/status")
def status():
    if not session.get("logged_in"):
        return jsonify({"ok": False}), 401
    try:
        result = run_command("list")
        return jsonify({"ok": True, "result": result})
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
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({"error": "پیام خالی است"}), 400

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = """
تو دستیار مدیریت سرور Minecraft Paper هستی.
فقط به فارسی پاسخ بده.
اگر کاربر درخواست اجرای دستور داشت،
یک دستور مناسب پیشنهاد بده.
هرگز دستور stop، restart یا حذف فایل پیشنهاد نده.
خروجی را فقط به شکل JSON بده:
{"reply":"پاسخ فارسی","command":""}
اگر دستور لازم نیست command خالی باشد.
درخواست کاربر:
""" + message

        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)

        command = str(result.get("command", "")).strip()
        if command and not allowed(command):
            command = ""

        return jsonify({
            "ok": True,
            "reply": result.get("reply", ""),
            "command": command
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
