import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
import os

class OPTIGRAL_APP:
    def __init__(self, root):
        self.root = root
        self.root.title("OPTIGRAL Energy Analysis")
        
        # Set theme colors
        self.bg_color = "#f0f0f0"
        self.accent_color = "#007acc"
        self.text_color = "#333333"
        
        # Configure root window
        self.root.configure(bg=self.bg_color)
        
        # Initialize data structures
        self.dataset = {}
        self.date_filter = {}
        self.list_items = []
        self.win_height = 0
        self.win_width = 50
        self.zoomed_in_window = None
        self.slider_xpts = []
        self.slider_ypts = []
        self.reconstruct_tab = None

        # Configure style
        self.style = ttk.Style()
        self.style.configure('TFrame', background=self.bg_color)
        self.style.configure('TLabel', background=self.bg_color, foreground=self.text_color)
        self.style.configure('TButton', background=self.accent_color, foreground='white')
        self.style.configure('TLabelframe', background=self.bg_color)
        self.style.configure('TLabelframe.Label', background=self.bg_color, foreground=self.text_color)

        # Create main UI components
        self.create_ui()

    def create_ui(self):
        # Create main frames with padding and styling
        self.control_frame = ttk.Frame(self.root, style='TFrame', padding="10")
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.tab_frame = ttk.Frame(self.root, style='TFrame', padding="10")
        self.tab_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.tab_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.energy_consumption_tab = ttk.Frame(self.notebook)
        self.energy_analysis_tab = ttk.Frame(self.notebook)
        self.load_reconstruction_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.energy_consumption_tab, text='Energy Consumption')
        self.notebook.add(self.energy_analysis_tab, text='Energy Analysis')
        self.notebook.add(self.load_reconstruction_tab, text='Load Reconstruction')

        # Add control buttons with improved styling
        title_label = ttk.Label(self.control_frame, 
                              text="OPTIGRAL - Copyright (c)",
                              font=('Helvetica', 16, 'bold'),
                              foreground=self.accent_color)
        title_label.pack(pady=10)

        import_btn = ttk.Button(self.control_frame, 
                              text="Import Energy Consumption Data",
                              command=self.import_energy_consumption_data,
                              style='TButton',
                              padding=(10, 5))
        import_btn.pack(pady=10, fill=tk.X)

        # Create data filtering panel
        filter_frame = ttk.LabelFrame(self.control_frame, text="Data Filtering")
        filter_frame.pack(fill=tk.X, pady=10)

        # Customer dropdown
        ttk.Label(filter_frame, text="Customer:").pack()
        self.customer_dropdown = ttk.Combobox(filter_frame, state='readonly')
        self.customer_dropdown.pack(pady=5)

        # Date pickers
        ttk.Label(filter_frame, text="Start Date:").pack()
        self.start_date_entry = ttk.Entry(filter_frame)
        self.start_date_entry.pack(pady=5)

        ttk.Label(filter_frame, text="End Date:").pack()
        self.end_date_entry = ttk.Entry(filter_frame)
        self.end_date_entry.pack(pady=5)

        # Filter buttons
        ttk.Button(filter_frame, text="Apply Filter",
                  command=self.apply_filter).pack(pady=5)
        ttk.Button(filter_frame, text="Reset",
                  command=self.reset_filter).pack(pady=5)

    def import_energy_consumption_data(self):
        filename = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        
        if filename:
            try:
                # Read CSV file
                data = pd.read_csv(filename)
                
                # Find next available customer number
                customer_nums = [int(val.split()[-1]) for val in (self.customer_dropdown['values'] or [])]
                next_customer_num = 1 if not customer_nums else max(customer_nums) + 1
                
                # Process the data with the correct customer number
                self.process_energy_data(data, next_customer_num)
                
                # Update customer dropdown
                new_values = list(self.customer_dropdown['values'] or [])
                new_values.append(f"Customer {next_customer_num}")
                self.customer_dropdown['values'] = new_values
                self.customer_dropdown.set(f"Customer {next_customer_num}")
                
                # Plot initial data
                self.plot_energy_consumption()
                
            except Exception as e:
                print(f"Import error details: {str(e)}")  # Debug output
                tk.messagebox.showerror("Error", f"Error importing data: {str(e)}")

    def process_energy_data(self, data, customer_num):
        try:
            # Print data info for debugging
            print("CSV columns:", data.columns.tolist())
            print("First few rows:")
            print(data.head())
            
            # Use the provided customer number
            print(f"Processing data for customer {customer_num}")  # Debug output
            
            # Initialize processed data
            processed_data = data.copy()
            
            # Handle different possible column names
            datetime_cols = {
                'start': ['Start', 'start', 'START', 'StartTime', 'start_time', 'timestamp'],
                'end': ['End', 'end', 'END', 'EndTime', 'end_time']
            }
            
            # First, get the actual column names from the data
            print("Original column names:", [f"'{col}'" for col in processed_data.columns])
            
            # Create a mapping of original column names to cleaned names
            column_mapping = {col: col.strip() for col in processed_data.columns}
            
            # Rename columns
            processed_data = processed_data.rename(columns=column_mapping)
            print("Cleaned column names:", processed_data.columns.tolist())
            
            # Find start column (looking for 'Start' after cleaning)
            start_col = 'Start'  # We know it's 'Start' from the CSV output
            if start_col not in processed_data.columns:
                raise ValueError(f"Could not find start time column. Available columns: {processed_data.columns.tolist()}")
            
            # Find end column (looking for 'End' after cleaning)
            end_col = 'End'  # We know it's 'End' from the CSV output
            if end_col not in processed_data.columns:
                raise ValueError(f"Could not find end time column. Available columns: {processed_data.columns.tolist()}")
            
            # Convert datetime columns with UTC handling
            processed_data['Start'] = pd.to_datetime(processed_data[start_col], utc=True)
            processed_data['End'] = pd.to_datetime(processed_data[end_col], utc=True)
            
            # Convert to local time
            processed_data['Start'] = processed_data['Start'].dt.tz_localize(None)
            processed_data['End'] = processed_data['End'].dt.tz_localize(None)
            
            # Split datetime into date and time
            processed_data['Start Date'] = processed_data['Start'].dt.strftime('%Y-%m-%d')
            processed_data['Start Time'] = processed_data['Start'].dt.strftime('%H:%M:%S')
            processed_data['End Date'] = processed_data['End'].dt.strftime('%Y-%m-%d')
            processed_data['End Time'] = processed_data['End'].dt.strftime('%H:%M:%S')
            
            # Handle consumption column
            consumption_col = 'Consumption (kWh)'  # The exact column name from the CSV
            if consumption_col not in processed_data.columns:
                # Try alternative names if needed
                consumption_cols = ['consumption', 'CONSUMPTION', 'Energy', 'energy', 'value', 'Value']
                alt_consumption_col = next((col for col in processed_data.columns 
                                         if col in consumption_cols), None)
                if alt_consumption_col:
                    consumption_col = alt_consumption_col
                else:
                    # If no consumption column found, create dummy data
                    processed_data['Consumption'] = np.random.rand(len(processed_data)) * 10
                    messagebox.showwarning("Warning", 
                                         "No consumption data found. Using random data for demonstration.")
                    consumption_col = 'Consumption'

            # If we found a consumption column, copy it to standardized name
            if consumption_col != 'Consumption':
                processed_data['Consumption'] = processed_data[consumption_col]

            print("Using consumption data from column:", consumption_col)
            
            # Store in dataset
            self.dataset[f'customer_{customer_num}'] = {
                'EnergyConsumptionData': processed_data,
                'date_filter': {
                    'startIndex': 0,
                    'endIndex': len(processed_data)
                }
            }
            
        except Exception as e:
            print(f"Error processing data: {str(e)}")
            raise ValueError(f"Error processing data: {str(e)}")

    def plot_energy_consumption(self):
        if not self.dataset:
            return
            
        customer = self.customer_dropdown.get()
        if not customer:
            return
            
        customer_num = int(customer.split()[-1])
        data = self.dataset[f'customer_{customer_num}']['EnergyConsumptionData']
        
        # Clear previous plot
        for widget in self.energy_consumption_tab.winfo_children():
            widget.destroy()
            
        # Create new plot
        fig, ax = plt.subplots(figsize=(10, 6))
        # Create datetime index for plotting
        dates = pd.to_datetime(data['Start'])
        ax.plot(dates, data['Consumption'])
        
        # Format x-axis
        plt.gcf().autofmt_xdate()  # Rotate and align the tick labels
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        ax.set_xlabel('Time')
        ax.set_ylabel('Energy Consumption (kWh)')
        ax.set_title('Energy Consumption Over Time')
        
        # Embed plot in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.energy_consumption_tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def apply_filter(self):
        try:
            start_date = datetime.strptime(self.start_date_entry.get(), '%Y-%m-%d')
            end_date = datetime.strptime(self.end_date_entry.get(), '%Y-%m-%d')
            
            customer = self.customer_dropdown.get()
            if not customer:
                return
                
            customer_num = int(customer.split()[-1])
            
            # Apply date filter
            self.dataset[f'customer_{customer_num}']['date_filter'] = {
                'start': start_date,
                'end': end_date
            }
            
            # Update plots
            self.plot_energy_consumption()
            
        except ValueError as e:
            tk.messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")

    def reset_filter(self):
        customer = self.customer_dropdown.get()
        if not customer:
            return
            
        customer_num = int(customer.split()[-1])
        
        # Reset filter
        data = self.dataset[f'customer_{customer_num}']['EnergyConsumptionData']
        self.dataset[f'customer_{customer_num}']['date_filter'] = {
            'startIndex': 0,
            'endIndex': len(data)
        }
        
        # Clear date entries
        self.start_date_entry.delete(0, tk.END)
        self.end_date_entry.delete(0, tk.END)
        
        # Update plots
        self.plot_energy_consumption()

def main():
    try:
        print("Starting OPTIGRAL Energy Analysis application...")
        print("Initializing Tkinter...")
        root = tk.Tk()
        print("Setting window properties...")
        root.title("OPTIGRAL Energy Analysis")
        root.geometry("1200x800")
        print("Creating application instance...")
        app = OPTIGRAL_APP(root)
        print("Starting main loop...")
        root.mainloop()
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print("Traceback:")
        traceback.print_exc()
        try:
            messagebox.showerror("Error", f"Application error: {str(e)}\n\nCheck console for details.")
        except:
            pass
        raise

if __name__ == "__main__":
    main()
