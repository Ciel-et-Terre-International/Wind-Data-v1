import tkinter as tk
from tkinter import simpledialog
from datetime import datetime

def get_date_range_from_user():
    root = tk.Tk()
    root.withdraw()  # Hide main window

    # Ask for start and end dates
    start_str = simpledialog.askstring("Start date", "Enter the start date (YYYY-MM-DD):")
    end_str = simpledialog.askstring("End date", "Enter the end date (YYYY-MM-DD):")

    try:
        # Validate formats
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()

        if start_date >= end_date:
            raise ValueError("Start date must be earlier than end date.")

        return str(start_date), str(end_date)

    except Exception as e:
        print(f"Error with dates: {e}")
        return None, None
