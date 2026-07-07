"""
Simple launcher to choose which interface to run
"""
import subprocess
import sys
import os

def main():
    print("=" * 50)
    print("Ticket Management System - Launcher")
    print("=" * 50)
    print("\nChoose an option:")
    print("1. User Interface (Port 8501)")
    print("2. Admin Dashboard (Port 8502)")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        print("\nStarting User Interface on http://localhost:8501")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "user_app.py", "--server.port", "8501"])
    elif choice == "2":
        print("\nStarting Admin Dashboard on http://localhost:8502")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "admin_app.py", "--server.port", "8502"])
    elif choice == "3":
        print("Exiting...")
        sys.exit(0)
    else:
        print("Invalid choice. Please run again.")

if __name__ == "__main__":
    main()
