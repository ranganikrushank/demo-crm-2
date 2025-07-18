from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = '06b7d11c58cad2c88e2121c1c5a48ec70274b53a830029efb4f92ace47c81ecd'

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_2wmrgLI0iYXP@ep-winter-bread-a1z0y9wq-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Login Manager Setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# -------------------- MODELS ------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), unique=True, nullable=False)
    customer_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    country = db.Column(db.String(100))
    requirement = db.Column(db.Text)
    company_name = db.Column(db.String(100))

class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    amount = db.Column(db.Float)
    date = db.Column(db.String(20), nullable=False)  # Format: YYYY-MM-DD



class FinancialSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(100))
    amount = db.Column(db.Float)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False)  # <- This MUST be included
    description = db.Column(db.String(255))
    amount = db.Column(db.Float)
    date = db.Column(db.String(20))  # Format: "YYYY-MM-DD"




class HistoryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))
    action = db.Column(db.String(200))
    panel = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

def log_history(user, action, panel):
    db.session.add(HistoryLog(user=user, action=action, panel=panel))
    db.session.commit()



class ClientPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float)
    date = db.Column(db.String(20))  # Format: YYYY-MM-DD
    status = db.Column(db.String(20))  # e.g., 'Pending', 'Paid'




# -------------------- AUTH ------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from flask import session  # 👈 import session at the top

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            login_user(user)
            session.permanent = True  # ✅ Session stays until manually logged out
            flash('Login successful!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_base_dashboard'))
            elif user.role == 'employee1':
                return redirect(url_for('purchase_panel'))
            elif user.role == 'employee2':
                return redirect(url_for('employee2_panel'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

# -------------------- ORDER PANEL ------------------------

@app.route('/order', methods=['GET', 'POST'])
@login_required
def order_panel():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        order = Order(
            order_id=request.form['order_id'],
            customer_name=request.form['customer_name'],
            email=request.form['email'],
            phone=request.form['phone'],
            country=request.form['country'],
            requirement=request.form['requirement'],
            company_name=request.form['company_name']
        )
        db.session.add(order)
        db.session.commit()
        flash('Order created successfully!', 'success')
        return redirect(url_for('order_panel'))

    return render_template('order.html', orders=Order.query.all())

# -------------------- PURCHASE PANEL ------------------------

@app.route('/purchase', methods=['GET', 'POST'])
@login_required
def purchase_panel():
    if current_user.role != 'employee1':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        order_id = request.form.get('order_id')
        descriptions = request.form.getlist('description[]')
        amounts = request.form.getlist('amount[]')
        dates = request.form.getlist('date[]')  # ✅ New line

        # 🔁 Save all entered rows with date
        for desc, amt, dt in zip(descriptions, amounts, dates):
            if desc.strip():
                db.session.add(PurchaseOrder(
                    order_id=order_id,
                    description=desc,
                    amount=float(amt or 0),
                    date=dt  # ✅ Save date
                ))

        db.session.commit()
        log_history(current_user.username, f"Created purchase entry for Order ID: {order_id}", "Purchase Panel")
        flash("Saved successfully!", "success")
        return redirect(url_for('purchase_panel'))

    # Grouped entries for display
    grouped_purchases = {}
    for p in PurchaseOrder.query.order_by(PurchaseOrder.order_id).all():
        grouped_purchases.setdefault(p.order_id, []).append(p)

    return render_template(
        'purchase.html',
        orders=Order.query.all(),
        grouped_purchases=grouped_purchases
    )



@app.route('/purchase/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_purchase(id):
    if current_user.role != 'employee1':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    po = PurchaseOrder.query.get_or_404(id)
    if request.method == 'POST':
        po.description = request.form['description']
        po.amount = float(request.form['amount'] or 0)
        db.session.commit()
        flash('Updated successfully.', 'success')
        return redirect(url_for('purchase_panel'))

    return render_template('edit_purchase.html', po=po)

@app.route('/purchase/delete/<int:id>', methods=['POST'])
@login_required
def delete_purchase(id):
    if current_user.role != 'employee1':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    db.session.delete(PurchaseOrder.query.get_or_404(id))
    db.session.commit()
    flash('Deleted successfully.', 'info')
    return redirect(url_for('purchase_panel'))



@app.route('/purchase/edit_group/<order_id>', methods=['GET', 'POST'])
@login_required
def edit_purchase_group(order_id):
    if current_user.role != 'employee1':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        descriptions = request.form.getlist('description[]')
        amounts = request.form.getlist('amount[]')
        dates = request.form.getlist('date[]')

        # Delete old entries for this order_id
        PurchaseOrder.query.filter_by(order_id=order_id).delete()

        # Add updated entries
        for desc, amt, dt in zip(descriptions, amounts, dates):
            if desc.strip():
                db.session.add(PurchaseOrder(
                    order_id=order_id,
                    description=desc.strip(),
                    amount=float(amt or 0),
                    date=dt
                ))

        db.session.commit()
        log_history(current_user.username, f"Edited purchase entries for Order ID: {order_id}", "Purchase Panel")
        flash("Purchase entries updated successfully.", "success")
        return redirect(url_for('purchase_panel'))

    purchases = PurchaseOrder.query.filter_by(order_id=order_id).all()
    return render_template('edit_purchase_group.html', purchases=purchases, order_id=order_id)




# -------------------- EMPLOYEE 2 PANEL ------------------------

@app.route('/employee2', methods=['GET'])
@login_required
def employee2_panel():
    if current_user.role != 'employee2':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    expenses = Expense.query
    if from_date and to_date:
        expenses = expenses.filter(Expense.date >= from_date, Expense.date <= to_date)
    expenses = expenses.all()

    return render_template('employee2.html',
                           orders=Order.query.all(),
                           summaries=FinancialSummary.query.all(),
                           expenses=expenses)

@app.route('/save_summary', methods=['POST'])
@login_required
def save_summary():
    if current_user.role != 'employee2':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    order_id = request.form.get('order_id')
    labels = request.form.getlist('labels[]')
    amounts = request.form.getlist('amounts[]')

    for label, amt in zip(labels, amounts):
        if amt.strip():
            db.session.add(FinancialSummary(order_id=order_id, label=label, amount=float(amt)))

    db.session.commit()
    log_history(current_user.username, f"Added summary for Order ID: {order_id}", "Employee 2 - Tab 1")
    flash("Summary saved.", "success")
    return redirect(url_for('employee2_panel'))

@app.route('/save_expenses', methods=['POST'])
@login_required
def save_expenses():
    if current_user.role != 'employee2':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    descriptions = request.form.getlist('description[]')
    amounts = request.form.getlist('amount[]')
    dates = request.form.getlist('date[]')

    for desc, amt, dt in zip(descriptions, amounts, dates):
        if not desc.strip():
            continue
        expense = Expense(
            order_id="GENERAL",  # 🔄 Mark as general expense
            description=desc,
            amount=float(amt) if amt else 0,
            date=dt
        )
        db.session.add(expense)

    db.session.commit()
    log_history(current_user.username, f"Added general business expenses", "Employee 2 - Tab 2")
    flash("Expenses saved successfully!", "success")
    return redirect(url_for('employee2_panel'))




# -------------------- ADMIN PANEL ------------------------

from sqlalchemy import func  # for aggregation if needed

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    data = []
    for order in Order.query.all():
        order_id = order.order_id
        has_purchase = PurchaseOrder.query.filter_by(order_id=order_id).first()
        has_summary = FinancialSummary.query.filter_by(order_id=order_id).first()
        has_expense = Expense.query.filter_by(order_id=order_id).first()
        client_payment = ClientPayment.query.filter_by(order_id=order_id).first()
        payment_status = client_payment.status if client_payment else "No Entry"

        status = "Completed" if has_purchase and has_summary and has_expense else "Pending"

        data.append({
            "order_id": order_id,
            "customer_name": order.customer_name,
            "company_name": order.company_name,
            "requirement": order.requirement,
            "status": status,
            "payment_status": payment_status  # <-- 👈 Add this field
        })

    return render_template('admin_dashboard.html', data=data)


@app.route('/admin/view/<order_id>')
@login_required
def view_order_details(order_id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    order = Order.query.filter_by(order_id=order_id).first_or_404()
    purchases = PurchaseOrder.query.filter_by(order_id=order_id).all()
    summaries = FinancialSummary.query.filter_by(order_id=order_id).all()
    expenses = Expense.query.filter_by(order_id=order_id).all()

    return render_template('admin_view_order.html',
                           order=order,
                           purchases=purchases,
                           summaries=summaries,
                           expenses=expenses)

@app.route('/admin/history')
@login_required
def view_history_logs():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    user = request.args.get('user')
    panel = request.args.get('panel')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    query = HistoryLog.query
    if user:
        query = query.filter_by(user=user)
    if panel:
        query = query.filter_by(panel=panel)
    if from_date and to_date:
        try:
            start = datetime.strptime(from_date, "%Y-%m-%d")
            end = datetime.strptime(to_date, "%Y-%m-%d")
            query = query.filter(HistoryLog.timestamp.between(start, end))
        except:
            flash("Invalid date format!", "danger")

    logs = query.order_by(HistoryLog.timestamp.desc()).all()
    users = db.session.query(HistoryLog.user).distinct()
    panels = db.session.query(HistoryLog.panel).distinct()

    return render_template("history_logs.html", logs=logs, users=users, panels=panels)


@app.route('/client', methods=['GET', 'POST'])
@login_required
def client_panel():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        payment = ClientPayment(
            order_id=request.form['order_id'],
            amount=float(request.form['amount'] or 0),
            date=request.form['date'],
            status=request.form['status']
        )
        db.session.add(payment)
        db.session.commit()
        flash("Client payment record added.", "success")
        return redirect(url_for('client_panel'))

    return render_template('client_panel.html', orders=Order.query.all(), payments=ClientPayment.query.all())



@app.route('/admin/base-dashboard')
@login_required
def admin_base_dashboard():
    if current_user.role != 'admin':
        flash("Access denied!", "danger")
        return redirect(url_for('login'))
    return render_template('base_dashboard.html')





# -------------------- MAIN ------------------------

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
