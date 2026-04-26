from flask import Flask, request, jsonify
import requests, base64, os
from datetime import datetime

app = Flask(__name__)

# ========= CONFIG =========
BASE_URL = "https://api.safaricom.co.ke"

CONSUMER_KEY = os.getenv("DARAJA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("DARAJA_CONSUMER_SECRET")
SHORTCODE = os.getenv("DARAJA_SHORTCODE")
PASSKEY = os.getenv("DARAJA_PASSKEY")
CALLBACK_URL = os.getenv("DARAJA_CALLBACK_URL")

# ========= MEMORY (WALLET) =========
wallets = {}
payments = {}

# ========= HELPERS =========
def format_phone(phone):
    phone = str(phone).replace("+", "").strip()
    if phone.startswith("0"):
        return "254" + phone[1:]
    if phone.startswith("7"):
        return "254" + phone
    return phone

def get_token():
    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return r.json()["access_token"]

# ========= DEPOSIT =========
@app.route("/deposit", methods=["POST"])
def deposit():
    data = request.json
    phone = format_phone(data["phone"])
    amount = int(data["amount"])

    token = get_token()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode((SHORTCODE + PASSKEY + timestamp).encode()).decode()

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerBuyGoodsOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": "5402532",
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "HopestonePay",
        "TransactionDesc": "Deposit"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    r = requests.post(f"{BASE_URL}/mpesa/stkpush/v1/processrequest",
                      json=payload, headers=headers)

    res = r.json()
    checkout_id = res.get("CheckoutRequestID")

    payments[checkout_id] = {
        "phone": phone,
        "amount": amount,
        "status": "PENDING"
    }

    return jsonify({"CheckoutRequestID": checkout_id})

# ========= CALLBACK =========
@app.route("/callback", methods=["POST"])
def callback():
    data = request.json
    stk = data["Body"]["stkCallback"]

    checkout_id = stk["CheckoutRequestID"]
    result_code = stk["ResultCode"]

    if result_code == 0:
        items = stk["CallbackMetadata"]["Item"]

        amount = next(i["Value"] for i in items if i["Name"] == "Amount")
        phone = str(next(i["Value"] for i in items if i["Name"] == "PhoneNumber"))

        # update wallet
        if phone not in wallets:
            wallets[phone] = 0

        wallets[phone] += amount

        payments[checkout_id]["status"] = "PAID"
    else:
        payments[checkout_id]["status"] = "FAILED"

    return jsonify({"ResultCode": 0})

# ========= STATUS =========
@app.route("/status/<checkout_id>")
def status(checkout_id):
    return jsonify(payments.get(checkout_id, {"status": "PENDING"}))

# ========= BALANCE =========
@app.route("/balance/<phone>")
def balance(phone):
    phone = format_phone(phone)
    return jsonify({"balance": wallets.get(phone, 0)})

# ========= SEND =========
@app.route("/send", methods=["POST"])
def send():
    data = request.json
    sender = format_phone(data["from"])
    receiver = format_phone(data["to"])
    amount = int(data["amount"])

    if wallets.get(sender, 0) < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    wallets[sender] -= amount

    if receiver not in wallets:
        wallets[receiver] = 0

    wallets[receiver] += amount

    return jsonify({"status": "SUCCESS"})

# ========= HEALTH =========
@app.route("/")
def home():
    return "HopestonePay running"

if __name__ == "__main__":
    app.run()
