from flask import Flask, render_template, request, redirect, session, send_file
import psycopg2
import os
from datetime import datetime
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","secret123")

DATABASE_URL = os.environ.get("DATABASE_URL")


# الاتصال بقاعدة البيانات
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


# إنشاء الجداول
def init_db():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS records(
        id SERIAL PRIMARY KEY,
        name TEXT,
        amount FLOAT,
        date TEXT,
        time TEXT,
        added_by TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS debts(
        id SERIAL PRIMARY KEY,
        title TEXT,
        amount FLOAT,
        date TEXT,
        added_by TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


init_db()


# تسجيل الدخول
@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username,password)
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:

            session["user"] = username
            return redirect("/dashboard")

        else:

            return render_template(
            "login.html",
            error="اسم المستخدم أو كلمة المرور غير صحيحة"
            )

    return render_template("login.html")


# إنشاء حساب
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        try:

            conn = get_db()
            cur = conn.cursor()

            cur.execute(
            "INSERT INTO users(username,password) VALUES(%s,%s)",
            (username,password)
            )

            conn.commit()

            cur.close()
            conn.close()

            return redirect("/")

        except:

            return render_template(
            "register.html",
            error="المستخدم موجود مسبقاً"
            )

    return render_template("register.html")


# تسجيل خروج
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/")


# لوحة التحكم
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():

    if "user" not in session:
        return redirect("/")

    if request.method == "POST":

        name = request.form["name"]
        amount = float(request.form["amount"])
        ttype = request.form["type"]

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M")

        conn = get_db()
        cur = conn.cursor()

        if ttype == "expense":

            cur.execute("""
            INSERT INTO debts(title,amount,date,added_by)
            VALUES(%s,%s,%s,%s)
            """,(name,amount,date,session["user"]))

        else:

            cur.execute("""
            INSERT INTO records(name,amount,date,time,added_by)
            VALUES(%s,%s,%s,%s,%s)
            """,(name,amount,date,time,session["user"]))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/dashboard")


    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id,name,amount,date FROM records ORDER BY id DESC")
    incomes = cur.fetchall()

    cur.execute("SELECT id,title,amount,date FROM debts ORDER BY id DESC")
    expenses = cur.fetchall()

    cur.execute("SELECT SUM(amount) FROM records")
    total_income = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(amount) FROM debts")
    total_expense = cur.fetchone()[0] or 0

    balance = total_income - total_expense

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        incomes=incomes,
        expenses=expenses,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance
    )


# حذف دخل
@app.route("/delete/<int:id>")
def delete(id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM records WHERE id=%s",(id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/dashboard")


# حذف مصروف
@app.route("/delete_expense/<int:id>")
def delete_expense(id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM debts WHERE id=%s",(id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/dashboard")


# تقرير PDF
@app.route("/pdf")
def pdf():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT name,amount,date FROM records")
    incomes = cur.fetchall()

    cur.execute("SELECT title,amount,date FROM debts")
    expenses = cur.fetchall()

    cur.close()
    conn.close()

    file = "report.pdf"
    pdf = canvas.Canvas(file)

    pdf.setFont("Helvetica-Bold",16)
    pdf.drawString(200,800,"Financial Report")

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
    pdf.drawString(40,y,f"Total Expenses: {total_expense}")
    y -= 20
    pdf.drawString(40,y,f"Balance: {balance}")

    pdf.save()

    return send_file(file, as_attachment=True)


if __name__ == "__main__":

    port = int(os.environ.get("PORT",10000))

    app.run(host="0.0.0.0",port=port)
