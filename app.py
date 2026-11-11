"""
============================================================
              HISAAB WEB BILLING SYSTEM (BACKEND)
       Project Developed by: Prerna Taktode 
============================================================
Lightweight Python HTTP server with SQLite3 persistence,
Product & Customer Management, Transactional Stock Control,
Payment Status Automation, and Dynamic Dashboard Analytics.
Zero external dependencies required - uses Python standard library.
"""

import http.server
import json
import socketserver
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import database

PORT = 5000
STATIC_DIR = Path(__file__).parent


class BillingRequestHandler(http.server.SimpleHTTPRequestHandler):
    def send_json(self, status_code, data):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def parse_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # 1. Products Catalog API
        if path == "/api/products":
            search_query = params.get("q", [""])[0].strip()
            category = params.get("category", [""])[0].strip()
            prods = database.get_all_products(search_query=search_query, category=category)
            # Add price alias for frontend compatibility
            for p in prods:
                p["price"] = p["selling_price"]
                p["stock"] = p["stock_quantity"]
            self.send_json(200, prods)

        # 2. Customers API
        elif path == "/api/customers":
            search_query = params.get("q", [""])[0].strip()
            customers = database.get_all_customers(search_query=search_query)
            self.send_json(200, customers)

        # 3. Customer Purchase History: /api/customers/<id>/history
        elif path.startswith("/api/customers/") and path.endswith("/history"):
            parts = path.strip("/").split("/")
            if len(parts) == 4:
                try:
                    cid = int(parts[2])
                    history = database.get_customer_purchase_history(cid)
                    self.send_json(200, history)
                    return
                except ValueError:
                    self.send_json(400, {"error": "Invalid customer ID"})
                    return

        # 4. Invoices / History API
        elif path == "/api/history":
            customer_query = params.get("customer", [""])[0].strip()
            status_query = params.get("status", ["All"])[0].strip()
            search_query = params.get("search", [""])[0].strip() or customer_query
            bills = database.get_all_bills(search_query=search_query, payment_status=status_query)
            self.send_json(200, bills)

        # 5. Dashboard Statistics API
        elif path == "/api/dashboard":
            period = params.get("period", ["All Time"])[0].strip()
            stats = database.get_dashboard_statistics(period=period)
            self.send_json(200, stats)

        # 6. Favicon
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()

        # 7. Static HTML & PDF Documents
        elif path in ("/", "/index.html"):
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                content = index_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")

        elif path.endswith(".pdf") or path.endswith(".html"):
            file_path = STATIC_DIR / path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                content = file_path.read_bytes()
                mime = "application/pdf" if path.endswith(".pdf") else "text/html; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, f"{path} not found")
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Transactional Checkout API
        if path == "/api/checkout":
            try:
                payload = self.parse_json_body()
            except Exception as e:
                self.send_json(400, {"error": "Invalid JSON format in checkout payload"})
                return

            try:
                invoice_data = database.create_bill_transaction(payload)
                self.send_json(200, invoice_data)
            except ValueError as ve:
                self.send_json(400, {"error": str(ve)})
            except Exception as ex:
                self.send_json(500, {"error": f"Internal billing transaction error: {str(ex)}"})

        # 2. Add Product API
        elif path == "/api/products":
            try:
                payload = self.parse_json_body()
                prod = database.create_product(payload)
                self.send_json(201, prod)
            except ValueError as ve:
                self.send_json(400, {"error": str(ve)})
            except Exception as ex:
                self.send_json(500, {"error": str(ex)})

        # 3. Add Customer API
        elif path == "/api/customers":
            try:
                payload = self.parse_json_body()
                cust = database.create_customer(payload)
                self.send_json(201, cust)
            except ValueError as ve:
                self.send_json(400, {"error": str(ve)})
            except Exception as ex:
                self.send_json(500, {"error": str(ex)})

        # 4. Cancel Bill API: /api/bills/<id>/cancel
        elif path.startswith("/api/bills/") and path.endswith("/cancel"):
            parts = path.strip("/").split("/")
            if len(parts) == 4:
                try:
                    bid = int(parts[2])
                    database.cancel_bill_transaction(bid)
                    self.send_json(200, {"success": True, "message": "Bill cancelled and stock restored successfully."})
                    return
                except ValueError as ve:
                    self.send_json(400, {"error": str(ve)})
                    return
                except Exception as ex:
                    self.send_json(500, {"error": str(ex)})
                    return
        else:
            self.send_error(404, "Endpoint not found")

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Update Product: /api/products/<id>
        if path.startswith("/api/products/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3:
                try:
                    pid = int(parts[2])
                    payload = self.parse_json_body()
                    updated = database.update_product(pid, payload)
                    self.send_json(200, updated)
                    return
                except ValueError as ve:
                    self.send_json(400, {"error": str(ve)})
                    return
                except Exception as ex:
                    self.send_json(500, {"error": str(ex)})
                    return

        # Update Customer: /api/customers/<id>
        elif path.startswith("/api/customers/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3:
                try:
                    cid = int(parts[2])
                    payload = self.parse_json_body()
                    updated = database.update_customer(cid, payload)
                    self.send_json(200, updated)
                    return
                except ValueError as ve:
                    self.send_json(400, {"error": str(ve)})
                    return
                except Exception as ex:
                    self.send_json(500, {"error": str(ex)})
                    return

        self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Delete Product: /api/products/<id>
        if path.startswith("/api/products/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3:
                try:
                    pid = int(parts[2])
                    database.delete_product(pid)
                    self.send_json(200, {"success": True, "message": "Product deleted successfully."})
                    return
                except ValueError as ve:
                    self.send_json(400, {"error": str(ve)})
                    return
                except Exception as ex:
                    self.send_json(500, {"error": str(ex)})
                    return

        # Delete Customer: /api/customers/<id>
        elif path.startswith("/api/customers/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3:
                try:
                    cid = int(parts[2])
                    database.delete_customer(cid)
                    self.send_json(200, {"success": True, "message": "Customer deleted successfully."})
                    return
                except ValueError as ve:
                    self.send_json(400, {"error": str(ve)})
                    return
                except Exception as ex:
                    self.send_json(500, {"error": str(ex)})
                    return

        self.send_error(404, "Endpoint not found")


def run():
    socketserver.TCPServer.allow_reuse_address = True
    database.init_db()
    with socketserver.TCPServer(("", PORT), BillingRequestHandler) as httpd:
        print("=" * 60)
        print("          HISAAB BILLING SYSTEM STARTED (SQLITE3)")
        print("             Creator: Prerna Taktode")
        print("=" * 60)
        print(f" Serving at: http://localhost:{PORT}")
        print(f" Database  : {database.DB_PATH}")
        print("Press Ctrl+C to stop the server.")
        print("=" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer shutting down. Goodbye!")


if __name__ == "__main__":
    run()
