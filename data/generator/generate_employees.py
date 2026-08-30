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

employees = []

designations = [
    "Branch Manager",
    "Relationship Manager",
    "Cashier",
    "Loan Officer",
    "Operations Executive",
    "Customer Support Executive",
    "Credit Analyst"
]

for i in range(2001, 2051):   # 50 employees
    employees.append({
        "Employee_ID": i,
        "First_Name": fake.first_name(),
        "Last_Name": fake.last_name(),
        "Gender": random.choice(["Male","Female"]),
        "Designation": random.choice(designations),
        "Salary": random.randint(300000,1200000),
        "Branch_ID": random.randint(101,105)
    })

df = pd.DataFrame(employees)

df.to_csv("../employees.csv", index=False)

print("✅ employees.csv generated successfully!")