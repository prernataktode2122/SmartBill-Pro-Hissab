"""
============================================================
              HISAAB - BILLING SYSTEM (CLI)
        Project Developed by: Prerna Taktode (Solo Project)
============================================================
A simple, clean, and lightweight Python billing system powered
by persistent SQLite3 database, automatic stock control,
payment status tracking, and sales analytics.
"""

from datetime import datetime
import database

database.init_db()


def display_menu():
    """Display available items in the SQLite database with stock."""
    products = database.get_all_products()
    print("\n" + "=" * 70)
    print("                      AVAILABLE PRODUCTS (SQLITE3)")
    print("=" * 70)
    print(f"{'Code':<6} {'Item Name':<22} {'SKU':<14} {'Price (Rs)':>10} {'Stock':>8} {'Status':>8}")
    print("-" * 70)
    for item in products:
        stock = item["stock_quantity"]
        thresh = item["low_stock_threshold"]
        status = "OUT" if stock == 0 else ("LOW" if stock <= thresh else "OK")
        print(f"{item['code']:<6} {item['name']:<22} {item['sku']:<14} {item['selling_price']:>10.2f} {stock:>8} {status:>8}")
    print("=" * 70)


def generate_bill_interactive():
    """Workflow to create a new customer bill with live stock validation and payment tracking."""
    products_list = database.get_all_products()
    prod_map = {p["code"]: p for p in products_list}

    print("\n--- CREATE NEW BILL ---")
    customer_name = input("Enter Customer Name [Guest Customer]: ").strip() or "Guest Customer"
    customer_phone = input("Enter Customer Phone (e.g. 9823012345): ").strip() or "9876543210"
    payment_method = input("Enter Payment Method (Cash / UPI / Card) [Cash]: ").strip() or "Cash"

    cart = []
    display_menu()

    while True:
        choice = input("\nEnter Product Code to add (or '0' to checkout): ").strip()
        if choice == '0':
            break

        if not choice.isdigit():
            print("Invalid input! Enter a numeric code.")
            continue

        code = int(choice)
        if code not in prod_map:
            print("Item code not found in database! Choose from menu.")
            continue

        prod = prod_map[code]
        avail = prod["stock_quantity"]

        # Check existing in cart
        existing_qty = sum(item["qty"] for item in cart if item["code"] == code)

        if avail <= 0:
            print(f"Sorry, '{prod['name']}' is OUT OF STOCK (0 available).")
            continue

        try:
            qty = int(input(f"Enter quantity for '{prod['name']}' (Available: {avail - existing_qty}): "))
            if qty <= 0:
                print("Quantity must be greater than 0.")
                continue
            if (existing_qty + qty) > avail:
                print(f"Error: Insufficient stock! Available: {avail - existing_qty} units.")
                continue
        except ValueError:
            print("Invalid quantity! Enter an integer.")
            continue

        cart.append({
            "id": prod["id"],
            "code": prod["code"],
            "name": prod["name"],
            "sku": prod["sku"],
            "price": prod["selling_price"],
            "qty": qty,
            "total": prod["selling_price"] * qty
        })
        print(f"Added {qty} x {prod['name']} to cart.")

    if not cart:
        print("Cart is empty. Checkout cancelled.")
        return

    # Checkout Discount Prompt
    try:
        disc_input = input("\nEnter Discount % (0-100, press Enter for 0): ").strip()
        discount_pct = float(disc_input) if disc_input else 0.0
        discount_pct = max(0.0, min(100.0, discount_pct))
    except ValueError:
        discount_pct = 0.0

    # Calculate provisional totals
    subtotal = sum(item["total"] for item in cart)
    discount_amount = subtotal * (discount_pct / 100.0)
    taxable = max(0.0, subtotal - discount_amount)
    tax = taxable * 0.05
    grand_total = round(taxable + tax, 2)

    print(f"\nCalculated Bill Grand Total: Rs {grand_total:.2f}")

    # Paid Amount input
    while True:
        paid_input = input(f"Enter Paid Amount (Press Enter for Full Rs {grand_total:.2f}): ").strip()
        if not paid_input:
            paid_amount = grand_total
            break
        try:
            paid_amount = round(float(paid_input), 2)
            if paid_amount < 0:
                print("Paid amount cannot be negative.")
                continue
            if paid_amount > grand_total:
                print(f"Paid amount cannot exceed Grand Total (Rs {grand_total:.2f}).")
                continue
            break
        except ValueError:
            print("Please enter a valid amount.")

    # Execute atomic SQLite transaction
    payload = {
        "customerName": customer_name,
        "customerPhone": customer_phone,
        "paymentMethod": payment_method,
        "discountPercent": discount_pct,
        "paidAmount": paid_amount,
        "items": [{"id": item["id"], "code": item["code"], "qty": item["qty"]} for item in cart]
    }

    try:
        invoice = database.create_bill_transaction(payload)
    except Exception as ex:
        print(f"\nTransaction failed: {ex}")
        return

    # Print Official Invoice Receipt
    print("\n" + "=" * 58)
    print("                 HISAAB INVOICE RECEIPT")
    print("               Developer: Prerna Taktode")
    print("=" * 58)
    print(f"Invoice #     : {invoice['invoiceNumber']}")
    print(f"Customer Name : {invoice['customerName']}")
    print(f"Phone Number  : {invoice['customerPhone'] or 'N/A'}")
    print(f"Date & Time   : {invoice['date']}")
    print(f"Payment Mode  : {invoice['paymentMethod']}")
    print("-" * 58)
    print(f"{'Item':<22} {'SKU':<12} {'Qty':<5} {'Rate':>8} {'Total':>9}")
    print("-" * 58)

    for item in invoice["items"]:
        print(f"{item['name']:<22} {item['sku']:<12} {item['qty']:<5} {item['price']:>8.2f} {item['total']:>9.2f}")

    print("-" * 58)
    print(f"{'Subtotal:':<44} Rs {invoice['subtotal']:>10.2f}")
    if invoice['discountAmount'] > 0:
        disc_label = f"Discount ({invoice['discountPercent']} %):"
        print(f"{disc_label:<44} -Rs {invoice['discountAmount']:>9.2f}")
    print(f"{'Tax (5% GST):':<44} Rs {invoice['tax']:>10.2f}")
    print("=" * 58)
    print(f"{'GRAND TOTAL:':<44} Rs {invoice['grandTotal']:>10.2f}")
    print(f"{'Paid Amount:':<44} Rs {invoice['paidAmount']:>10.2f}")
    print(f"{'Pending Dues:':<44} Rs {invoice['pendingAmount']:>10.2f}")
    print(f"{'Payment Status:':<44} {invoice['paymentStatus']:>13}")
    print("=" * 58)
    print("       Thank You for Shopping With Us!")
    print("        Project Made by Prerna Taktode")
    print("=" * 58 + "\n")


def view_history():
    """Display past customer billing history from SQLite3."""
    bills = database.get_all_bills()
    print("\n" + "=" * 82)
    print("                       CUSTOMER BILLING HISTORY (SQLITE3)")
    print("                          Project by: Prerna Taktode")
    print("=" * 82)

    if not bills:
        print("No past orders found in database.")
        print("=" * 82 + "\n")
        return

    print(f"{'Invoice #':<18} {'Date':<18} {'Customer':<18} {'Total':>10} {'Paid':>8} {'Pending':>8} {'Status':>10}")
    print("-" * 82)
    for inv in bills:
        print(f"{inv['invoiceNumber']:<18} {inv['date'][:16]:<18} {inv['customerName'][:16]:<18} {inv['grandTotal']:>10.2f} {inv['paidAmount']:>8.2f} {inv['pendingAmount']:>8.2f} {inv['paymentStatus']:>10}")
    print("=" * 82 + "\n")


def view_dashboard_summary():
    """Display real-time business statistics from SQLite3."""
    stats = database.get_dashboard_statistics("All Time")
    rev = stats["revenue"]
    dues = stats["pendingDues"]
    pstats = stats["productStats"]
    low = stats["lowStockProducts"]
    top = stats["topSellingProducts"]

    print("\n" + "=" * 60)
    print("               BUSINESS DASHBOARD (SQLITE3)")
    print("                Project: Prerna Taktode")
    print("=" * 60)
    print(f"Total Revenue (All Time) : Rs {rev['totalRevenueAllTime']:.2f}")
    print(f"Total Paid Collected     : Rs {rev['totalPaidAllTime']:.2f}")
    print(f"Total Pending Dues       : Rs {dues['totalPendingDues']:.2f} ({dues['pendingBillsCount']} bills)")
    print(f"Total Products in Store  : {pstats['totalProducts']}")
    print(f"Total Customers          : {pstats['totalCustomers']}")
    print(f"Total Completed Bills    : {pstats['totalBills']}")
    print(f"Total Units Sold         : {pstats['totalUnitsSold']}")
    print("-" * 60)

    print("\n[LOW STOCK ALERTS]")
    if not low:
        print("  All products have healthy stock levels.")
    else:
        for p in low:
            print(f"  * {p['name']} ({p['sku']}): Stock = {p['stock_quantity']} (Threshold = {p['low_stock_threshold']})")

    print("\n[TOP SELLING PRODUCTS]")
    if not top:
        print("  No sales recorded yet.")
    else:
        for idx, t in enumerate(top, 1):
            print(f"  {idx}. {t['product_name']} ({t['sku']}) - {t['total_sold']} units sold | Rs {t['revenue_generated']:.2f}")

    print("=" * 60 + "\n")


def main():
    print("=" * 55)
    print("          HISAAB - BILLING SYSTEM (SQLITE3)")
    print("             Creator: Prerna Taktode")
    print("=" * 55)

    while True:
        print("\n--- MAIN MENU ---")
        print("1. Create New Bill (Live Stock & Payment Tracking)")
        print("2. View Customer Billing History")
        print("3. View Dashboard & Inventory Statistics")
        print("4. Display Product Catalog")
        print("5. Exit")

        choice = input("Enter choice (1-5): ").strip()
        if choice == '1':
            generate_bill_interactive()
        elif choice == '2':
            view_history()
        elif choice == '3':
            view_dashboard_summary()
        elif choice == '4':
            display_menu()
        elif choice == '5':
            print("\nThank you for using the system. Goodbye!")
            break
        else:
            print("Invalid selection. Please choose 1 to 5.")


if __name__ == "__main__":
    main()
