"""
Enterprise Banking Risk Analytics

Author: Manasvi Vats

Purpose:
Generate synthetic banking dataset.
"""
import pandas as pd
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker("en_IN")

transactions = []

transaction_types = [
    "UPI",
    "ATM",
    "NEFT",
    "RTGS",
    "IMPS",
    "Debit Card",
    "Credit Card"
]

merchants = [
    "Amazon",
    "Flipkart",
    "Swiggy",
    "Zomato",
    "Reliance",
    "DMart",
    "Uber",
    "IRCTC",
    "Paytm",
    "PhonePe"
]

cities = [
    "Delhi",
    "Mumbai",
    "Lucknow",
    "Bengaluru",
    "Hyderabad",
    "Kolkata",
    "Pune"
]

devices = [
    "Mobile",
    "Laptop",
    "ATM",
    "POS"
]

start_date = datetime(2026,1,1)

transaction_id = 900001

for i in range(10000):

    amount = random.randint(100,100000)

    fraud = "No"
    reason = "Normal Transaction"

    if random.random() < 0.03:

        fraud = "Yes"

        reason = random.choice([
            "High Amount",
            "Multiple Transactions",
            "Midnight Transaction",
            "Different City"
        ])

    transaction = {

        "Transaction_ID": transaction_id,

        "Account_ID": random.randint(500000001,500000180),

        "Transaction_Date":
        (start_date+timedelta(days=random.randint(0,365))).strftime("%Y-%m-%d"),

        "Transaction_Time":
        fake.time(),

        "Transaction_Type":
        random.choice(transaction_types),

        "Amount":
        amount,

        "Merchant_Name":
        random.choice(merchants),

        "City":
        random.choice(cities),

        "Device_Type":
        random.choice(devices),

        "Is_Fraud":
        fraud,

        "Fraud_Reason":
        reason

    }

    transactions.append(transaction)

    transaction_id += 1

df = pd.DataFrame(transactions)

df.to_csv("../transactions.csv",index=False)

print("✅ transactions.csv generated successfully!")