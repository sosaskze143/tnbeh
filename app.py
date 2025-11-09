import os
import sqlite3
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from pywebpush import webpush, WebPushException
from werkzeug.utils import secure_filename

# -------- CONFIG ----------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXT = {'png','jpg','jpeg','gif'}
ADMIN_NUMBER = "1430"
DB_FILE = 'database.db'
VAPID_PRIVATE_KEY_FILE = 'vapid_private.pem'
VAPID_PUBLIC_KEY_FILE = 'vapid_public.pem'
VAPID_CLAIMS = {"sub":"mailto:you@example.com"}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ------------------- DATABASE -------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        category TEXT,
        image TEXT,
        link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT,
        p256dh TEXT,
        auth TEXT
    )
    ''')
    conn.commit()
    conn.close()

def add_notification(title, body, category=None, image_filename=None, link=None):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO notifications (title, body, category, image, link) VALUES (?, ?, ?, ?, ?)", 
                (title, body, category, image_filename, link))
    nid = cur.lastrowid
    conn.commit()
    conn.close()
    return nid

def list_notifications():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, title, body, category, image, link, created_at FROM notifications ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_notification(nid):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM notifications WHERE id = ?", (nid,))
    conn.commit()
    conn.close()

def get_subscriptions():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, endpoint, p256dh, auth FROM subscriptions")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_subscription(endpoint, p256dh, auth):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO subscriptions (endpoint, p256dh, auth) VALUES (?, ?, ?)", (endpoint, p256dh, auth))
    conn.commit()
    conn.close()

init_db()

# ------------------- ROUTES -------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/admin')
def admin_panel():
    return render_template('admin_panel.html')

@app.route('/user')
def user_home():
    return render_template('user_home.html')

@app.route('/api/notifications')
def api_notifications():
    rows = list_notifications()
    data = [{"id": r[0], "title": r[1], "body": r[2], "category": r[3], "image": r[4], "link": r[5], "created_at": r[6]} for r in rows]
    return jsonify(data)

@app.route('/api/admin/add', methods=['POST'])
def api_admin_add():
    number = request.form.get('number')
    if number != ADMIN_NUMBER:
        return jsonify({"ok": False, "msg":"Unauthorized"}), 403
    title = request.form.get('title','').strip()
    body = request.form.get('body','').strip()
    category = request.form.get('category','').strip()
    link = request.form.get('link','').strip()
    image_filename = None
    if 'image' in request.files:
        f = request.files['image']
        if f and '.' in f.filename and f.filename.rsplit('.',1)[1].lower() in ALLOWED_EXT:
            filename = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename
    nid = add_notification(title, body, category, image_filename, link)
    # إرسال إشعار لكل المشتركين
    for sub in get_subscriptions():
        sub_info = {"endpoint": sub[1], "keys":{"p256dh":sub[2], "auth":sub[3]}}
        try:
            webpush(subscription_info=sub_info, data=f"{title}\n{body}", 
                    vapid_private_key=open(VAPID_PRIVATE_KEY_FILE).read(), 
                    vapid_claims=VAPID_CLAIMS)
        except WebPushException as ex:
            print("WebPush error:", ex)
    return jsonify({"ok": True, "id": nid})

@app.route('/api/admin/delete/<int:nid>', methods=['POST'])
def api_admin_delete(nid):
    delete_notification(nid)
    return jsonify({"ok": True})

@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    data = request.get_json()
    endpoint = data.get('endpoint')
    keys = data.get('keys', {})
    add_subscription(endpoint, keys.get('p256dh'), keys.get('auth'))
    return jsonify({"ok": True})

@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)