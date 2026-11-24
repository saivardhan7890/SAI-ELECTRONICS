import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import traceback
from decimal import Decimal

from db import get_connection


# ---------------- PASSWORD FUNCTIONS ----------------

def hash_password(password):
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200000
    ).hex()
    return f"{salt}${password_hash}"


def verify_password(password, stored_hash):
    try:
        salt, original_hash = stored_hash.split("$", 1)
    except (AttributeError, ValueError):
        return False

    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200000
    ).hex()
    return hmac.compare_digest(candidate_hash, original_hash)


# ---------------- API RESPONSE ----------------

def api_response(status_code, data):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Admin-Key",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(data, default=str)
    }


# ---------------- REQUEST FUNCTIONS ----------------

def get_request_method(event):
    return (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or "GET"
    ).upper()


def get_request_path(event):
    path = event.get("rawPath") or event.get("path") or "/"
    return path.rstrip("/") or "/"


def parse_body(event):
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("Request body must be a JSON object")
    return parsed


# ---------------- CUSTOMER TABLE ----------------

def ensure_customers_table(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)
    connection.commit()


# ---------------- PRODUCTS API ----------------

def get_products():
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT product_id, name, price, category, stock, image_url
                FROM products
                ORDER BY product_id
            """)
            rows = cursor.fetchall()

        products = [
            {
                "id": row[0],
                "name": row[1],
                "price": float(row[2]),
                "category": row[3],
                "stock": row[4],
                "image_url": row[5]
            }
            for row in rows
        ]
        return api_response(200, {"success": True, "products": products})
    finally:
        connection.close()


# ---------------- CUSTOMER REGISTRATION ----------------

def register_customer(event):
    body = parse_body(event)
    name = body.get("name", "")
    email = body.get("email", "")
    password = body.get("password", "")

    if not all(isinstance(value, str) for value in (name, email, password)):
        return api_response(400, {
            "success": False,
            "message": "Name, email and password must be text"
        })

    name = name.strip()
    email = email.strip().lower()
    if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return api_response(400, {
            "success": False,
            "message": "A valid name and email are required"
        })

    if len(password) < 8:
        return api_response(400, {
            "success": False,
            "message": "Password must contain at least 8 characters"
        })

    connection = get_connection()
    try:
        ensure_customers_table(connection)
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO customers (name, email, password_hash)
                VALUES (%s, %s, %s)
            """, (name, email, hash_password(password)))
            customer_id = cursor.lastrowid

        connection.commit()
        return api_response(201, {
            "success": True,
            "message": "Registration successful",
            "customer_id": customer_id
        })
    except Exception as error:
        connection.rollback()
        if getattr(error, "args", [None])[0] == 1062:
            return api_response(409, {
                "success": False,
                "message": "Email already registered"
            })
        raise
    finally:
        connection.close()


# ---------------- CUSTOMER LOGIN ----------------

def login_customer(event):
    body = parse_body(event)
    email = body.get("email", "")
    password = body.get("password", "")

    if not isinstance(email, str) or not isinstance(password, str):
        return api_response(400, {
            "success": False,
            "message": "Email and password are required"
        })

    email = email.strip().lower()
    if not email or not password:
        return api_response(400, {
            "success": False,
            "message": "Email and password are required"
        })

    connection = get_connection()
    try:
        ensure_customers_table(connection)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT customer_id, name, password_hash
                FROM customers
                WHERE email = %s
                LIMIT 1
            """, (email,))
            customer = cursor.fetchone()

        if not customer or not verify_password(password, customer[2]):
            return api_response(401, {
                "success": False,
                "message": "Invalid email or password"
            })

        return api_response(200, {
            "success": True,
            "message": "Login successful",
            "customer": {"id": customer[0], "name": customer[1]}
        })
    finally:
        connection.close()


# ---------------- CREATE CUSTOMER ORDER ----------------

def create_order(event):
    body = parse_body(event)
    customer_id = body.get("customer_id")
    items = body.get("items")

    if not customer_id or not isinstance(items, list) or not items:
        return api_response(400, {
            "success": False,
            "message": "Customer ID and order items are required"
        })

    try:
        customer_id = int(customer_id)
        if customer_id <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return api_response(400, {"success": False, "message": "Invalid customer ID"})

    quantities = {}
    try:
        for item in items:
            if not isinstance(item, dict):
                raise ValueError()
            product_id = int(item["product_id"])
            quantity = int(item["quantity"])
            if product_id <= 0 or quantity <= 0:
                raise ValueError()
            quantities[product_id] = quantities.get(product_id, 0) + quantity
    except (KeyError, ValueError, TypeError):
        return api_response(400, {
            "success": False,
            "message": "Invalid product ID or quantity"
        })

    if any(quantity > 100 for quantity in quantities.values()):
        return api_response(400, {
            "success": False,
            "message": "Maximum quantity per product is 100"
        })

    connection = get_connection()
    try:
        total_amount = Decimal("0.00")
        order_products = []

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT customer_id FROM customers WHERE customer_id = %s",
                (customer_id,)
            )
            if not cursor.fetchone():
                connection.rollback()
                return api_response(404, {"success": False, "message": "Customer not found"})

            for product_id, quantity in sorted(quantities.items()):
                cursor.execute("""
                    SELECT product_id, name, price, stock
                    FROM products
                    WHERE product_id = %s
                    FOR UPDATE
                """, (product_id,))
                product = cursor.fetchone()

                if not product:
                    connection.rollback()
                    return api_response(404, {
                        "success": False,
                        "message": f"Product {product_id} not found"
                    })

                if product[3] is None or product[3] < quantity:
                    connection.rollback()
                    return api_response(400, {
                        "success": False,
                        "message": f"Insufficient stock for {product[1]}"
                    })

                price = Decimal(str(product[2]))
                total_amount += price * quantity
                order_products.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "price": price
                })

            cursor.execute("""
                INSERT INTO orders
                    (customer_id, total_amount, order_status, payment_status)
                VALUES (%s, %s, 'PENDING', 'PENDING')
            """, (customer_id, total_amount))
            order_id = cursor.lastrowid

            for item in order_products:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, price)
                    VALUES (%s, %s, %s, %s)
                """, (
                    order_id,
                    item["product_id"],
                    item["quantity"],
                    item["price"]
                ))

                cursor.execute("""
                    UPDATE products
                    SET stock = stock - %s
                    WHERE product_id = %s AND stock >= %s
                """, (item["quantity"], item["product_id"], item["quantity"]))

                if cursor.rowcount != 1:
                    raise ValueError("Stock changed while creating order. Please retry.")

        connection.commit()
        return api_response(201, {
            "success": True,
            "message": "Order created successfully. Payment is pending.",
            "order_id": order_id,
            "customer_id": customer_id,
            "total_amount": float(total_amount),
            "order_status": "PENDING",
            "payment_status": "PENDING"
        })
    except ValueError as error:
        connection.rollback()
        return api_response(400, {"success": False, "message": str(error)})
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# ---------------- MY ORDERS API ----------------

def get_my_orders(event):
    params = event.get("queryStringParameters") or {}
    customer_id = params.get("customer_id")

    if not customer_id or not str(customer_id).isdigit() or int(customer_id) <= 0:
        return api_response(400, {"success": False, "message": "Valid customer_id is required"})

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    o.order_id, o.total_amount, o.order_status,
                    o.payment_status, o.created_at, oi.product_id,
                    p.name AS product_name, oi.quantity, oi.price
                FROM orders o
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                LEFT JOIN products p ON oi.product_id = p.product_id
                WHERE o.customer_id = %s
                ORDER BY o.created_at DESC, o.order_id DESC
            """, (int(customer_id),))
            rows = cursor.fetchall()

        orders = {}
        for row in rows:
            order_id = row[0]
            if order_id not in orders:
                orders[order_id] = {
                    "order_id": order_id,
                    "total_amount": float(row[1]),
                    "order_status": row[2],
                    "payment_status": row[3],
                    "created_at": str(row[4]),
                    "items": []
                }
            if row[5] is not None:
                orders[order_id]["items"].append({
                    "product_id": row[5],
                    "product_name": row[6],
                    "quantity": row[7],
                    "price": float(row[8])
                })

        return api_response(200, {"success": True, "orders": list(orders.values())})
    finally:
        connection.close()


# ---------------- SUBMIT UPI PAYMENT REFERENCE ----------------

def submit_payment(event):
    body = parse_body(event)
    customer_id = body.get("customer_id")
    order_id = body.get("order_id")
    payment_reference = body.get("payment_reference", "")

    try:
        customer_id = int(customer_id)
        order_id = int(order_id)
    except (TypeError, ValueError):
        return api_response(400, {
            "success": False,
            "message": "Valid customer_id and order_id are required"
        })

    if customer_id <= 0 or order_id <= 0:
        return api_response(400, {
            "success": False,
            "message": "Invalid customer_id or order_id"
        })

    if not isinstance(payment_reference, str):
        return api_response(400, {
            "success": False,
            "message": "UPI transaction reference must be text"
        })

    payment_reference = payment_reference.strip()
    if not re.fullmatch(r"[A-Za-z0-9-]{8,50}", payment_reference):
        return api_response(400, {
            "success": False,
            "message": "Enter a valid UPI transaction reference (8-50 letters or numbers)"
        })

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT payment_status
                FROM orders
                WHERE order_id = %s AND customer_id = %s
                LIMIT 1
            """, (order_id, customer_id))
            order = cursor.fetchone()

            if not order:
                return api_response(404, {
                    "success": False,
                    "message": "Order not found for this customer"
                })

            if str(order[0]).upper() == "PAID":
                return api_response(409, {
                    "success": False,
                    "message": "This order is already marked as paid"
                })

            cursor.execute("""
                SELECT order_id
                FROM orders
                WHERE payment_reference = %s AND order_id <> %s
                LIMIT 1
            """, (payment_reference, order_id))
            if cursor.fetchone():
                return api_response(409, {
                    "success": False,
                    "message": "This transaction reference has already been submitted"
                })

            cursor.execute("""
                UPDATE orders
                SET payment_method = 'UPI_QR',
                    payment_reference = %s,
                    payment_submitted_at = CURRENT_TIMESTAMP,
                    payment_status = 'PENDING_VERIFICATION'
                WHERE order_id = %s AND customer_id = %s
                  AND payment_status <> 'PAID'
            """, (payment_reference, order_id, customer_id))

            if cursor.rowcount != 1:
                connection.rollback()
                return api_response(409, {
                    "success": False,
                    "message": "Payment could not be submitted. Please refresh your orders."
                })

        connection.commit()
        return api_response(200, {
            "success": True,
            "message": "UPI reference submitted. Payment is pending manual verification.",
            "order_id": order_id,
            "payment_status": "PENDING_VERIFICATION"
        })
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# ---------------- ADMIN AUTHENTICATION ----------------

def verify_admin_request(event):
    """Check the admin key supplied in the x-admin-key header.

    This is a development/admin prototype. For production, replace this
    shared-key approach with a proper identity provider and API authorizer.
    """
    configured_key = os.environ.get("ADMIN_API_KEY", "")
    if not configured_key:
        return api_response(503, {
            "success": False,
            "message": "Admin API is not configured. Set ADMIN_API_KEY in Lambda environment variables."
        })

    headers = event.get("headers") or {}
    supplied_key = ""
    for name, value in headers.items():
        if str(name).lower() == "x-admin-key":
            supplied_key = str(value or "")
            break

    if not supplied_key or not hmac.compare_digest(supplied_key, configured_key):
        return api_response(401, {
            "success": False,
            "message": "Unauthorized admin request"
        })

    return None


# ---------------- ADMIN: LIST PENDING PAYMENTS ----------------

def get_pending_payments(event):
    auth_error = verify_admin_request(event)
    if auth_error:
        return auth_error

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    o.order_id,
                    o.customer_id,
                    c.name AS customer_name,
                    c.email AS customer_email,
                    o.total_amount,
                    o.payment_method,
                    o.payment_reference,
                    o.payment_status,
                    o.order_status,
                    o.payment_submitted_at,
                    o.created_at
                FROM orders o
                INNER JOIN customers c ON c.customer_id = o.customer_id
                WHERE o.payment_status = 'PENDING_VERIFICATION'
                ORDER BY o.payment_submitted_at ASC, o.order_id ASC
            """)
            rows = cursor.fetchall()

        payments = []
        for row in rows:
            payments.append({
                "order_id": row[0],
                "customer_id": row[1],
                "customer_name": row[2],
                "customer_email": row[3],
                "total_amount": float(row[4]),
                "payment_method": row[5],
                "payment_reference": row[6],
                "payment_status": row[7],
                "order_status": row[8],
                "payment_submitted_at": str(row[9]) if row[9] else None,
                "created_at": str(row[10]) if row[10] else None
            })

        return api_response(200, {
            "success": True,
            "count": len(payments),
            "payments": payments
        })
    finally:
        connection.close()


# ---------------- ADMIN: VERIFY OR REJECT PAYMENT ----------------

def verify_payment(event):
    auth_error = verify_admin_request(event)
    if auth_error:
        return auth_error

    body = parse_body(event)
    order_id = body.get("order_id")
    action = str(body.get("action", "")).strip().lower()

    try:
        order_id = int(order_id)
        if order_id <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return api_response(400, {
            "success": False,
            "message": "A valid order_id is required"
        })

    if action not in ("approve", "reject"):
        return api_response(400, {
            "success": False,
            "message": "Action must be approve or reject"
        })

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT payment_status
                FROM orders
                WHERE order_id = %s
                FOR UPDATE
            """, (order_id,))
            order = cursor.fetchone()

            if not order:
                connection.rollback()
                return api_response(404, {
                    "success": False,
                    "message": "Order not found"
                })

            current_status = str(order[0] or "").upper()
            if current_status != "PENDING_VERIFICATION":
                connection.rollback()
                return api_response(409, {
                    "success": False,
                    "message": f"Order is not awaiting verification. Current payment status: {current_status}"
                })

            if action == "approve":
                cursor.execute("""
                    UPDATE orders
                    SET payment_status = 'PAID',
                        order_status = 'CONFIRMED'
                    WHERE order_id = %s
                      AND payment_status = 'PENDING_VERIFICATION'
                """, (order_id,))
                new_payment_status = "PAID"
                new_order_status = "CONFIRMED"
                message = "Payment approved. Confirm receipt in your bank/UPI app before approving."
            else:
                cursor.execute("""
                    UPDATE orders
                    SET payment_status = 'REJECTED'
                    WHERE order_id = %s
                      AND payment_status = 'PENDING_VERIFICATION'
                """, (order_id,))
                new_payment_status = "REJECTED"
                new_order_status = None
                message = "Payment reference rejected. The customer may submit a corrected reference."

            if cursor.rowcount != 1:
                connection.rollback()
                return api_response(409, {
                    "success": False,
                    "message": "Payment status changed. Refresh the pending payment list."
                })

        connection.commit()
        result = {
            "success": True,
            "message": message,
            "order_id": order_id,
            "payment_status": new_payment_status
        }
        if new_order_status:
            result["order_status"] = new_order_status
        return api_response(200, result)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


# ---------------- MAIN LAMBDA HANDLER ----------------

def lambda_handler(event, context):
    method = get_request_method(event)
    path = get_request_path(event)

    if method == "OPTIONS":
        return api_response(200, {"success": True})

    try:
        if method == "GET" and path == "/products":
            return get_products()

        if method == "POST" and path == "/register":
            return register_customer(event)

        if method == "POST" and path == "/login":
            return login_customer(event)

        if method == "POST" and path == "/orders":
            return create_order(event)

        if method == "GET" and path == "/my-orders":
            return get_my_orders(event)

        if method == "POST" and path == "/submit-payment":
            return submit_payment(event)

        if method == "GET" and path == "/admin/pending-payments":
            return get_pending_payments(event)

        if method == "POST" and path == "/admin/verify-payment":
            return verify_payment(event)

        return api_response(404, {
            "success": False,
            "message": "Endpoint not found"
        })

    except json.JSONDecodeError:
        return api_response(400, {
            "success": False,
            "message": "Request body must contain valid JSON"
        })

    except ValueError as error:
        return api_response(400, {
            "success": False,
            "message": str(error)
        })

    except Exception as error:
        print("APPLICATION ERROR:", repr(error))
        traceback.print_exc()
        return api_response(500, {
            "success": False,
            "message": "Internal server error"
        })
