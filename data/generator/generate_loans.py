"""
Enterprise Banking Risk Analytics

Author: Manasvi Vats

Purpose:
Generate synthetic banking dataset.
"""
from faker import Faker
import pandas as pd
import random
from datetime import datetime, timedelta

fake = Faker("en_IN")

loan_types = [
    "Home Loan",
    "Car Loan",
    "Personal Loan",
    "Education Loan",
    "Business Loan"
]

loan_status = [
    "Active",
    "Closed",
    "Default"
]

records = []

loan_id = 700001

for i in range(1000):

    amount = random.randint(50000,5000000)

    months = random.choice([12,24,36,60,120,240])

    rate = round(random.uniform(7.5,15),2)

    emi = round(amount/months,2)

    start = fake.date_between("-5y","today")

    end = start + timedelta(days=months*30)

    records.append({

        "Loan_ID": loan_id,

       "Customer_ID": random.randint(1001,1180),

        "Loan_Type": random.choice(loan_types),

        "Loan_Amount": amount,

        "Interest_Rate": rate,

        "Loan_Term_Months": months,

        "Loan_Status": random.choice(loan_status),

        "EMI": emi,

        "Start_Date": start,

        "End_Date": end

    })

    loan_id += 1

df = pd.DataFrame(records)

df.to_csv("../loans.csv",index=False)

print("✅ loans.csv generated successfully!")