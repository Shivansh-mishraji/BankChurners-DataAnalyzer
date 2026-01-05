# -*- coding: utf-8 -*-
"""
Bank Churner Analytics - Improved Version
Advanced data analysis and visualization tool for credit card customer data
Author: [Your Name]
Version: 2.0
Last Updated: January 2026
"""

import pandas as pd
import numpy as np
import time
import logging
import os
from pathlib import Path
from typing import Optional, Tuple, List
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import sqlalchemy
from sqlalchemy import create_engine
import json

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Create config dictionary (replace with config file in production)
CONFIG = {
    "data_dir": Path("./data"),
    "backup_dir": Path("./backup"),
    "csv_filename": "C:\\Users\\91727\\Desktop\\BankChurners-DataAnalyzer\\dataset.csv",
    "db_config": {
        "user": "root",
        "password": "",
        "host": "localhost",
        "port": 3306,
        "database": "bank_analytics"
    },
    "pagination_size": 50,
    "log_level": logging.INFO
}

# Create necessary directories
CONFIG["data_dir"].mkdir(exist_ok=True)
CONFIG["backup_dir"].mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=CONFIG["log_level"],
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG["backup_dir"] / "app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA VALIDATION & CONSTANTS
# ============================================================================

VALID_CARD_TYPES = {'Premium', 'Standard', 'Gold', 'Platinum'}
VALID_CARD_CATEGORIES = {'Blue', 'Silver', 'Gold', 'Platinum'}
VALID_EDUCATION_LEVELS = {'High School', 'Graduate', 'Uneducated', 'Unknown', 'Post-Graduate'}
VALID_MARITAL_STATUSES = {'Single', 'Married', 'Divorced', 'Unknown'}
VALID_INCOME_CATEGORIES = {'Less than $40K', '$40K - $60K', '$60K - $80K', '$80K - $120K', '$120K+'}
VALID_GENDERS = {'M', 'F'}
VALID_GEOGRAPHIES = {'USA', 'Canada', 'UK'}

AGE_RANGE = (18, 100)
CREDIT_LIMIT_RANGE = (1000, 50000)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clear_screen() -> None:
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def press_key_to_continue() -> None:
    """Wait for user to press Enter."""
    input('\n\nPress Enter to continue...')

def slow_print(message: str, delay: float = 0.002) -> None:
    """Print message with typewriter effect."""
    for char in message:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def load_data(filepath: Optional[Path] = None) -> pd.DataFrame:
    """
    Load CSV data with error handling and caching.
    
    Args:
        filepath: Path to CSV file. Uses default if None.
        
    Returns:
        DataFrame with loaded data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        pd.errors.ParserError: If CSV is malformed
    """
    if filepath is None:
        filepath = CONFIG["data_dir"] / CONFIG["csv_filename"]
    
    if not filepath.exists():
        logger.error(f"Data file not found: {filepath}")
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    try:
        df = pd.read_csv(filepath)
        logger.info(f"Successfully loaded {len(df)} records from {filepath.name}")
        return df
    except pd.errors.ParserError as e:
        logger.error(f"Error parsing CSV: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading data: {e}")
        raise

def validate_numeric_input(prompt: str, min_val: Optional[float] = None, 
                          max_val: Optional[float] = None) -> float:
    """
    Get and validate numeric input from user.
    
    Args:
        prompt: Input prompt message
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Validated numeric input
    """
    while True:
        try:
            value = float(input(prompt))
            if min_val is not None and value < min_val:
                print(f"❌ Value must be >= {min_val}")
                continue
            if max_val is not None and value > max_val:
                print(f"❌ Value must be <= {max_val}")
                continue
            return value
        except ValueError:
            print("❌ Invalid input. Please enter a valid number.")

def validate_choice_input(prompt: str, valid_choices: set) -> str:
    """
    Get and validate choice input from user.
    
    Args:
        prompt: Input prompt message
        valid_choices: Set of valid options
        
    Returns:
        Validated choice
    """
    while True:
        value = input(prompt).strip()
        if value in valid_choices:
            return value
        print(f"❌ Invalid choice. Valid options: {', '.join(valid_choices)}")

# ============================================================================
# CORE DATA OPERATIONS
# ============================================================================

class DataAnalyzer:
    """Main class for data analysis operations."""
    
    def __init__(self, filepath: Optional[Path] = None):
        """Initialize analyzer with data."""
        self.df = load_data(filepath)
        logger.info("DataAnalyzer initialized")
    
    def show_dataframe(self, rows: Optional[int] = None) -> None:
        """Display full or partial dataframe."""
        try:
            if rows is None:
                print(self.df)
            else:
                print(self.df.head(rows))
            logger.info(f"Displayed {len(self.df)} records")
        except Exception as e:
            logger.error(f"Error displaying dataframe: {e}")
            print(f"❌ Error: {e}")
    
    def show_columns(self) -> None:
        """Display all column names."""
        print("\n📊 Dataset Columns:")
        print("-" * 50)
        for i, col in enumerate(self.df.columns, 1):
            print(f"{i:2d}. {col}")
    
    def show_top_rows(self, n: int = 5) -> None:
        """Display top N rows."""
        n = int(validate_numeric_input(f"Enter number of rows (1-{len(self.df)}): ", 1, len(self.df)))
        print(self.df.head(n))
    
    def show_bottom_rows(self, n: int = 5) -> None:
        """Display bottom N rows."""
        n = int(validate_numeric_input(f"Enter number of rows (1-{len(self.df)}): ", 1, len(self.df)))
        print(self.df.tail(n))
    
    def show_specific_column(self) -> None:
        """Display specific column data."""
        self.show_columns()
        col_name = input('\nEnter column name: ').strip()
        if col_name in self.df.columns:
            print(f"\n📋 Column: {col_name}")
            print(self.df[col_name])
        else:
            print(f"❌ Column '{col_name}' not found")
    
    def add_new_record(self) -> None:
        """Add new record with validation."""
        try:
            record_data = {}
            
            # Validated inputs
            record_data['clientID'] = input('Enter Client ID: ').strip()
            record_data['Type'] = validate_choice_input('Enter Type: ', VALID_CARD_TYPES)
            record_data['age'] = int(validate_numeric_input('Enter Age: ', *AGE_RANGE))
            record_data['gender'] = validate_choice_input('Enter Gender (M/F): ', VALID_GENDERS)
            record_data['Dependent_count'] = int(validate_numeric_input('Enter Dependent Count: ', 0, 10))
            record_data['Educational_Level'] = validate_choice_input('Enter Education Level: ', VALID_EDUCATION_LEVELS)
            record_data['Marital_Status'] = validate_choice_input('Enter Marital Status: ', VALID_MARITAL_STATUSES)
            record_data['Income_Category'] = validate_choice_input('Enter Income Category: ', VALID_INCOME_CATEGORIES)
            record_data['Card_Category'] = validate_choice_input('Enter Card Category: ', VALID_CARD_CATEGORIES)
            record_data['Months_on_book'] = int(validate_numeric_input('Enter Months on Book: ', 0, 60))
            record_data['Total_Relationship_count'] = int(validate_numeric_input('Enter Relationship Count: ', 0, 10))
            record_data['Month_Inactive_12_month'] = int(validate_numeric_input('Enter Inactive Months: ', 0, 12))
            record_data['Contacts_count_12_mon'] = int(validate_numeric_input('Enter Contacts Count: ', 0, 20))
            record_data['Credit_Limit'] = int(validate_numeric_input('Enter Credit Limit: ', *CREDIT_LIMIT_RANGE))
            record_data['Total_Revolving_Bal'] = float(validate_numeric_input('Enter Revolving Balance: ', 0))
            record_data['Avg_Open_To_Buy'] = float(validate_numeric_input('Enter Avg Open to Buy: ', 0))
            record_data['Total_Amt_chng_Q4_Q1'] = float(input('Enter Amount Change Q4 to Q1: '))
            record_data['Total_Trans_Amt'] = float(validate_numeric_input('Enter Total Transaction Amount: ', 0))
            record_data['Total_Trans_Ct'] = int(validate_numeric_input('Enter Transaction Count: ', 0))
            record_data['Total_Ct_Chng_Q4_Q1'] = float(input('Enter Count Change Q4 to Q1: '))
            record_data['Average_Utilization_Ratio'] = float(validate_numeric_input('Enter Utilization Ratio: ', 0, 1))
            record_data['geography'] = validate_choice_input('Enter Geography: ', VALID_GEOGRAPHIES)
            
            # Use concat instead of deprecated append
            self.df = pd.concat([self.df, pd.DataFrame([record_data])], ignore_index=True)
            print(f"✅ Record added successfully. Total records: {len(self.df)}")
            logger.info(f"New record added: {record_data['clientID']}")
        
        except ValueError as e:
            print(f"❌ Invalid input: {e}")
            logger.error(f"Input validation error: {e}")
        except Exception as e:
            print(f"❌ Error adding record: {e}")
            logger.error(f"Error adding record: {e}")
    
    def add_new_column(self) -> None:
        """Add new column with validation."""
        try:
            col_name = input('Enter new column name: ').strip()
            if col_name in self.df.columns:
                print(f"❌ Column '{col_name}' already exists")
                return
            
            col_value = input('Enter default value for all rows: ').strip()
            self.df[col_name] = col_value
            print(f"✅ Column '{col_name}' added successfully")
            logger.info(f"Column added: {col_name}")
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Error adding column: {e}")
    
    def delete_column(self) -> None:
        """Delete column with confirmation."""
        self.show_columns()
        col_name = input('\nEnter column name to delete: ').strip()
        
        if col_name not in self.df.columns:
            print(f"❌ Column '{col_name}' not found")
            return
        
        confirm = input(f"⚠️  Are you sure? Type 'YES' to confirm: ").strip().upper()
        if confirm == 'YES':
            self.df = self.df.drop(columns=[col_name])
            print(f"✅ Column '{col_name}' deleted")
            logger.info(f"Column deleted: {col_name}")
        else:
            print("❌ Deletion cancelled")
    
    def delete_record(self) -> None:
        """Delete record with confirmation."""
        try:
            idx = int(validate_numeric_input(f'Enter record index to delete (0-{len(self.df)-1}): ', 
                                            0, len(self.df)-1))
            print(f"\nRecord to delete:\n{self.df.iloc[idx]}")
            confirm = input("⚠️  Type 'YES' to confirm deletion: ").strip().upper()
            
            if confirm == 'YES':
                self.df = self.df.drop(self.df.index[idx])
                self.df.reset_index(drop=True, inplace=True)
                print(f"✅ Record deleted. Total records: {len(self.df)}")
                logger.info(f"Record deleted at index {idx}")
            else:
                print("❌ Deletion cancelled")
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Error deleting record: {e}")
    
    def show_group_summary(self, group_by: str) -> None:
        """Display grouped summary."""
        try:
            if group_by not in self.df.columns:
                print(f"❌ Column '{group_by}' not found")
                return
            
            print(f"\n📊 Summary by {group_by}:")
            print("-" * 50)
            summary = self.df.groupby(group_by).size().sort_values(ascending=False)
            print(summary)
            logger.info(f"Generated summary for {group_by}")
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Error generating summary: {e}")
    
    def show_data_summary(self) -> None:
        """Display statistical summary."""
        print("\n📈 Data Summary Statistics:")
        print(self.df.describe())
        logger.info("Displayed data summary")
    
    def export_data(self, format_type: str, filepath: Optional[Path] = None) -> None:
        """
        Export data to specified format.
        
        Args:
            format_type: 'csv', 'excel', or 'mysql'
            filepath: Output path (for csv/excel)
        """
        try:
            if format_type == 'csv':
                if filepath is None:
                    filepath = CONFIG["backup_dir"] / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                self.df.to_csv(filepath, index=False)
                print(f"✅ Data exported to {filepath}")
                logger.info(f"Data exported to CSV: {filepath}")
            
            elif format_type == 'excel':
                if filepath is None:
                    filepath = CONFIG["backup_dir"] / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                self.df.to_excel(filepath, index=False)
                print(f"✅ Data exported to {filepath}")
                logger.info(f"Data exported to Excel: {filepath}")
            
            elif format_type == 'mysql':
                self._export_to_mysql()
        
        except PermissionError:
            print("❌ Permission denied. Check file permissions.")
            logger.error("Permission denied during export")
        except Exception as e:
            print(f"❌ Export error: {e}")
            logger.error(f"Export error: {e}")
    
    def _export_to_mysql(self) -> None:
        """Export data to MySQL database."""
        try:
            db_config = CONFIG["db_config"]
            engine = create_engine(
                f'mysql+pymysql://{db_config["user"]}:{db_config["password"]}'
                f'@{db_config["host"]}:{db_config["port"]}/{db_config["database"]}'
            )
            
            self.df.to_sql(name='bankchurner_backup', con=engine,
                          index=False, if_exists='replace')
            print("✅ Data exported to MySQL")
            logger.info("Data exported to MySQL")
        
        except sqlalchemy.exc.OperationalError:
            print("❌ MySQL connection failed. Check credentials and server.")
            logger.error("MySQL connection failed")
        except Exception as e:
            print(f"❌ MySQL export error: {e}")
            logger.error(f"MySQL export error: {e}")

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

class DataVisualizer:
    """Class for creating data visualizations."""
    
    def __init__(self, df: pd.DataFrame):
        """Initialize visualizer."""
        self.df = df
        sns.set_style("whitegrid")
    
    def plot_gender_distribution(self) -> None:
        """Plot gender-wise distribution."""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            gender_counts = self.df['gender'].value_counts()
            ax.bar(gender_counts.index, gender_counts.values, color=['#3498db', '#e74c3c'])
            ax.set_xlabel('Gender')
            ax.set_ylabel('Number of Users')
            ax.set_title('Credit Card Users - Gender Distribution')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"❌ Error creating plot: {e}")
            logger.error(f"Plot error: {e}")
    
    def plot_education_distribution(self) -> None:
        """Plot education level distribution."""
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            edu_counts = self.df['Educational_Level'].value_counts()
            ax.bar(edu_counts.index, edu_counts.values, color='#2ecc71')
            ax.set_xlabel('Education Level')
            ax.set_ylabel('Number of Users')
            ax.set_title('Credit Card Users - Education Level Distribution')
            plt.xticks(rotation=45, ha='right')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"❌ Error creating plot: {e}")
            logger.error(f"Plot error: {e}")
    
    def plot_income_distribution(self) -> None:
        """Plot income category distribution."""
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            income_counts = self.df['Income_Category'].value_counts()
            ax.bar(income_counts.index, income_counts.values, color='#f39c12')
            ax.set_xlabel('Income Category')
            ax.set_ylabel('Number of Users')
            ax.set_title('Credit Card Users - Income Distribution')
            plt.xticks(rotation=45, ha='right')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"❌ Error creating plot: {e}")
            logger.error(f"Plot error: {e}")
    
    def plot_geography_pie(self) -> None:
        """Plot geography distribution as pie chart."""
        try:
            fig, ax = plt.subplots(figsize=(10, 8))
            geo_counts = self.df['geography'].value_counts()
            ax.pie(geo_counts.values, labels=geo_counts.index, autopct='%1.1f%%',
                   startangle=90, colors=['#3498db', '#e74c3c', '#2ecc71'])
            ax.set_title('Credit Card Users - Geography Distribution')
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"❌ Error creating plot: {e}")
            logger.error(f"Plot error: {e}")

# ============================================================================
# MENU SYSTEM
# ============================================================================

def show_header(title: str) -> None:
    """Display menu header."""
    clear_screen()
    print(f"\n{'=' * 80}")
    print(f"{title.center(80)}")
    print(f"{'=' * 80}\n")

def data_analysis_menu(analyzer: DataAnalyzer) -> None:
    """Data analysis operations menu."""
    while True:
        show_header("DATA ANALYSIS MENU")
        print("""
        1.  Show Whole DataFrame
        2.  Show Columns
        3.  Show Top Rows
        4.  Show Bottom Rows
        5.  Show Specific Column
        6.  Add New Record
        7.  Add New Column
        8.  Delete Column
        9.  Delete Record
        10. Card Type Distribution
        11. Gender Distribution
        12. Data Summary
        13. Back to Main Menu
        """)
        
        try:
            choice = input('\nEnter your choice (1-13): ').strip()
            
            if choice == '1':
                analyzer.show_dataframe()
                press_key_to_continue()
            elif choice == '2':
                analyzer.show_columns()
                press_key_to_continue()
            elif choice == '3':
                analyzer.show_top_rows()
                press_key_to_continue()
            elif choice == '4':
                analyzer.show_bottom_rows()
                press_key_to_continue()
            elif choice == '5':
                analyzer.show_specific_column()
                press_key_to_continue()
            elif choice == '6':
                analyzer.add_new_record()
                press_key_to_continue()
            elif choice == '7':
                analyzer.add_new_column()
                press_key_to_continue()
            elif choice == '8':
                analyzer.delete_column()
                press_key_to_continue()
            elif choice == '9':
                analyzer.delete_record()
                press_key_to_continue()
            elif choice == '10':
                analyzer.show_group_summary('Type')
                press_key_to_continue()
            elif choice == '11':
                analyzer.show_group_summary('gender')
                press_key_to_continue()
            elif choice == '12':
                analyzer.show_data_summary()
                press_key_to_continue()
            elif choice == '13':
                break
            else:
                print("❌ Invalid choice. Please try again.")
                time.sleep(1)
        
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Menu error: {e}")
            press_key_to_continue()

def graph_menu(visualizer: DataVisualizer) -> None:
    """Graph visualization menu."""
    while True:
        show_header("GRAPH & VISUALIZATION MENU")
        print("""
        1. Gender Distribution (Bar)
        2. Education Distribution (Bar)
        3. Income Distribution (Bar)
        4. Geography Distribution (Pie)
        5. Back to Main Menu
        """)
        
        try:
            choice = input('\nEnter your choice (1-5): ').strip()
            
            if choice == '1':
                visualizer.plot_gender_distribution()
            elif choice == '2':
                visualizer.plot_education_distribution()
            elif choice == '3':
                visualizer.plot_income_distribution()
            elif choice == '4':
                visualizer.plot_geography_pie()
            elif choice == '5':
                break
            else:
                print("❌ Invalid choice. Please try again.")
                time.sleep(1)
        
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Menu error: {e}")

def export_menu(analyzer: DataAnalyzer) -> None:
    """Data export menu."""
    while True:
        show_header("EXPORT DATA MENU")
        print("""
        1. Export to CSV
        2. Export to Excel
        3. Export to MySQL
        4. Back to Main Menu
        """)
        
        try:
            choice = input('\nEnter your choice (1-4): ').strip()
            
            if choice == '1':
                analyzer.export_data('csv')
                press_key_to_continue()
            elif choice == '2':
                analyzer.export_data('excel')
                press_key_to_continue()
            elif choice == '3':
                analyzer.export_data('mysql')
                press_key_to_continue()
            elif choice == '4':
                break
            else:
                print("❌ Invalid choice. Please try again.")
                time.sleep(1)
        
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"Menu error: {e}")
            press_key_to_continue()

def main_menu() -> None:
    """Main menu."""
    try:
        analyzer = DataAnalyzer()
        visualizer = DataVisualizer(analyzer.df)
        
        while True:
            show_header("BANK CHURNER ANALYTICS - MAIN MENU")
            print(f"Current records: {len(analyzer.df)}\n")
            print("""
            1. Data Analysis
            2. Visualizations
            3. Export Data
            4. Help
            5. Exit
            """)
            
            choice = input('\nEnter your choice (1-5): ').strip()
            
            if choice == '1':
                data_analysis_menu(analyzer)
                # Update visualizer with modified data
                visualizer = DataVisualizer(analyzer.df)
            elif choice == '2':
                graph_menu(visualizer)
            elif choice == '3':
                export_menu(analyzer)
            elif choice == '4':
                show_header("HELP")
                print("""
                This application provides comprehensive credit card customer analysis.
                
                Features:
                - View and analyze customer data
                - Add/modify/delete records and columns
                - Generate statistical summaries
                - Create visualizations (charts, graphs, pie charts)
                - Export data to CSV, Excel, or MySQL
                
                Need help? Check the log file in ./backup/app.log
                """)
                press_key_to_continue()
            elif choice == '5':
                confirm = input("⚠️  Are you sure you want to exit? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y']:
                    print("👋 Thank you for using Bank Churner Analytics!")
                    logger.info("Application closed by user")
                    break
            else:
                print("❌ Invalid choice. Please try again.")
                time.sleep(1)
    
    except FileNotFoundError as e:
        print(f"❌ {e}")
        logger.error(f"File not found: {e}")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("Application started")
    logger.info("=" * 80)
    
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Application interrupted by user")
        logger.info("Application interrupted")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.critical(f"Unexpected error: {e}", exc_info=True)
