from flask import Flask, request, jsonify
import requests
import base64
import os
from datetime import datetime

app = Flask(__name__)

# ENV VARIABLES (SET THESE IN RENDER)
CONSUMER_KEY = os.getenv("DARAJA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("DARAJA_CONSUMER_SECRET")
SHORTCODE = os.getenv("DARAJA_SHORTCODE")  # 4567769
PASSKEY = os.getenv("DARAJA_PASSKEY")
CALLBACK_URL = os.getenv("DARAJA_CALLBACK_URL")

BASE_URL = "https://api.safaricom.co.ke"  # LIVE

# FORMAT PHONE NUMBER
def format_phone(phone):
    phone = str(phone).strip().replace(" ", "").replace("+", "")
    if phone.startswith("0"):
        return "254" + phone[1:]
    if phone.startswith("7"):
        return "254" + phone
    return phone

# GET ACCESS TOKEN
def get_access_token():
    url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return response.json().get("access_token")

# STK PUSH ROUTE (THIS WAS MISSING / BROKEN)
@app.route('/stkpush', methods=['POST'])
def stkpush():
    try:
        data = request.get_json()
        phone = format_phone(data.get("phone"))
        amount = int(data.get("amount"))

        access_token = get_access_token()

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            (SHORTCODE + PASSKEY + timestamp).encode()
        ).decode()

        url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerBuyGoodsOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": "5402532",  # YOUR TILL NUMBER
            "PhoneNumber": phone,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": "HopestonePay",
            "TransactionDesc": "Deposit"
        }

        res = requests.post(url, json=payload, headers=headers)

        return jsonify({
            "success": True,
            "response": res.json()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# CALLBACK (VERY IMPORTANT FOR PAYMENT CONFIRMATION)
@app.route('/callback', methods=['POST'])
def callback():
    data = request.json
    print("M-PESA CALLBACK:", data)
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


# ROOT ROUTE
@app.route('/')
def home():
    return "HopestonePay STK Backend Running ✅"


if __name__ == '__main__':
    app.run()
