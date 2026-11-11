"""
============================================================
              HISAAB - SQLITE3 DATABASE ENGINE
       Project Developed by: Prerna Taktode (Solo Project)
============================================================
Persistent SQLite3 database layer handling Products, Customers,
Bills, Bill Items, Automatic Stock Deductions, Payment Status,
and Dynamic Business Analytics.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import re

DB_PATH = Path(__file__).parent / "billing_system.db"


def get_db_connection():
    """Get a SQLite database connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables and seed initial catalog if empty."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Products Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code INTEGER UNIQUE,
                name TEXT NOT NULL,
                sku TEXT UNIQUE NOT NULL,
                barcode TEXT UNIQUE,
                category TEXT NOT NULL DEFAULT 'General',
                selling_price REAL NOT NULL CHECK(selling_price >= 0),
                cost_price REAL DEFAULT 0.0 CHECK(cost_price >= 0),
                stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK(stock_quantity >= 0),
                low_stock_threshold INTEGER NOT NULL DEFAULT 5 CHECK(low_stock_threshold >= 0),
                icon TEXT DEFAULT '🛍️',
                created_date TEXT NOT NULL,
                updated_date TEXT NOT NULL
            )
        """)

        # 2. Customers Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                address TEXT,
                created_date TEXT NOT NULL,
                updated_date TEXT NOT NULL
            )
        """)

        # 3. Bills / Sales Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE NOT NULL,
                customer_id INTEGER,
                customer_name TEXT NOT NULL,
                customer_phone TEXT,
                customer_email TEXT,
                customer_address TEXT,
                sale_date TEXT NOT NULL,
                subtotal REAL NOT NULL,
                discount_percent REAL DEFAULT 0.0,
                discount_amount REAL DEFAULT 0.0,
                tax REAL DEFAULT 0.0,
                total_amount REAL NOT NULL,
                paid_amount REAL NOT NULL CHECK(paid_amount >= 0),
                pending_amount REAL NOT NULL CHECK(pending_amount >= 0),
                payment_status TEXT NOT NULL, -- 'Paid', 'Partially Paid', 'Pending', 'Cancelled'
                payment_method TEXT NOT NULL,
                developer TEXT DEFAULT 'Prerna Taktode',
                created_date TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
            )
        """)

        # 4. Bill Items Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                sku TEXT,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_price REAL NOT NULL CHECK(unit_price >= 0),
                discount REAL DEFAULT 0.0,
                subtotal REAL NOT NULL,
                FOREIGN KEY(bill_id) REFERENCES bills(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
        """)

        # Indexes for fast lookup & search
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_invoice ON bills(invoice_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_status ON bills(payment_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bill_items_bill_id ON bill_items(bill_id)")

        # Seed initial products if catalog is empty
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            initial_products = [
                (101, "Milk (1L)", "SKU-MLK-101", "890101000101", "Dairy", 60.0, 48.0, 25, 5, "🥛", now_str, now_str),
                (102, "Bread", "SKU-BRD-102", "890101000102", "Bakery", 40.0, 30.0, 20, 5, "🍞", now_str, now_str),
                (103, "Butter (100g)", "SKU-BTR-103", "890101000103", "Dairy", 55.0, 44.0, 15, 4, "🧈", now_str, now_str),
                (104, "Eggs (1 Dozen)", "SKU-EGG-104", "890101000104", "Dairy", 85.0, 70.0, 30, 8, "🥚", now_str, now_str),
                (105, "Rice (1kg)", "SKU-RIC-105", "890101000105", "Groceries", 70.0, 55.0, 40, 10, "🍚", now_str, now_str),
                (106, "Wheat Flour (1kg)", "SKU-WHT-106", "890101000106", "Groceries", 45.0, 35.0, 35, 10, "🌾", now_str, now_str),
                (107, "Sugar (1kg)", "SKU-SGR-107", "890101000107", "Groceries", 42.0, 34.0, 50, 10, "🍬", now_str, now_str),
                (108, "Tea Powder (250g)", "SKU-TEA-108", "890101000108", "Beverages", 110.0, 85.0, 18, 5, "🍵", now_str, now_str),
                (109, "Coffee (50g)", "SKU-COF-109", "890101000109", "Beverages", 95.0, 75.0, 22, 5, "☕", now_str, now_str),
                (110, "Biscuits Pack", "SKU-BIS-110", "890101000110", "Snacks", 30.0, 22.0, 40, 8, "🍪", now_str, now_str),
            ]
            cursor.executemany("""
                INSERT INTO products 
                (code, name, sku, barcode, category, selling_price, cost_price, stock_quantity, low_stock_threshold, icon, created_date, updated_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, initial_products)
            cursor.execute("DELETE FROM products WHERE name LIKE 'Almond Milk%'")

        # Seed initial customers if customer table is empty
        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] == 0:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            initial_customers = [
                ("Guest Customer", "9876543210", "guest@store.local", "In-Store Counter", now_str, now_str),
                ("Rahul Sharma", "9823012345", "rahul.sharma@example.com", "Flat 402, Green Valley Apartments, Mumbai", now_str, now_str),
                ("Pooja Patel", "9898765432", "pooja.patel@example.com", "12 Park Street, Ahmedabad", now_str, now_str),
                ("Amit Verma", "9711223344", "amit.verma@example.com", "Sector 15, Rohini, New Delhi", now_str, now_str)
            ]
            cursor.executemany("""
                INSERT INTO customers (name, phone, email, address, created_date, updated_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, initial_customers)

        conn.commit()


# ============================================================
# PRODUCT CRUD & SEARCH
# ============================================================

def get_all_products(search_query=None, category=None):
    """Fetch products with optional search (name, SKU, barcode, category)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if search_query:
            term = f"%{search_query.strip()}%"
            query += " AND (name LIKE ? OR sku LIKE ? OR barcode LIKE ? OR category LIKE ? OR CAST(code AS TEXT) LIKE ?)"
            params.extend([term, term, term, term, term])

        if category and category != "All":
            query += " AND category = ?"
            params.append(category.strip())

        query += " ORDER BY id ASC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_product_by_id(product_id):
    """Retrieve single product by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_product_by_code_or_id(code_or_id):
    """Retrieve product matching either code or id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE code = ? OR id = ?", (code_or_id, code_or_id))
        row = cursor.fetchone()
        return dict(row) if row else None


def validate_product_data(data, product_id=None):
    """Validate product inputs for constraints and uniqueness."""
    name = str(data.get("name", "")).strip()
    if not name:
        return "Product name is required."

    sku = str(data.get("sku", "")).strip().upper()
    if not sku:
        return "SKU is required."

    barcode = str(data.get("barcode", "")).strip() or None
    category = str(data.get("category", "General")).strip() or "General"

    try:
        selling_price = float(data.get("selling_price", 0.0))
        if selling_price < 0:
            return "Selling price cannot be negative."
    except (ValueError, TypeError):
        return "Selling price must be a valid number."

    try:
        cost_price = float(data.get("cost_price", 0.0))
        if cost_price < 0:
            return "Cost price cannot be negative."
    except (ValueError, TypeError):
        return "Cost price must be a valid number."

    try:
        stock_quantity = int(data.get("stock_quantity", 0))
        if stock_quantity < 0:
            return "Stock quantity cannot be negative."
    except (ValueError, TypeError):
        return "Stock quantity must be an integer."

    try:
        low_stock_threshold = int(data.get("low_stock_threshold", 5))
        if low_stock_threshold < 0:
            return "Low stock threshold cannot be negative."
    except (ValueError, TypeError):
        return "Low stock threshold must be an integer."

    # Check uniqueness of SKU and Barcode
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # SKU uniqueness
        if product_id:
            cursor.execute("SELECT id FROM products WHERE sku = ? AND id != ?", (sku, product_id))
        else:
            cursor.execute("SELECT id FROM products WHERE sku = ?", (sku,))
        if cursor.fetchone():
            return f"Product with SKU '{sku}' already exists."

        # Barcode uniqueness
        if barcode:
            if product_id:
                cursor.execute("SELECT id FROM products WHERE barcode = ? AND id != ?", (barcode, product_id))
            else:
                cursor.execute("SELECT id FROM products WHERE barcode = ?", (barcode,))
            if cursor.fetchone():
                return f"Product with Barcode '{barcode}' already exists."

    return None


def create_product(data):
    """Create a new product in the database."""
    val_err = validate_product_data(data)
    if val_err:
        raise ValueError(val_err)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Auto generate code if not supplied
        code = data.get("code")
        if not code:
            cursor.execute("SELECT MAX(COALESCE(code, 100)) FROM products")
            max_code = cursor.fetchone()[0] or 100
            code = max_code + 1

        cursor.execute("""
            INSERT INTO products 
            (code, name, sku, barcode, category, selling_price, cost_price, stock_quantity, low_stock_threshold, icon, created_date, updated_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            code,
            data["name"].strip(),
            data["sku"].strip().upper(),
            data.get("barcode", "").strip() or None,
            data.get("category", "General").strip() or "General",
            float(data.get("selling_price", 0.0)),
            float(data.get("cost_price", 0.0)),
            int(data.get("stock_quantity", 0)),
            int(data.get("low_stock_threshold", 5)),
            data.get("icon", "🛍️"),
            now_str,
            now_str
        ))
        conn.commit()
        return get_product_by_id(cursor.lastrowid)


def update_product(product_id, data):
    """Update an existing product."""
    val_err = validate_product_data(data, product_id=product_id)
    if val_err:
        raise ValueError(val_err)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET
                name = ?,
                sku = ?,
                barcode = ?,
                category = ?,
                selling_price = ?,
                cost_price = ?,
                stock_quantity = ?,
                low_stock_threshold = ?,
                icon = COALESCE(?, icon),
                updated_date = ?
            WHERE id = ?
        """, (
            data["name"].strip(),
            data["sku"].strip().upper(),
            data.get("barcode", "").strip() or None,
            data.get("category", "General").strip() or "General",
            float(data["selling_price"]),
            float(data.get("cost_price", 0.0)),
            int(data["stock_quantity"]),
            int(data.get("low_stock_threshold", 5)),
            data.get("icon"),
            now_str,
            product_id
        ))
        conn.commit()
        return get_product_by_id(product_id)


def delete_product(product_id):
    """Delete a product if not referenced in active sales."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bill_items WHERE product_id = ?", (product_id,))
        if cursor.fetchone()[0] > 0:
            raise ValueError("Cannot delete this product because it is part of existing sales records. You may set its stock to 0 instead.")

        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        return True


# ============================================================
# CUSTOMER CRUD & SEARCH
# ============================================================

def validate_phone(phone_str):
    """Validate phone number: digits and optional leading +, min 7 digits."""
    cleaned = re.sub(r"[\s\-\(\)]", "", str(phone_str))
    if not re.match(r"^\+?[0-9]{7,15}$", cleaned):
        return False
    return True


def validate_customer_data(data, customer_id=None):
    """Validate customer input."""
    name = str(data.get("name", "")).strip()
    if not name:
        return "Customer name is required."

    phone = str(data.get("phone", "")).strip()
    if not phone:
        return "Customer phone number is required."
    if not validate_phone(phone):
        return "Please enter a valid phone number (e.g. 9823012345 or +919823012345)."

    email = str(data.get("email", "")).strip()
    if email and "@" not in email:
        return "Please enter a valid email address."

    return None


def get_all_customers(search_query=None):
    """Fetch customers with optional search by name, phone, or email."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM customers WHERE 1=1"
        params = []

        if search_query:
            term = f"%{search_query.strip()}%"
            query += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)"
            params.extend([term, term, term])

        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_customer_by_id(customer_id):
    """Retrieve single customer by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_customer(data):
    """Add a new customer to SQLite."""
    val_err = validate_customer_data(data)
    if val_err:
        raise ValueError(val_err)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customers (name, phone, email, address, created_date, updated_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["name"].strip(),
            data["phone"].strip(),
            data.get("email", "").strip() or None,
            data.get("address", "").strip() or None,
            now_str,
            now_str
        ))
        conn.commit()
        return get_customer_by_id(cursor.lastrowid)


def update_customer(customer_id, data):
    """Update customer details."""
    val_err = validate_customer_data(data, customer_id=customer_id)
    if val_err:
        raise ValueError(val_err)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE customers SET
                name = ?,
                phone = ?,
                email = ?,
                address = ?,
                updated_date = ?
            WHERE id = ?
        """, (
            data["name"].strip(),
            data["phone"].strip(),
            data.get("email", "").strip() or None,
            data.get("address", "").strip() or None,
            now_str,
            customer_id
        ))
        conn.commit()
        return get_customer_by_id(customer_id)


def delete_customer(customer_id):
    """Delete a customer."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        return True


def get_customer_purchase_history(customer_id):
    """Retrieve all past bills for a specific customer."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM bills 
            WHERE customer_id = ? 
            ORDER BY id DESC
        """, (customer_id,))
        bills = [dict(b) for b in cursor.fetchall()]

        # Attach items to each bill
        for bill in bills:
            cursor.execute("SELECT * FROM bill_items WHERE bill_id = ?", (bill["id"],))
            bill["items"] = [dict(i) for i in cursor.fetchall()]

        return bills


# ============================================================
# BILLING, STOCK TRANSACTIONS & PAYMENT STATUS
# ============================================================

def determine_payment_status(total_amount, paid_amount):
    """
    Determine payment status:
    - Paid: paid_amount >= total_amount
    - Partially Paid: 0 < paid_amount < total_amount
    - Pending: paid_amount == 0
    """
    total = round(float(total_amount), 2)
    paid = round(float(paid_amount), 2)

    if paid >= total:
        return "Paid", 0.0
    elif paid > 0:
        return "Partially Paid", round(total - paid, 2)
    else:
        return "Pending", total


def create_bill_transaction(bill_payload):
    """
    Atomic Database Transaction:
    1. Validates cart items and availability.
    2. Validates and checks stock for each product.
    3. Fails & rolls back if stock is insufficient:
       'Current Stock - Sold Quantity = Updated Stock'.
    4. Automatically calculates payment status & pending dues:
       'Pending Amount = Total Amount - Paid Amount'.
    5. Deducts stock quantity atomically.
    6. Inserts bill into 'bills'.
    7. Inserts bill items into 'bill_items'.
    8. Commits transaction and returns full invoice record.
    """
    items = bill_payload.get("items", [])
    if not items:
        raise ValueError("Cart cannot be empty. Please add items to bill.")

    customer_id = bill_payload.get("customerId")
    customer_name = str(bill_payload.get("customerName", "Guest Customer")).strip() or "Guest Customer"
    customer_phone = str(bill_payload.get("customerPhone", "")).strip() or None
    customer_email = str(bill_payload.get("customerEmail", "")).strip() or None
    customer_address = str(bill_payload.get("customerAddress", "")).strip() or None
    payment_method = str(bill_payload.get("paymentMethod", "Cash")).strip() or "Cash"
    discount_percent = max(0.0, min(100.0, float(bill_payload.get("discountPercent", 0.0))))

    # Connect with manual transaction handling for strict ACID atomicity
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE TRANSACTION")

        # If customer details were entered and customer_id is None, link or create
        if not customer_id and customer_phone:
            cursor.execute("SELECT id, name FROM customers WHERE phone = ?", (customer_phone,))
            existing = cursor.fetchone()
            if existing:
                customer_id = existing["id"]
            else:
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO customers (name, phone, email, address, created_date, updated_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (customer_name, customer_phone, customer_email, customer_address, now_s, now_s))
                customer_id = cursor.lastrowid
        elif customer_id:
            cursor.execute("SELECT name, phone, email, address FROM customers WHERE id = ?", (customer_id,))
            cust = cursor.fetchone()
            if cust:
                customer_name = cust["name"]
                customer_phone = cust["phone"]
                customer_email = cust["email"]
                customer_address = cust["address"]

        # 1. Validate items and verify available stock
        receipt_items = []
        subtotal = 0.0

        for item in items:
            code_or_id = item.get("code") or item.get("id")
            qty = int(item.get("qty", 1))

            if qty <= 0:
                raise ValueError(f"Quantity must be greater than 0 for all items.")

            # Look up product
            cursor.execute("SELECT * FROM products WHERE id = ? OR code = ?", (code_or_id, code_or_id))
            prod = cursor.fetchone()
            if not prod:
                raise ValueError(f"Product with code/ID '{code_or_id}' was not found in database.")

            # Stock check
            avail_stock = prod["stock_quantity"]
            if qty > avail_stock:
                raise ValueError(
                    f"Insufficient stock for '{prod['name']}'. Available stock: {avail_stock} units, requested: {qty} units."
                )

            line_total = round(prod["selling_price"] * qty, 2)
            subtotal += line_total

            receipt_items.append({
                "product_id": prod["id"],
                "code": prod["code"],
                "name": prod["name"],
                "sku": prod["sku"],
                "unit_price": prod["selling_price"],
                "qty": qty,
                "subtotal": line_total,
                "current_stock": avail_stock
            })

        # 2. Financial Computations
        subtotal = round(subtotal, 2)
        discount_amount = round(subtotal * (discount_percent / 100.0), 2)
        taxable_subtotal = max(0.0, round(subtotal - discount_amount, 2))
        tax = round(taxable_subtotal * 0.05, 2)  # 5% GST
        grand_total = round(taxable_subtotal + tax, 2)

        # 3. Paid Amount & Payment Status Validation
        raw_paid = bill_payload.get("paidAmount")
        if raw_paid is None or raw_paid == "":
            paid_amount = grand_total  # Default to full payment
        else:
            paid_amount = round(float(raw_paid), 2)

        if paid_amount < 0:
            raise ValueError("Paid amount cannot be negative.")
        if paid_amount > grand_total:
            raise ValueError(f"Paid amount (₹{paid_amount:.2f}) cannot exceed bill total (₹{grand_total:.2f}).")

        payment_status, pending_amount = determine_payment_status(grand_total, paid_amount)

        # 4. Generate Unique Invoice Number
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        date_display = now.strftime("%d-%m-%Y %H:%M:%S")
        cursor.execute("SELECT COUNT(*) FROM bills")
        next_seq = cursor.fetchone()[0] + 1
        invoice_number = f"INV-{now.strftime('%Y%m%d')}-{next_seq:04d}"

        # 5. Insert Bill Header
        cursor.execute("""
            INSERT INTO bills 
            (invoice_number, customer_id, customer_name, customer_phone, customer_email, customer_address,
             sale_date, subtotal, discount_percent, discount_amount, tax, total_amount, paid_amount, pending_amount,
             payment_status, payment_method, developer, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_number,
            customer_id,
            customer_name,
            customer_phone,
            customer_email,
            customer_address,
            date_display,
            subtotal,
            discount_percent,
            discount_amount,
            tax,
            grand_total,
            paid_amount,
            pending_amount,
            payment_status,
            payment_method,
            "Prerna Taktode",
            now_str
        ))
        bill_id = cursor.lastrowid

        # 6. Deduct Stock & Insert Bill Items Atomically
        for item in receipt_items:
            # Stock deduction: Current Stock - Sold Quantity = Updated Stock
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = stock_quantity - ?, updated_date = ?
                WHERE id = ?
            """, (item["qty"], now_str, item["product_id"]))

            cursor.execute("""
                INSERT INTO bill_items 
                (bill_id, product_id, product_name, sku, quantity, unit_price, discount, subtotal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bill_id,
                item["product_id"],
                item["name"],
                item["sku"],
                item["qty"],
                item["unit_price"],
                0.0,
                item["subtotal"]
            ))

        # Commit entire transaction
        conn.commit()

        # Build response representation matching existing receipt format
        return {
            "success": True,
            "id": bill_id,
            "invoiceNumber": invoice_number,
            "date": date_display,
            "customerId": customer_id,
            "customerName": customer_name,
            "customerPhone": customer_phone,
            "customerEmail": customer_email,
            "customerAddress": customer_address,
            "paymentMethod": payment_method,
            "items": [
                {
                    "id": item["product_id"],
                    "code": item["code"],
                    "name": item["name"],
                    "sku": item["sku"],
                    "price": item["unit_price"],
                    "qty": item["qty"],
                    "total": item["subtotal"]
                }
                for item in receipt_items
            ],
            "itemsCount": sum(i["qty"] for i in receipt_items),
            "subtotal": subtotal,
            "discountPercent": discount_percent,
            "discountAmount": discount_amount,
            "taxableSubtotal": taxable_subtotal,
            "tax": tax,
            "taxRatePercent": 5,
            "grandTotal": grand_total,
            "totalAmount": grand_total,
            "paidAmount": paid_amount,
            "pendingAmount": pending_amount,
            "paymentStatus": payment_status,
            "developer": "Prerna Taktode"
        }

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def cancel_bill_transaction(bill_id):
    """
    Atomically cancels a bill and restores sold stock back to products:
    'Current Stock + Sold Quantity = Restored Stock'.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE TRANSACTION")

        cursor.execute("SELECT * FROM bills WHERE id = ?", (bill_id,))
        bill = cursor.fetchone()
        if not bill:
            raise ValueError(f"Bill with ID {bill_id} not found.")

        if bill["payment_status"] == "Cancelled":
            raise ValueError("Bill is already cancelled.")

        # Get items to restore
        cursor.execute("SELECT product_id, quantity FROM bill_items WHERE bill_id = ?", (bill_id,))
        items = cursor.fetchall()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for it in items:
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = stock_quantity + ?, updated_date = ?
                WHERE id = ?
            """, (it["quantity"], now_str, it["product_id"]))

        # Mark bill as Cancelled with 0 pending dues
        cursor.execute("""
            UPDATE bills 
            SET payment_status = 'Cancelled', pending_amount = 0.0 
            WHERE id = ?
        """, (bill_id,))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_all_bills(search_query=None, payment_status=None):
    """Retrieve bills history with optional search and payment status filter."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM bills WHERE 1=1"
        params = []

        if payment_status and payment_status != "All":
            query += " AND payment_status = ?"
            params.append(payment_status)

        if search_query:
            term = f"%{search_query.strip()}%"
            query += " AND (invoice_number LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ?)"
            params.extend([term, term, term])

        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        bills = [dict(b) for b in cursor.fetchall()]

        for b in bills:
            cursor.execute("SELECT * FROM bill_items WHERE bill_id = ?", (b["id"],))
            b["items"] = [
                {
                    "productId": it["product_id"],
                    "name": it["product_name"],
                    "sku": it["sku"],
                    "qty": it["quantity"],
                    "price": it["unit_price"],
                    "total": it["subtotal"]
                }
                for it in cursor.fetchall()
            ]
            b["itemsCount"] = sum(i["qty"] for i in b["items"])
            # Aliases for frontend compatibility
            b["invoiceNumber"] = b["invoice_number"]
            b["customerName"] = b["customer_name"]
            b["customerPhone"] = b["customer_phone"]
            b["customerEmail"] = b["customer_email"]
            b["customerAddress"] = b["customer_address"]
            b["paymentMethod"] = b["payment_method"]
            b["grandTotal"] = b["total_amount"]
            b["totalAmount"] = b["total_amount"]
            b["paidAmount"] = b["paid_amount"]
            b["pendingAmount"] = b["pending_amount"]
            b["paymentStatus"] = b["payment_status"]
            b["discountPercent"] = b["discount_percent"]
            b["discountAmount"] = b["discount_amount"]
            b["date"] = b["sale_date"]

        return bills


def get_bill_by_id_or_invoice(identifier):
    """Retrieve bill with items by either ID or Invoice Number."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bills WHERE id = ? OR invoice_number = ?", (identifier, identifier))
        row = cursor.fetchone()
        if not row:
            return None

        bill = dict(row)
        cursor.execute("SELECT * FROM bill_items WHERE bill_id = ?", (bill["id"],))
        bill["items"] = [
            {
                "productId": it["product_id"],
                "name": it["product_name"],
                "sku": it["sku"],
                "qty": it["quantity"],
                "price": it["unit_price"],
                "total": it["subtotal"]
            }
            for it in cursor.fetchall()
        ]
        bill["itemsCount"] = sum(i["qty"] for i in bill["items"])
        bill["invoiceNumber"] = bill["invoice_number"]
        bill["customerName"] = bill["customer_name"]
        bill["customerPhone"] = bill["customer_phone"]
        bill["customerEmail"] = bill["customer_email"]
        bill["customerAddress"] = bill["customer_address"]
        bill["paymentMethod"] = bill["payment_method"]
        bill["grandTotal"] = bill["total_amount"]
        bill["totalAmount"] = bill["total_amount"]
        bill["paidAmount"] = bill["paid_amount"]
        bill["pendingAmount"] = bill["pending_amount"]
        bill["paymentStatus"] = bill["payment_status"]
        bill["discountPercent"] = bill["discount_percent"]
        bill["discountAmount"] = bill["discount_amount"]
        bill["date"] = bill["sale_date"]
        return bill


# ============================================================
# REAL-TIME DASHBOARD & SALES STATISTICS
# ============================================================

def get_dashboard_statistics(period="All Time"):
    """
    Computes real-time dynamic statistics directly from SQLite3:
    - Revenue (Total & Filtered: Today, This Week, This Month, All Time)
    - Total Pending Customer Dues & Count of Pending/Partially Paid Bills
    - Low Stock Products (stock_quantity <= low_stock_threshold)
    - Product Statistics (Total products, total customers, total bills, total units sold)
    - Top Selling Products (ordered by quantity sold, showing name, SKU, units sold, revenue)
    - Sales summary (total revenue, paid amount, pending amount, transactions count)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Date filtering logic
        now = datetime.now()
        date_filter_clause = ""
        date_param = []

        if period == "Today":
            today_str = now.strftime("%d-%m-%Y")
            date_filter_clause = " AND sale_date LIKE ?"
            date_param = [f"{today_str}%"]
        elif period == "This Week":
            # Bills from past 7 days
            week_ago = now - timedelta(days=7)
            date_filter_clause = " AND created_date >= ?"
            date_param = [week_ago.strftime("%Y-%m-%d 00:00:00")]
        elif period == "This Month":
            month_str = now.strftime("%m-%Y")
            date_filter_clause = " AND sale_date LIKE ?"
            date_param = [f"%-{month_str}%"]

        # 1. Total Revenue for chosen period (excluding Cancelled)
        cursor.execute(
            f"SELECT COALESCE(SUM(total_amount), 0), COALESCE(SUM(paid_amount), 0), COALESCE(SUM(pending_amount), 0), COUNT(*) FROM bills WHERE payment_status != 'Cancelled'{date_filter_clause}",
            date_param
        )
        period_row = cursor.fetchone()
        period_revenue = round(period_row[0], 2)
        period_paid = round(period_row[1], 2)
        period_pending = round(period_row[2], 2)
        period_bills_count = period_row[3]

        # All-time revenue totals
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0), COALESCE(SUM(paid_amount), 0), COALESCE(SUM(pending_amount), 0) FROM bills WHERE payment_status != 'Cancelled'")
        all_time_row = cursor.fetchone()
        total_revenue_all_time = round(all_time_row[0], 2)
        total_paid_all_time = round(all_time_row[1], 2)

        # 2. Total Pending Dues (all active pending customer balances)
        cursor.execute("SELECT COALESCE(SUM(pending_amount), 0), COUNT(*) FROM bills WHERE pending_amount > 0 AND payment_status != 'Cancelled'")
        pending_row = cursor.fetchone()
        total_pending_dues = round(pending_row[0], 2)
        bills_with_pending_count = pending_row[1]

        # 3. Product Statistics
        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM customers")
        total_customers = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM bills WHERE payment_status != 'Cancelled'")
        total_bills = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(bi.quantity), 0) 
            FROM bill_items bi 
            JOIN bills b ON bi.bill_id = b.id 
            WHERE b.payment_status != 'Cancelled'
        """)
        total_units_sold = cursor.fetchone()[0]

        # 4. Low Stock Products (stock_quantity <= low_stock_threshold)
        cursor.execute("""
            SELECT id, code, name, sku, barcode, category, stock_quantity, low_stock_threshold, selling_price
            FROM products 
            WHERE stock_quantity <= low_stock_threshold 
            ORDER BY stock_quantity ASC
        """)
        low_stock_products = [dict(p) for p in cursor.fetchall()]

        # 5. Top Selling Products based on actual units sold in SQLite
        cursor.execute("""
            SELECT 
                bi.product_id,
                bi.product_name,
                bi.sku,
                COALESCE(p.barcode, '') AS barcode,
                COALESCE(p.category, 'General') AS category,
                SUM(bi.quantity) AS total_sold,
                ROUND(SUM(bi.subtotal), 2) AS revenue_generated
            FROM bill_items bi
            JOIN bills b ON bi.bill_id = b.id
            LEFT JOIN products p ON bi.product_id = p.id
            WHERE b.payment_status != 'Cancelled'
            GROUP BY bi.product_id, bi.product_name, bi.sku
            ORDER BY total_sold DESC
            LIMIT 6
        """)
        top_selling = [dict(r) for r in cursor.fetchall()]

        # 6. Payment Status Distribution
        cursor.execute("""
            SELECT payment_status, COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total
            FROM bills
            GROUP BY payment_status
        """)
        status_breakdown = {r["payment_status"]: {"count": r["count"], "total": round(r["total"], 2)} for r in cursor.fetchall()}

        return {
            "period": period,
            "revenue": {
                "periodRevenue": period_revenue,
                "periodPaid": period_paid,
                "periodPending": period_pending,
                "totalRevenueAllTime": total_revenue_all_time,
                "totalPaidAllTime": total_paid_all_time
            },
            "pendingDues": {
                "totalPendingDues": total_pending_dues,
                "pendingBillsCount": bills_with_pending_count
            },
            "productStats": {
                "totalProducts": total_products,
                "totalCustomers": total_customers,
                "totalBills": total_bills,
                "totalUnitsSold": total_units_sold
            },
            "salesStats": {
                "totalSales": total_bills,
                "periodSales": period_bills_count,
                "totalRevenue": total_revenue_all_time,
                "periodRevenue": period_revenue,
                "totalUnitsSold": total_units_sold,
                "paidAmount": total_paid_all_time,
                "pendingAmount": total_pending_dues,
                "transactionsCount": total_bills,
                "statusBreakdown": status_breakdown
            },
            "lowStockProducts": low_stock_products,
            "lowStockCount": len(low_stock_products),
            "topSellingProducts": top_selling
        }


# Initialize DB on import
init_db()
