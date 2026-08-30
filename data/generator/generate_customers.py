"""
Enterprise Banking Risk Analytics

Author: Manasvi Vats

Purpose:
Generate synthetic banking dataset.
"""
import pandas as pd
from faker import Faker
import random

fake = Faker("en_IN")

customers = []

for i in range(1001, 1101):
    customers.append({
        "Customer_ID": i,
        "First_Name": fake.first_name(),
        "Last_Name": fake.last_name(),
        "Gender": random.choice(["Male", "Female"]),
        "Annual_Income": random.randint(300000, 2500000),
        "Risk_Score": random.randint(1, 100),
        "KYC_Status": random.choice(["Complete", "Pending", "Expired"])
    })

df = pd.DataFrame(customers)

df.to_csv("../customers.csv", index=False)

print("✅ customers.csv generated successfully!")