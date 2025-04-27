import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np

class EnhancedBudgetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Budget Tracker")
        self.root.geometry("1200x800")
        
        self.init_database()
        self.create_widgets()
        self.setup_keyboard_shortcuts()
        
    def setup_keyboard_shortcuts(self):
        self.root.bind('<Delete>', lambda event: self.delete_selected_transaction())
        
    def init_database(self):
        self.conn = sqlite3.connect('budget.db')
        self.cursor = self.conn.cursor()
        
        # Create tables
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                amount REAL NOT NULL,
                category_id INTEGER,
                description TEXT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories (id)
            )
        ''')
        
        # Insert default categories
        default_expense_categories = ['Food', 'Transportation', 'Housing', 'Utilities', 'Entertainment']
        default_income_categories = ['Salary', 'Freelance', 'Investments', 'Other Income']
        
        for category in default_expense_categories:
            try:
                self.cursor.execute('INSERT INTO categories (name, type) VALUES (?, ?)', 
                                  (category, 'expense'))
            except sqlite3.IntegrityError:
                pass
                
        for category in default_income_categories:
            try:
                self.cursor.execute('INSERT INTO categories (name, type) VALUES (?, ?)', 
                                  (category, 'income'))
            except sqlite3.IntegrityError:
                pass
        
        self.conn.commit()

    def create_widgets(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(pady=10, expand=True, fill='both')

        # Add Transaction tab
        self.add_transaction_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.add_transaction_frame, text="Add Transaction")
        self.create_add_transaction_widgets()

        # View Transactions tab
        self.view_transactions_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.view_transactions_frame, text="View Transactions")
        self.create_view_transactions_widgets()

        # Analytics tab
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text="Analytics")
        self.create_analytics_widgets()

        # Forecasting tab
        self.forecasting_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.forecasting_frame, text="Forecasting")
        self.create_forecasting_widgets()

    def create_add_transaction_widgets(self):
        # Transaction type selection
        ttk.Label(self.add_transaction_frame, text="Type:").grid(row=0, column=0, padx=5, pady=5)
        self.transaction_type_var = tk.StringVar(value="expense")
        ttk.Radiobutton(self.add_transaction_frame, text="Expense", variable=self.transaction_type_var, 
                       value="expense", command=self.update_categories).grid(row=0, column=1)
        ttk.Radiobutton(self.add_transaction_frame, text="Income", variable=self.transaction_type_var, 
                       value="income", command=self.update_categories).grid(row=0, column=2)

        # Amount entry
        ttk.Label(self.add_transaction_frame, text="Amount:").grid(row=1, column=0, padx=5, pady=5)
        self.amount_var = tk.StringVar()
        self.amount_entry = ttk.Entry(self.add_transaction_frame, textvariable=self.amount_var)
        self.amount_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5)

        # Category dropdown
        ttk.Label(self.add_transaction_frame, text="Category:").grid(row=2, column=0, padx=5, pady=5)
        self.category_var = tk.StringVar()
        self.category_dropdown = ttk.Combobox(self.add_transaction_frame, textvariable=self.category_var)
        self.category_dropdown.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        self.update_categories()

        # Description entry
        ttk.Label(self.add_transaction_frame, text="Description:").grid(row=3, column=0, padx=5, pady=5)
        self.description_var = tk.StringVar()
        self.description_entry = ttk.Entry(self.add_transaction_frame, textvariable=self.description_var)
        self.description_entry.grid(row=3, column=1, columnspan=2, padx=5, pady=5)

        # Submit button
        self.submit_button = ttk.Button(self.add_transaction_frame, 
                                      text="Add Transaction",
                                      command=self.add_transaction)
        self.submit_button.grid(row=4, column=0, columnspan=3, pady=20)

    def create_view_transactions_widgets(self):
        # Create treeview
        self.transaction_tree = ttk.Treeview(self.view_transactions_frame, 
                                        columns=("Date", "Type", "Amount", "Category", "Description"),
                                        show="headings",
                                        selectmode="extended")  # Enable multiple selection
        
        # Define headings
        self.transaction_tree.heading("Date", text="Date")
        self.transaction_tree.heading("Type", text="Type")
        self.transaction_tree.heading("Amount", text="Amount")
        self.transaction_tree.heading("Category", text="Category")
        self.transaction_tree.heading("Description", text="Description")

        # Set column widths
        self.transaction_tree.column("Date", width=150)
        self.transaction_tree.column("Type", width=100)
        self.transaction_tree.column("Amount", width=100)
        self.transaction_tree.column("Category", width=150)
        self.transaction_tree.column("Description", width=200)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.view_transactions_frame, 
                                orient="vertical", 
                                command=self.transaction_tree.yview)
        self.transaction_tree.configure(yscrollcommand=scrollbar.set)

        # Pack widgets
        self.transaction_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Configure grid weights
        self.view_transactions_frame.grid_columnconfigure(0, weight=1)
        self.view_transactions_frame.grid_rowconfigure(0, weight=1)

        # Refresh button
        refresh_button = ttk.Button(self.view_transactions_frame,
                                  text="Refresh",
                                  command=self.refresh_transactions)
        refresh_button.grid(row=1, column=0, pady=5)

        # Add delete buttons
        self.create_delete_buttons()

        # Load transactions
        self.refresh_transactions()
    def create_delete_buttons(self):
        # Create a frame for delete buttons
        delete_frame = ttk.Frame(self.view_transactions_frame)
        delete_frame.grid(row=2, column=0, pady=5)

        # Delete selected button
        delete_selected_btn = ttk.Button(delete_frame,
                                       text="Delete Selected",
                                       command=self.delete_selected_transaction)
        delete_selected_btn.pack(side=tk.LEFT, padx=5)

        # Delete all button
        delete_all_btn = ttk.Button(delete_frame,
                                   text="Delete All",
                                   command=self.delete_all_transactions)
        delete_all_btn.pack(side=tk.LEFT, padx=5)

    def create_analytics_widgets(self):
        # Create frames for charts
        self.pie_chart_frame = ttk.Frame(self.analytics_frame)
        self.pie_chart_frame.grid(row=0, column=0, padx=10, pady=10)

        self.trend_chart_frame = ttk.Frame(self.analytics_frame)
        self.trend_chart_frame.grid(row=0, column=1, padx=10, pady=10)

        self.update_charts()

        # Add refresh button
        refresh_button = ttk.Button(self.analytics_frame, text="Refresh Charts", 
                                  command=self.update_charts)
        refresh_button.grid(row=1, column=0, columnspan=2, pady=10)

    def create_forecasting_widgets(self):
        # Forecasting period selection
        ttk.Label(self.forecasting_frame, text="Forecast Period (months):").grid(row=0, column=0, padx=5, pady=5)
        self.forecast_period_var = tk.StringVar(value="3")
        forecast_period_entry = ttk.Entry(self.forecasting_frame, textvariable=self.forecast_period_var)
        forecast_period_entry.grid(row=0, column=1, padx=5, pady=5)

        # Generate forecast button
        forecast_button = ttk.Button(self.forecasting_frame, text="Generate Forecast", 
                                   command=self.generate_forecast)
        forecast_button.grid(row=1, column=0, columnspan=2, pady=10)

        # Frame for forecast chart
        self.forecast_chart_frame = ttk.Frame(self.forecasting_frame)
        self.forecast_chart_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    def delete_selected_transaction(self):
        selected_items = self.transaction_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select transaction(s) to delete")
            return

        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete {len(selected_items)} transaction(s)?"):
            try:
                for item in selected_items:
                    # Get the date and amount of the transaction to identify it
                    values = self.transaction_tree.item(item)['values']
                    date = values[0]
                    amount = float(values[2])
                    
                    # Delete from database
                    self.cursor.execute('''
                        DELETE FROM transactions 
                        WHERE date = ? AND amount = ?
                    ''', (date, amount))
                
                self.conn.commit()
                messagebox.showinfo("Success", f"{len(selected_items)} transaction(s) deleted successfully")
                self.refresh_transactions()
                self.update_charts()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
                self.conn.rollback()

    def delete_all_transactions(self):
        if messagebox.askyesno("Confirm Delete All", 
                              "Are you sure you want to delete ALL transactions? This cannot be undone!"):
            try:
                self.cursor.execute("DELETE FROM transactions")
                self.conn.commit()
                messagebox.showinfo("Success", "All transactions deleted successfully")
                self.refresh_transactions()
                self.update_charts()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
                self.conn.rollback()

    def update_categories(self):
        transaction_type = self.transaction_type_var.get()
        self.cursor.execute('SELECT name FROM categories WHERE type = ?', (transaction_type,))
        categories = [category[0] for category in self.cursor.fetchall()]
        self.category_dropdown['values'] = categories
        self.category_var.set('')

    def add_transaction(self):
        try:
            amount = float(self.amount_var.get())
            category = self.category_var.get()
            description = self.description_var.get()
            transaction_type = self.transaction_type_var.get()
            
            if not category:
                messagebox.showerror("Error", "Please select a category")
                return

            # Get category_id
            self.cursor.execute('SELECT id FROM categories WHERE name = ?', (category,))
            category_id = self.cursor.fetchone()[0]

            # Insert transaction
            self.cursor.execute('''
                INSERT INTO transactions (amount, category_id, description, date, type)
                VALUES (?, ?, ?, ?, ?)
            ''', (amount, category_id, description, 
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                 transaction_type))
            
            self.conn.commit()
            
            # Clear entries
            self.amount_var.set("")
            self.category_var.set("")
            self.description_var.set("")
            
            messagebox.showinfo("Success", "Transaction added successfully!")
            self.refresh_transactions()
            self.update_charts()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid amount")

    def refresh_transactions(self):
        # Clear current items
        for item in self.transaction_tree.get_children():
            self.transaction_tree.delete(item)

        # Fetch and display transactions
        self.cursor.execute('''
            SELECT transactions.date, transactions.type, transactions.amount, 
                   categories.name, transactions.description
            FROM transactions
            JOIN categories ON transactions.category_id = categories.id
            ORDER BY transactions.date DESC
        ''')
        
        for transaction in self.cursor.fetchall():
            # Format amount with 2 decimal places
            formatted_transaction = list(transaction)
            formatted_transaction[2] = f"{float(transaction[2]):.2f}"
            self.transaction_tree.insert("", "end", values=formatted_transaction)

    def update_charts(self):
        # Clear existing charts
        for widget in self.pie_chart_frame.winfo_children():
            widget.destroy()
        for widget in self.trend_chart_frame.winfo_children():
            widget.destroy()

        # Create pie chart
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        self.cursor.execute('''
            SELECT categories.name, SUM(transactions.amount)
            FROM transactions
            JOIN categories ON transactions.category_id = categories.id
            WHERE transactions.type = 'expense'
            GROUP BY categories.name
        ''')
        expenses_data = self.cursor.fetchall()
        
        if expenses_data:
            labels = [row[0] for row in expenses_data]
            sizes = [row[1] for row in expenses_data]
            ax1.pie(sizes, labels=labels, autopct='%1.1f%%')
            ax1.set_title('Expense Distribution')

        # Embed pie chart
        canvas1 = FigureCanvasTkAgg(fig1, self.pie_chart_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack()

        # Create trend chart
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        self.cursor.execute('''
            SELECT date, type, SUM(amount)
            FROM transactions
            GROUP BY date(date), type
            ORDER BY date
        ''')
        trend_data = self.cursor.fetchall()
        
        if trend_data:
            df = pd.DataFrame(trend_data, columns=['date', 'type', 'amount'])
            df['date'] = pd.to_datetime(df['date'])
            
            for t_type in ['expense', 'income']:
                type_data = df[df['type'] == t_type]
                if not type_data.empty:
                    ax2.plot(type_data['date'], type_data['amount'], 
                            label=t_type.capitalize())

            ax2.set_title('Income vs Expenses Over Time')
            ax2.legend()
            plt.xticks(rotation=45)

        # Embed trend chart
        canvas2 = FigureCanvasTkAgg(fig2, self.trend_chart_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack()

    def generate_forecast(self):
        try:
            forecast_months = int(self.forecast_period_var.get())
            
            # Clear existing forecast chart
            for widget in self.forecast_chart_frame.winfo_children():
                widget.destroy()

            # Get historical data
            self.cursor.execute('''
                SELECT date, type, SUM(amount)
                FROM transactions
                GROUP BY date(date), type
                ORDER BY date
            ''')
            historical_data = self.cursor.fetchall()
            
            if historical_data:
                df = pd.DataFrame(historical_data, columns=['date', 'type', 'amount'])
                df['date'] = pd.to_datetime(df['date'])
                df['days_from_start'] = (df['date'] - df['date'].min()).dt.days

                # Create forecast chart
                fig, ax = plt.subplots(figsize=(10, 6))

                for t_type in ['expense', 'income']:
                    type_data = df[df['type'] == t_type]
                    if not type_data.empty:
                        # Prepare data for linear regression
                        X = type_data['days_from_start'].values.reshape(-1, 1)
                        y = type_data['amount'].values

                        # Fit linear regression
                        model = LinearRegression()
                        model.fit(X, y)

                        # Generate future dates
                        last_date = df['date'].max()
                        future_dates = pd.date_range(
                            start=last_date, 
                            periods=forecast_months * 30, 
                            freq='D'
                        )
                        future_days = (future_dates - df['date'].min()).days.values.reshape(-1, 1)

                        # Generate predictions
                        predictions = model.predict(future_days)

                        # Plot historical data and predictions
                        ax.plot(type_data['date'], type_data['amount'], 
                               label=f'Historical {t_type}')
                        ax.plot(future_dates, predictions, 
                               '--', label=f'Predicted {t_type}')

                ax.set_title('Financial Forecast')
                ax.legend()
                plt.xticks(rotation=45)

                # Embed forecast chart
                canvas = FigureCanvasTkAgg(fig, self.forecast_chart_frame)
                canvas.draw()
                canvas.get_tk_widget().pack()

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid forecast period")

if __name__ == "__main__":
    root = tk.Tk()
    app = EnhancedBudgetApp(root)
    root.mainloop()
