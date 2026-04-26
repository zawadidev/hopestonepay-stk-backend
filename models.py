from sqlalchemy import Column, Integer, String, Float
from db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    phone = Column(String, unique=True)
    balance = Column(Float, default=0)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    phone = Column(String)
    amount = Column(Float)
    type = Column(String)
    status = Column(String)
    receipt = Column(String)
