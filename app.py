from flask import Flask, render_template, request, redirect, send_file, session
import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ========================
# إنشاء قاعدة البيانات
# ========================
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY,
        name TEXT,
        amount REAL,
        date TEXT,
        time TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ========================
# تسجيل الدخول
# ========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["user"] == "admin" and request.form["pass"] == "1234":
            session["user"] = True
            return redirect("/dashboard")
    return render_template("login.html")

# ========================
# لوحة التحكم
# ========================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        name = request.form["name"]
        amount = request.form["amount"]

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M")

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO records VALUES(NULL,?,?,?,?)",
            (name, amount, date, time)
        )
        conn.commit()
        conn.close()

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    return render_template("dashboard.html", data=data)

# ========================
# حذف سجل
# ========================
@app.route("/delete/<int:id>")
def delete(id):

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ========================
# تقرير PDF عام
# ========================
@app.route("/pdf")
def pdf():

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT name, amount, date, time FROM records")
    rows = c.fetchall()
    conn.close()

    file = "records.pdf"
    pdf = canvas.Canvas(file)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(170, 800, "Student Fund Report")

    pdf.setFont("Helvetica-Bold", 10)
    y = 760
    pdf.drawString(50, y, "Name")
    pdf.drawString(200, y, "Amount")
    pdf.drawString(300, y, "Date")
    pdf.drawString(420, y, "Time")

    pdf.setFont("Helvetica", 10)
    y -= 20

    for row in rows:
        pdf.drawString(50, y, str(row[0]))
        pdf.drawString(200, y, str(row[1]))
        pdf.drawString(300, y, str(row[2]))
        pdf.drawString(420, y, str(row[3]))

        y -= 20
        if y < 50:
            pdf.showPage()
            y = 800

    pdf.save()

    return send_file(file, as_attachment=True)

# ========================
# تقرير شهري
# ========================
@app.route("/monthly", methods=["POST"])
def monthly():

    month = request.form["month"]

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("""
        SELECT name, amount, date, time
        FROM records
        WHERE date LIKE ?
    """, (month + "%",))

    rows = c.fetchall()

    total = sum(float(r[1]) for r in rows)

    conn.close()

    file = "monthly_report.pdf"
    pdf = canvas.Canvas(file)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(150, 800, f"Monthly Report — {month}")

    pdf.setFont("Helvetica", 10)
    y = 760

    for r in rows:
        pdf.drawString(50, y, f"{r[0]} | {r[1]} | {r[2]} {r[3]}")
        y -= 20

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y-20, f"TOTAL = {total}")

    pdf.save()

    return send_file(file, as_attachment=True)

# ========================
# تشغيل البرنامج
# ========================
if __name__ == "__main__":
    app.run(debug=True)
