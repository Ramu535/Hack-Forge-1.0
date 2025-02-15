from flask import Flask, request, jsonify, render_template, redirect, url_for,session
import sqlite3
import random
import bcrypt
import secrets
import os
from twilio.rest import Client
from flask import session

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize Database with tables
def init_db():
    conn = sqlite3.connect('imei_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS imei_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mobile_number TEXT UNIQUE NOT NULL,
                        imei_number TEXT NOT NULL)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL)''')
    try:
        cursor.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ("Ramu", "1234"))

        print("Admin registered successfully!")
    except sqlite3.IntegrityError:
        print("Admin username already exists!")
    finally:
        conn.close()


# Generate a random 15-digit IMEI number
def generate_random_imei():
    return str(random.randint(100000000000000, 999999999999999))

# Function to calculate Luhn check digit
def calculate_luhn(imei_base):
    sum_digits = 0
    for i, digit in enumerate(imei_base):
        num = int(digit)
        if i % 2 == 1:
            num *= 2
            if num > 9:
                num -= 9
        sum_digits += num
    return (10 - (sum_digits % 10)) % 10

# Generate a formatted IMEI number
def generate_random_imei():
    tac = f"{random.randint(10, 99)}{random.randint(100000, 999999)}"
    serial = f"{random.randint(100000, 999999)}"
    imei_base = tac + serial
    check_digit = calculate_luhn(imei_base)
    return f"{tac[:2]}-{tac[2:]}-{serial}-{check_digit}"


# Assign IMEI Page
@app.route('/')
def login():
    return render_template("assign.html")

@app.route('/assign_imei', methods=['GET', 'POST'])
def assign_imei():
    if request.method == 'POST':
        mobile_number = request.form.get('mobile_number')

        # Check if mobile number is provided
        if not mobile_number:
            message = "Mobile number is required!"
        # Check if the mobile number is 10 digits and contains only numbers
        elif not (mobile_number.isdigit() and len(mobile_number) == 10):
            message = "Invalid mobile number!"
        else:
            generated_imei = generate_random_imei()
            try:
                conn = sqlite3.connect('imei_tracker.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO imei_data (mobile_number, imei_number) VALUES (?, ?)", 
                            (mobile_number, generated_imei))
                conn.commit()
                message = f"Assigned IMEI: {generated_imei}"
            except sqlite3.IntegrityError:
                message = "Mobile number already exists!"
            finally:
                conn.close()

        return render_template('assign.html', message=message, imei=generated_imei if 'generated_imei' in locals() else None)


# Admin Login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect('imei_tracker.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM admins WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result :
            session['admin'] = username  # Store session
            return redirect(url_for('retrieve_imei'))
        else:
            message = "Invalid username or password!"

    return render_template('admin_login.html', message=message)

# Retrieve IMEI (Protected by Admin Login)
@app.route('/retrieve', methods=['GET', 'POST'])
def retrieve_imei():
    if 'admin' not in session:  # Check if admin is logged in
        return redirect(url_for('admin_login'))

    imei_number = None
    message = None
    if request.method == 'POST':
        mobile_number = request.form.get('mobile_number')
        if not mobile_number:
            message = "Mobile number is required!"
        else:
            conn = sqlite3.connect('imei_tracker.db')
            cursor = conn.cursor()
            cursor.execute("SELECT imei_number FROM imei_data WHERE mobile_number = ?", (mobile_number,))
            result = cursor.fetchone()
            conn.close()
            if result:
                imei_number = result[0]
            else:
                message = "Mobile number not found!"
    
    return render_template('retrieve.html', imei_number=imei_number, message=message)

# Admin Logout
@app.route('/logout')
def logout():
    session.pop('admin', None)  # Remove admin session
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
