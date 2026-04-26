from flask import Flask, request, jsonify
import requests
import base64
import os
from datetime import datetime

app = Flask(__name__)

# Environment variables
CONSUMER_KEY = os.getenv("DARAJA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("DARAJA_CONSUMER_SECRET")
SHORTCODE = os.getenv("DARAJA_SHORTCODE")
PASSKEY = os.getenv("DARAJA_PASSKEY")
CALLBACK_URL = os.getenv("DARAJA_CALLBACK_URL")

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return response.json()['access_token']

@app.route("/")
def home():
    return "HopestonePay STK Backend Running"

@app.route("/stkpush", methods=["POST"])
def stkpush():
    data = request.json
    phone = data.get("phone")
    amount = data.get("amount")

    # format phone
    if phone.startswith("0"):
        phone = "254" + phone[1:]

    access_token = get_access_token()

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((SHORTCODE + PASSKEY + timestamp).encode()).decode()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

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
        "TransactionDesc": "Payment"
    }

    response = requests.post(url, json=payload, headers=headers)

    return jsonify(response.json())

@app.route("/callback", methods=["POST"])
def callback():
    print(request.json)
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

if __name__ == "__main__":
    app.run()
