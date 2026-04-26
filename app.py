from flask import Flask, request, jsonify
import requests
import base64
import os
from datetime import datetime

app = Flask(__name__)

CONSUMER_KEY = os.getenv("DARAJA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("DARAJA_CONSUMER_SECRET")
SHORTCODE = os.getenv("DARAJA_SHORTCODE")  # 4567769
PASSKEY = os.getenv("DARAJA_PASSKEY")
CALLBACK_URL = os.getenv("DARAJA_CALLBACK_URL")

BASE_URL = "https://api.safaricom.co.ke"  # REAL LIVE M-PESA

def format_phone(phone):
    phone = str(phone).strip().replace(" ", "").replace("+", "")
    if phone.startswith("0"):
        return "254" + phone[1:]
    if phone.startswith("7"):
        return "254" + phone
    return phone

def get_access_token():
    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        auth=(CONSUMER_KEY, CONSUMER_SECRET),
        timeout=30
    )

    data = response.json()

    if "access_token" not in data:
        return None, data

    return data["access_token"], None

@app.route("/", methods=["GET"])
def home():
    return "HopestonePay LIVE STK Backend Running"

@app.route("/stkpush", methods=["POST"])
def stkpush():
    try:
        data = request.get_json()

        phone = data.get("phone")
        amount = data.get("amount")

        if not phone or not amount:
            return jsonify({
                "success": False,
                "message": "Phone and amount are required"
            }), 400

        phone = format_phone(phone)
        amount = int(float(amount))

        access_token, token_error = get_access_token()

        if token_error:
            return jsonify({
                "success": False,
                "message": "Failed to get access token",
                "error": token_error
            }), 500

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            (SHORTCODE + PASSKEY + timestamp).encode("utf-8")
        ).decode("utf-8")

        url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": "HopestonePay",
            "TransactionDesc": "HopestonePay Deposit"
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )

        safaricom_response = response.json()

        return jsonify({
            "success": response.status_code in [200, 201],
            "message": "STK request sent",
            "safaricom": safaricom_response
        }), response.status_code

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Server error",
            "error": str(e)
        }), 500

@app.route("/callback", methods=["POST"])
def callback():
    data = request.get_json()
    print("M-PESA CALLBACK:", data)

    return jsonify({
        "ResultCode": 0,
        "ResultDesc": "Callback received successfully"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
