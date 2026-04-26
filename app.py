from flask import Flask, request, jsonify
from db import SessionLocal, engine
from models import Base, User, Transaction
import requests, base64, os
from datetime import datetime

Base.metadata.create_all(bind=engine)

app = Flask(__name__)

BASE_URL = "https://api.safaricom.co.ke"

def format_phone(phone):
    if phone.startswith("0"):
        return "254" + phone[1:]
    return phone

def get_token():
    r = requests.get(
        f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
        auth=(os.getenv("DARAJA_CONSUMER_KEY"), os.getenv("DARAJA_CONSUMER_SECRET"))
    )
    return r.json()["access_token"]

# ================= DEPOSIT =================
@app.route("/deposit", methods=["POST"])
def deposit():
    phone = format_phone(request.json["phone"])
    amount = int(request.json["amount"])

    token = get_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        (os.getenv("DARAJA_SHORTCODE") + os.getenv("DARAJA_PASSKEY") + timestamp).encode()
    ).decode()

    payload = {
        "BusinessShortCode": os.getenv("DARAJA_SHORTCODE"),
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerBuyGoodsOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": "5402532",
        "PhoneNumber": phone,
        "CallBackURL": os.getenv("DARAJA_CALLBACK_URL"),
        "AccountReference": "HopestonePay",
        "TransactionDesc": "Deposit"
    }

    headers = {"Authorization": f"Bearer {token}"}

    r = requests.post(f"{BASE_URL}/mpesa/stkpush/v1/processrequest",
                      json=payload, headers=headers)

    return jsonify(r.json())

# ================= CALLBACK =================
@app.route("/callback", methods=["POST"])
def callback():
    db = SessionLocal()

    data = request.json["Body"]["stkCallback"]

    if data["ResultCode"] == 0:
        items = data["CallbackMetadata"]["Item"]

        amount = next(i["Value"] for i in items if i["Name"] == "Amount")
        phone = str(next(i["Value"] for i in items if i["Name"] == "PhoneNumber"))
        receipt = next(i["Value"] for i in items if i["Name"] == "MpesaReceiptNumber")

        user = db.query(User).filter(User.phone == phone).first()

        if not user:
            user = User(phone=phone, balance=0)
            db.add(user)

        user.balance += amount

        tx = Transaction(
            phone=phone,
            amount=amount,
            type="deposit",
            status="PAID",
            receipt=receipt
        )

        db.add(tx)
        db.commit()

    return jsonify({"ResultCode": 0})

# ================= BALANCE =================
@app.route("/balance/<phone>")
def balance(phone):
    db = SessionLocal()
    user = db.query(User).filter(User.phone == format_phone(phone)).first()
    return jsonify({"balance": user.balance if user else 0})

# ================= SEND =================
@app.route("/send", methods=["POST"])
def send():
    db = SessionLocal()

    sender = format_phone(request.json["from"])
    receiver = format_phone(request.json["to"])
    amount = int(request.json["amount"])

    s = db.query(User).filter(User.phone == sender).first()
    r = db.query(User).filter(User.phone == receiver).first()

    if s.balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    s.balance -= amount

    if not r:
        r = User(phone=receiver, balance=0)
        db.add(r)

    r.balance += amount

    db.commit()

    return jsonify({"status": "SUCCESS"})

@app.route("/")
def home():
    return "REAL HopestonePay running"
