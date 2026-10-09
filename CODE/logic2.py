import csv

INVENTORY_FILE = "inventory.csv"
CUSTOMERS_FILE = "customers.csv"
KIOSK_IDS = ["K1", "K2", "K3", "K4"]
LOW_STOCK_THRESHOLD = 5
TIER_DISCOUNTS = {"Basic": 0, "Silver": 5, "Gold": 10}
SILVER_AT_VISIT = 2
GOLD_AT_VISIT = 10


# Inventory: {item_id: {"name", "quantity", "price"}}  (saved in inventory.csv)

def load_inventory(path):
    inventory = {}
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                inventory[row["item_id"]] = {
                    "name": row["name"],
                    "quantity": int(row["quantity"]),
                    "price": int(row["price"]),
                }
    except (FileNotFoundError, OSError):
        print(f"Error: could not read inventory file '{path}'.")
        raise SystemExit(1)
    except (KeyError, ValueError):
        print(f"Error: inventory file '{path}' is malformed.")
        raise SystemExit(1)
    return inventory


def save_inventory(path, inventory):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "name", "quantity", "price"])
        for item_id in sorted(inventory):
            info = inventory[item_id]
            writer.writerow([item_id, info["name"], info["quantity"], info["price"]])


def deduct_stock(inventory, item_id, qty):
    inventory[item_id]["quantity"] -= qty


def add_stock(inventory, item_id, qty):
    inventory[item_id]["quantity"] += qty


# Customers: {customer_id: number of completed purchases}  (saved in customers.csv)

def load_customers(path):
    customers = {}
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                customers[row["customer_id"]] = int(row["visits"])
    except FileNotFoundError:
        pass
    return customers


def save_customers(path, customers):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_id", "visits"])
        for customer_id in sorted(customers):
            writer.writerow([customer_id, customers[customer_id]])


def get_visits(customers, customer_id):
    return customers.get(customer_id, 0)


def record_visit(customers, customer_id, visit_number):
    customers[customer_id] = visit_number


# Kiosks: {kiosk_id: "Free" or "Busy"}
# Active sessions: {kiosk_id: {"customer_id", "tier", "visit_number"}}

def new_kiosks():
    return {kiosk_id: "Free" for kiosk_id in KIOSK_IDS}


def find_free_kiosk(kiosks):
    for kiosk_id in sorted(kiosks):
        if kiosks[kiosk_id] == "Free":
            return kiosk_id
    return None


def assign_kiosk(kiosks, active_sessions, kiosk_id, session):
    kiosks[kiosk_id] = "Busy"
    active_sessions[kiosk_id] = session


def release_kiosk(kiosks, kiosk_id):
    kiosks[kiosk_id] = "Free"


# Queue: list of session dictionaries, first in first out

def add_to_queue(queue, session):
    queue.append(session)
    return len(queue)


def take_from_queue(queue):
    return queue.pop(0)


# Cart: list of {"name", "quantity", "line_total"}, lasts for one checkout only

def add_to_cart(cart, name, quantity, line_total):
    cart.append({"name": name, "quantity": quantity, "line_total": line_total})
