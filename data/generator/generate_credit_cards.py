"""
Enterprise Banking Risk Analytics

Author: Manasvi Vats

Purpose:
Generate synthetic banking dataset.
"""
from faker import Faker
import pandas as pd
import random
from datetime import timedelta

fake = Faker("en_IN")

cards = []

card_types = [
    "Classic",
    "Gold",
    "Platinum",
    "Signature"
]

networks = [
    "Visa",
    "Mastercard",
    "RuPay"
]

status = [
    "Active",
    "Blocked",
    "Expired"
]

card_id = 800001

for i in range(1000):

    limit = random.randint(50000,1000000)

    outstanding = random.randint(0,limit)

    issue = fake.date_between("-5y","today")

    expiry = issue + timedelta(days=365*5)

    cards.append({

        "Card_ID":card_id,

        "Customer_ID": random.randint(1001,1180),

        "Card_Type":random.choice(card_types),

        "Card_Network":random.choice(networks),

        "Credit_Limit":limit,

        "Outstanding_Balance":outstanding,

        "Card_Status":random.choice(status),

        "Issue_Date":issue,

        "Expiry_Date":expiry

    })

    card_id += 1

df = pd.DataFrame(cards)

df.to_csv("../credit_cards.csv",index=False)

print("✅ credit_cards.csv generated successfully!")