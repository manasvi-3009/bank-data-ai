"""
Enterprise Banking Risk Analytics

Author: Manasvi Vats

Purpose:
Generate synthetic banking dataset.
"""
import pandas as pd
import random

accounts = []

account_types = [
    "Savings",
    "Current",
    "Salary"
]

account_status = [
    "Active",
    "Inactive"
]

account_number = 500000001

for customer_id in range(1001, 1101):      # 100 customers

    total_accounts = random.randint(1, 2)

    for i in range(total_accounts):

        accounts.append({

            "Account_ID": account_number,

            "Customer_ID": customer_id,

            "Account_Type": random.choice(account_types),

            "Balance": random.randint(5000, 1000000),

            "Account_Status": random.choice(account_status),

            "Branch_ID": random.randint(101,105)

        })

        account_number += 1

df = pd.DataFrame(accounts)

df.to_csv("../accounts.csv", index=False)

print("✅ accounts.csv generated successfully!")