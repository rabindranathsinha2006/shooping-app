import os
import sqlite3
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lumistore-development-secret-key")
DATABASE = os.path.join(os.path.dirname(__file__), "store.db")


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            stock INTEGER DEFAULT 20
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'Processing',
            payment_method TEXT DEFAULT 'COD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    # Small migration for databases created by an older version.
    order_columns = [row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()]
    if "payment_method" not in order_columns:
        conn.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'COD'")

    product_count = conn.execute(
        "SELECT COUNT(*) AS count FROM products"
    ).fetchone()["count"]

    if product_count == 0:
        products = [
            (
                "Audio Studio Wireless Headphones",
                "Premium wireless headphones with clear studio sound and comfortable ear cushions.",
                189,
                "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=85",
                "Tech & Audio",
                25
            ),
            (
                "Nordic Ceramic Vase",
                "Minimal Scandinavian ceramic vase for modern home decoration.",
                42,
                "https://images.unsplash.com/photo-1612196808214-b8e1d6145a8c?auto=format&fit=crop&w=800&q=85",
                "Home",
                18
            ),
            (
                "Minimalist Chrono Watch",
                "Elegant minimalist watch with a classic dial and premium strap.",
                145,
                "https://images.unsplash.com/photo-1524805444758-089113d48a6d?auto=format&fit=crop&w=800&q=85",
                "Fashion",
                12
            ),
            (
                "Merino Desk Mat",
                "Sustainable soft desk mat designed for a clean and productive workspace.",
                36,
                "https://images.unsplash.com/photo-1586953208448-b95a79798f07?auto=format&fit=crop&w=800&q=85",
                "Workspace",
                30
            ),
            (
                "Modern Table Lamp",
                "Warm ambient table lamp for a calm and stylish interior.",
                74,
                "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=800&q=85",
                "Home",
                20
            ),
            (
                "Wireless Desk Speaker",
                "Compact wireless speaker with balanced sound and modern design.",
                99,
                "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?auto=format&fit=crop&w=800&q=85",
                "Tech & Audio",
                15
            ),
        ]

        conn.executemany("""
            INSERT INTO products
            (name, description, price, image, category, stock)
            VALUES (?, ?, ?, ?, ?, ?)
        """, products)

    conn.commit()
    conn.close()


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)
    return wrapped_view


@app.context_processor
def inject_cart_count():
    cart = session.get("cart", {})
    wishlist_count = 0
    if "user_id" in session:
        conn = get_db_connection()
        wishlist_count = conn.execute(
            "SELECT COUNT(*) FROM wishlist WHERE user_id = ?",
            (session["user_id"],)
        ).fetchone()[0]
        conn.close()
    return {
        "cart_count": sum(cart.values()),
        "wishlist_count": wishlist_count
    }


@app.route("/")
def index():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    wishlist_ids = set()
    if "user_id" in session:
        wishlist_ids = {
            row[0] for row in conn.execute(
                "SELECT product_id FROM wishlist WHERE user_id = ?",
                (session["user_id"],)
            ).fetchall()
        }
    conn.close()
    return render_template("index.html", products=products, wishlist_ids=wishlist_ids)


@app.route("/product/<int:product_id>")
def product(product_id):
    conn = get_db_connection()
    item = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    conn.close()

    if item is None:
        flash("Product not found.", "danger")
        return redirect(url_for("index"))

    return render_template("product.html", product=item)


@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    conn = get_db_connection()
    item = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    conn.close()

    if item is None:
        flash("Product not found.", "danger")
        return redirect(url_for("index"))

    cart = session.get("cart", {})
    key = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    session["cart"] = cart
    flash(f"{item['name']} added to cart.", "success")

    return redirect(request.referrer or url_for("index"))


@app.route("/cart")
def cart():
    cart_data = session.get("cart", {})
    products = []
    total = 0

    conn = get_db_connection()

    for product_id, quantity in cart_data.items():
        item = conn.execute(
            "SELECT * FROM products WHERE id = ?", (int(product_id),)
        ).fetchone()

        if item:
            subtotal = item["price"] * quantity
            products.append({
                "id": item["id"],
                "name": item["name"],
                "price": item["price"],
                "image": item["image"],
                "quantity": quantity,
                "subtotal": subtotal
            })
            total += subtotal

    conn.close()
    return render_template("cart.html", products=products, total=total)


@app.route("/update_cart/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    quantity = int(request.form.get("quantity", 1))
    cart = session.get("cart", {})

    if quantity <= 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = quantity

    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/wishlist")
@login_required
def wishlist():
    conn = get_db_connection()
    items = conn.execute("""
        SELECT p.* FROM wishlist w
        JOIN products p ON p.id = w.product_id
        WHERE w.user_id = ?
        ORDER BY w.created_at DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("wishlist.html", products=items)


@app.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
@login_required
def toggle_wishlist(product_id):
    conn = get_db_connection()
    product = conn.execute("SELECT id, name FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        return jsonify({"ok": False, "message": "Product not found."}), 404

    existing = conn.execute(
        "SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?",
        (session["user_id"], product_id)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM wishlist WHERE id = ?", (existing["id"],))
        wishlisted = False
    else:
        conn.execute(
            "INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)",
            (session["user_id"], product_id)
        )
        wishlisted = True

    conn.commit()
    count = conn.execute(
        "SELECT COUNT(*) FROM wishlist WHERE user_id = ?",
        (session["user_id"],)
    ).fetchone()[0]
    conn.close()
    return jsonify({"ok": True, "wishlisted": wishlisted, "count": count})


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        conn = get_db_connection()

        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing:
            conn.close()
            flash("Email already registered.", "danger")
            return render_template("register.html")

        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password))
        )
        conn.commit()
        conn.close()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Welcome back to LumiStore.", "success")
            return redirect(url_for("index"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_name", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_data = session.get("cart", {})

    if not cart_data:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))

    conn = get_db_connection()
    products = []
    total = 0

    for product_id, quantity in cart_data.items():
        item = conn.execute(
            "SELECT * FROM products WHERE id = ?", (int(product_id),)
        ).fetchone()

        if item:
            subtotal = item["price"] * quantity
            products.append({
                "id": item["id"],
                "name": item["name"],
                "price": item["price"],
                "quantity": quantity,
                "subtotal": subtotal
            })
            total += subtotal

    if request.method == "POST":
        address = request.form.get("address", "").strip()
        payment_method = request.form.get("payment_method", "COD")
        allowed_payments = {"UPI", "CARD", "NETBANKING", "COD"}

        if not address:
            conn.close()
            flash("Please enter your delivery address.", "danger")
            return render_template("checkout.html", products=products, total=total)
        if payment_method not in allowed_payments:
            conn.close()
            flash("Please select a valid payment method.", "danger")
            return render_template("checkout.html", products=products, total=total)

        order_cursor = conn.execute(
            "INSERT INTO orders (user_id, total, status, payment_method) VALUES (?, ?, ?, ?)",
            (session["user_id"], total, "Processing", payment_method)
        )
        order_id = order_cursor.lastrowid

        for item in products:
            conn.execute("""
                INSERT INTO order_items
                (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)
            """, (
                order_id,
                item["id"],
                item["quantity"],
                item["price"]
            ))

        conn.commit()
        conn.close()
        session["cart"] = {}
        return render_template("success.html", order_id=order_id, total=total)

    conn.close()
    return render_template("checkout.html", products=products, total=total)


@app.route("/orders")
@login_required
def orders():
    conn = get_db_connection()
    order_list = conn.execute("""
        SELECT * FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()
    conn.close()

    return render_template("orders.html", orders=order_list)


@app.route("/api/products")
def api_products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify([dict(product) for product in products])


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
