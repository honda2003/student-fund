from flask import Flask, render_template, request, redirect, send_file, session
import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

DB = "data.db"

# ======================
# الاتصال بقاعدة البيانات
# ======================
def get_db():
    return sqlite3.connect(DB)

# ======================
# إنشاء الجداول
# ======================
def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        amount REAL,
        date TEXT,
        time TEXT,
        added_by TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS debts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        amount REAL,
        date TEXT,
        added_by TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ======================
# تسجيل الدخول
# ======================
@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username") or request.form.get("user")

        if not username:
            return render_template("login.html", error="ادخل اسم المستخدم")

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()

        if not user:
            c.execute("INSERT INTO users(username) VALUES(?)", (username,))
            conn.commit()

        conn.close()

        session["user"] = username

        return redirect("/dashboard")

    return render_template("login.html")

# ======================
# إنشاء حساب
# ======================
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")

        if not username:
            return render_template("register.html", error="ادخل اسم المستخدم")

        try:

            conn = get_db()
            c = conn.cursor()

            c.execute("INSERT INTO users(username) VALUES(?)",(username,))
            conn.commit()
            conn.close()

            return redirect("/")

        except:

            return render_template("register.html", error="المستخدم موجود مسبقاً")

    return render_template("register.html")

# ======================
# تسجيل خروج
# ======================
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/")

# ======================
# لوحة التحكم
# ======================
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():

    if "user" not in session:
        return redirect("/")

    if request.method == "POST":

        name = request.form.get("name")
        amount = request.form.get("amount")
        ttype = request.form.get("type")

        if name and amount:

            amount = float(amount)

            now = datetime.now()
            date = now.strftime("%Y-%m-%d")
            time = now.strftime("%H:%M")

            conn = get_db()
            c = conn.cursor()

            if ttype == "expense":

                c.execute("""
                INSERT INTO debts(title,amount,date,added_by)
                VALUES(?,?,?,?)
                """,(name,amount,date,session["user"]))

            else:

                c.execute("""
                INSERT INTO records(name,amount,date,time,added_by)
                VALUES(?,?,?,?,?)
                """,(name,amount,date,time,session["user"]))

            conn.commit()
            conn.close()

        return redirect("/dashboard")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id,name,amount,date FROM records ORDER BY id DESC")
    incomes = c.fetchall()

    c.execute("SELECT id,title,amount,date FROM debts ORDER BY id DESC")
    expenses = c.fetchall()

    c.execute("SELECT SUM(amount) FROM records")
    total_income = c.fetchone()[0] or 0

    c.execute("SELECT SUM(amount) FROM debts")
    total_expense = c.fetchone()[0] or 0

    balance = total_income - total_expense

    conn.close()

    return render_template(
        "dashboard.html",
        incomes=incomes,
        expenses=expenses,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        user=session["user"]
    )

# ======================
# حذف العمليات
# ======================
@app.route("/delete/<int:id>")
def delete(id):

    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM records WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

@app.route("/delete_expense/<int:id>")
def delete_expense(id):

    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM debts WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ======================
# صفحة الخصوصية
# ======================
@app.route("/policy")
def policy():
    return render_template("policy.html")

# ======================
# إنشاء تقرير PDF
# ======================
@app.route("/pdf")
def pdf():

    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT name,amount,date FROM records")
    incomes = c.fetchall()

    c.execute("SELECT title,amount,date FROM debts")
    expenses = c.fetchall()

    conn.close()

    file = "report.pdf"
    pdf = canvas.Canvas(file)

    pdf.setFont("Helvetica-Bold",16)
    pdf.drawString(180,800,"Financial Report")

    y = 760
    total_income = 0
    total_expense = 0

    pdf.drawString(40,y,"Incomes")
    y -= 20

    for row in incomes:
        pdf.drawString(40,y,f"{row[2]} - {row[0]} : {row[1]}")
        total_income += row[1]
        y -= 20

    y -= 10
    pdf.drawString(40,y,"Expenses")
    y -= 20

    for row in expenses:
        pdf.drawString(40,y,f"{row[2]} - {row[0]} : {row[1]}")
        total_expense += row[1]
        y -= 20

    balance = total_income - total_expense

    y -= 20
    pdf.drawString(40,y,f"Total Income: {total_income}")
    y -= 20
    pdf.drawString(40,y,f"Total Expense: {total_expense}")
    y -= 20
    pdf.drawString(40,y,f"Balance: {balance}")

    pdf.save()

    return send_file(file, as_attachment=True)

# ======================
# تشغيل التطبيق
# ======================
if __name__ == "__main__":
    app.run(debug=True)
