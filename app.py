#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify
from imap_tools import MailBox, AND
import re

app = Flask(__name__)

# ======= إعدادات البريد =======
EMAIL = "catch.steam@swamp-store.com"
PASSWORD = "n1etqhnSxNDc"
IMAP_SERVER = "imap.zoho.com"

# ======= الطلبات =======
ORDERS_FILE = "orders.txt"

def load_orders():
    orders = set()
    with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                orders.add(line.strip())
    return orders

def check_order_exists(order):
    return order in load_orders()

# ======= تنظيف اليوزر =======
def normalize(u):
    return re.sub(r'[^a-z0-9]', '', u.lower())

# ======= استخراج الكود من ايميلات Zoho =======
def get_steam_code(target_username):
    norm_target = normalize(target_username)

    try:
        with MailBox(IMAP_SERVER).login(EMAIL, PASSWORD) as mailbox:
            # نبحث عن آخر 50 إيميل غير مقروء
            for msg in mailbox.fetch(AND(seen=False), limit=50):
                body = msg.text or ""
                if msg.html:
                    body += " " + msg.html

                # استخراج اليوزر والكود
                # الكود: 5-6 أحرف أو أرقام
                code_match = re.search(r'\b([A-Z0-9]{5,6})\b', body)
                username_match = re.search(r'^([a-zA-Z0-9_]+),', body, re.MULTILINE)
                
                username_in_email = None
                if username_match:
                    username_in_email = username_match.group(1)
                else:
                    hello_match = re.search(r'(?:Hello|Hi|Dear)[,\s]+([a-zA-Z0-9_]+)', body, re.IGNORECASE)
                    if hello_match:
                        username_in_email = hello_match.group(1)

                if not code_match or not username_in_email:
                    continue

                code = code_match.group(1).upper()
                norm_email_user = normalize(username_in_email)

                # ✅ إذا تطابق اليوزر
                if norm_email_user == norm_target:
                    # علم الإيميل كمقروء
                    mailbox.flag(msg.uid, '\\Seen', True)
                    return code

    except Exception as e:
        print("خطأ في البريد:", e)
        return None

    return None

# ======= Routes =======
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check_order', methods=['POST'])
def check_order():
    data = request.get_json()
    order = data.get('order_number', '').strip()
    if not order:
        return jsonify({'success': False, 'message': '❌ أدخل رقم الطلب'})

    if check_order_exists(order):
        return jsonify({'success': True, 'message': '✅ الطلب موجود، أدخل اسم المستخدم الآن'})
    else:
        return jsonify({'success': False, 'message': '❌ الطلب غير موجود'})

@app.route('/get_steam_code', methods=['POST'])
def get_code():
    data = request.get_json()
    username = data.get('steam_username', '').strip()
    if not username:
        return jsonify({'success': False, 'message': '❌ أدخل اسم المستخدم'})

    code = get_steam_code(username)
    if code:
        return jsonify({'success': True, 'steam_code': code, 'message': f'✅ الكود: {code}'})
    else:
        return jsonify({'success': False, 'message': '❌ اليوزر غير مطابق أو لا يوجد كود في الإيميل'})
    
if __name__ == '__main__':
    print("🚀 http://localhost:5000")
    app.run(debug=True)
