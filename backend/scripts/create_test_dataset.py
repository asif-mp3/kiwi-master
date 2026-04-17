"""
Create a realistic test dataset for Thara AI plug-and-play testing.
Generates an Excel file with multiple sheets simulating real business data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

def create_test_dataset():
    """Create a realistic multi-sheet Excel dataset for testing."""

    # Set seed for reproducibility
    np.random.seed(42)
    random.seed(42)

    # =====================
    # SHEET 1: Daily Sales
    # =====================

    # Generate 6 months of daily data (Aug 2024 - Jan 2025)
    start_date = datetime(2024, 8, 1)
    dates = [start_date + timedelta(days=i) for i in range(184)]

    branches = ['Chennai', 'Mumbai', 'Bangalore', 'Hyderabad', 'Coimbatore']
    categories = ['Saree', 'Dhoti', 'Kurta', 'Salwar Kameez', 'Shirt']
    payment_modes = ['UPI', 'Cash', 'Credit Card', 'Debit Card', 'Net Banking']
    states = ['Tamil Nadu', 'Maharashtra', 'Karnataka', 'Andhra Pradesh', 'Kerala']

    # Generate ~1000 sales records
    n_records = 1000

    sales_data = []
    for i in range(n_records):
        date = random.choice(dates)
        branch = random.choice(branches)
        category = random.choice(categories)

        # Price varies by category
        base_prices = {
            'Saree': 2500, 'Dhoti': 800, 'Kurta': 1500,
            'Salwar Kameez': 2000, 'Shirt': 1200
        }

        quantity = random.randint(1, 5)
        unit_price = base_prices[category] * (1 + random.uniform(-0.3, 0.3))
        amount = round(unit_price * quantity, 2)
        cost = round(amount * random.uniform(0.5, 0.7), 2)
        profit = round(amount - cost, 2)

        # State based on branch
        branch_state = {
            'Chennai': 'Tamil Nadu', 'Mumbai': 'Maharashtra',
            'Bangalore': 'Karnataka', 'Hyderabad': 'Andhra Pradesh',
            'Coimbatore': 'Tamil Nadu'
        }

        sales_data.append({
            'Transaction_ID': f'TXN{10000 + i}',
            'Date': date.strftime('%Y-%m-%d'),
            'Branch': branch,
            'State': branch_state[branch],
            'Category': category,
            'SKU_Name': f'{category}_{random.randint(100, 999)}',
            'Quantity': quantity,
            'Unit_Price': round(unit_price, 2),
            'Amount': amount,
            'Cost_Price': cost,
            'Profit': profit,
            'Payment_Mode': random.choice(payment_modes),
            'Customer_ID': f'CUST{random.randint(1000, 9999)}'
        })

    df_sales = pd.DataFrame(sales_data)

    # =====================
    # SHEET 2: Attendance
    # =====================

    employees = [
        ('E001', 'Rajesh Kumar', 'Chennai', 'Sales'),
        ('E002', 'Sneha Patel', 'Mumbai', 'Sales'),
        ('E003', 'Amit Singh', 'Bangalore', 'Operations'),
        ('E004', 'Priya Sharma', 'Hyderabad', 'Sales'),
        ('E005', 'Vikram Reddy', 'Coimbatore', 'Sales'),
        ('E006', 'Lakshmi Iyer', 'Chennai', 'Operations'),
        ('E007', 'Mohammed Ali', 'Mumbai', 'Sales'),
        ('E008', 'Kavitha Nair', 'Bangalore', 'HR'),
        ('E009', 'Suresh Menon', 'Hyderabad', 'Finance'),
        ('E010', 'Deepa Krishnan', 'Chennai', 'Sales'),
    ]

    # Generate 3 months of attendance (Nov 2024 - Jan 2025)
    attendance_start = datetime(2024, 11, 1)
    attendance_dates = [attendance_start + timedelta(days=i) for i in range(92)]

    attendance_data = []
    for date in attendance_dates:
        # Skip Sundays
        if date.weekday() == 6:
            continue

        for emp_id, name, branch, dept in employees:
            # 90% attendance rate
            if random.random() < 0.9:
                hours = round(random.uniform(7.5, 10), 1)
                status = 'Present'
            else:
                hours = 0
                status = 'Absent'

            attendance_data.append({
                'Date': date.strftime('%Y-%m-%d'),
                'Employee_ID': emp_id,
                'Employee_Name': name,
                'Department': dept,
                'Hours_Worked': hours,
                'Status': status
            })

    df_attendance = pd.DataFrame(attendance_data)

    # =====================
    # SHEET 3: Branch Summary
    # =====================

    branch_summary = []
    for branch in branches:
        branch_state = {
            'Chennai': 'Tamil Nadu', 'Mumbai': 'Maharashtra',
            'Bangalore': 'Karnataka', 'Hyderabad': 'Andhra Pradesh',
            'Coimbatore': 'Tamil Nadu'
        }

        branch_data = df_sales[df_sales['Branch'] == branch]

        branch_summary.append({
            'Branch': branch,
            'State': branch_state[branch],
            'Total_Transactions': len(branch_data),
            'Total_Revenue': round(branch_data['Amount'].sum(), 2),
            'Total_Profit': round(branch_data['Profit'].sum(), 2),
            'Avg_Transaction_Value': round(branch_data['Amount'].mean(), 2),
            'Top_Category': branch_data.groupby('Category')['Amount'].sum().idxmax(),
            'Employee_Count': 2
        })

    df_branch = pd.DataFrame(branch_summary)

    # =====================
    # SHEET 4: Monthly Summary
    # =====================

    df_sales['Month'] = pd.to_datetime(df_sales['Date']).dt.to_period('M')

    monthly_summary = df_sales.groupby('Month').agg({
        'Transaction_ID': 'count',
        'Amount': 'sum',
        'Profit': 'sum',
        'Quantity': 'sum'
    }).reset_index()

    monthly_summary.columns = ['Month', 'Transactions', 'Revenue', 'Profit', 'Quantity']
    monthly_summary['Month'] = monthly_summary['Month'].astype(str)

    df_sales = df_sales.drop('Month', axis=1)

    # =====================
    # SAVE TO EXCEL
    # =====================

    output_path = os.path.join(os.path.expanduser("~"), "Downloads", "thara_test_dataset.xlsx")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_sales.to_excel(writer, sheet_name='Daily_Sales', index=False)
        df_attendance.to_excel(writer, sheet_name='Attendance', index=False)
        df_branch.to_excel(writer, sheet_name='Branch_Summary', index=False)
        monthly_summary.to_excel(writer, sheet_name='Monthly_Summary', index=False)

    print(f"\n{'='*60}")
    print("TEST DATASET CREATED SUCCESSFULLY!")
    print(f"{'='*60}")
    print(f"\nFile: {output_path}")
    print(f"\nSheets created:")
    print(f"  1. Daily_Sales    : {len(df_sales)} records")
    print(f"     Columns: {list(df_sales.columns)}")
    print(f"\n  2. Attendance     : {len(df_attendance)} records")
    print(f"     Columns: {list(df_attendance.columns)}")
    print(f"\n  3. Branch_Summary : {len(df_branch)} records")
    print(f"     Columns: {list(df_branch.columns)}")
    print(f"\n  4. Monthly_Summary: {len(monthly_summary)} records")
    print(f"     Columns: {list(monthly_summary.columns)}")

    print(f"\n{'='*60}")
    print("SAMPLE DATA PREVIEW")
    print(f"{'='*60}")

    print("\nDaily_Sales (first 5 rows):")
    print(df_sales.head().to_string(index=False))

    print("\nAttendance (first 5 rows):")
    print(df_attendance.head().to_string(index=False))

    print("\nBranch_Summary:")
    print(df_branch.to_string(index=False))

    print("\nMonthly_Summary:")
    print(monthly_summary.to_string(index=False))

    return output_path


if __name__ == "__main__":
    create_test_dataset()
