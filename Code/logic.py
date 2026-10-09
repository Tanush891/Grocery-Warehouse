import csv

LINE = "-" * 44
INVENTORY_FILE = "inventory.csv"
CUSTOMERS_FILE = "customers.csv"
KIOSK_IDS = ["K1", "K2", "K3", "K4"]
LOW_STOCK_THRESHOLD = 5
TIER_DISCOUNTS = {"Basic": 0, "Silver": 5, "Gold": 10}
SILVER_AT_VISIT = 2
GOLD_AT_VISIT = 10


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


def compute_tier(visit_number):
    if visit_number >= GOLD_AT_VISIT:
        return "Gold"
    if visit_number >= SILVER_AT_VISIT:
        return "Silver"
    return "Basic"


def print_kiosks(kiosks, active_sessions):
    print("Kiosk Status:")
    for kiosk_id in sorted(kiosks):
        if kiosks[kiosk_id] == "Busy" and kiosk_id in active_sessions:
            s = active_sessions[kiosk_id]
            print(f"  {kiosk_id}   Busy  ({s['customer_id']}, {s['tier']})")
        else:
            print(f"  {kiosk_id}   {kiosks[kiosk_id]}")
    print()


def print_queue(queue):
    if not queue:
        print("Queue: (empty)")
    else:
        print("Queue: " + ", ".join(f"{c['customer_id']} ({c['tier']})" for c in queue))
    print()


def print_inventory(inventory):
    print("Inventory Snapshot:")
    print(f"  {'ITEM_ID':<8}{'NAME':<18}{'QTY':>5}  {'PRICE':>8}")
    for item_id in sorted(inventory):
        info = inventory[item_id]
        flag = "  [LOW STOCK]" if info["quantity"] <= LOW_STOCK_THRESHOLD else ""
        print(f"  {item_id:<8}{info['name']:<18}{info['quantity']:>5}  Rs {info['price']:<5}{flag}")
    print()


def print_menu(inventory, kiosks, active_sessions, queue):
    print(LINE)
    print("  CO-OP GROCERY - SELF CHECKOUT SYSTEM")
    print(LINE)
    print()
    print_kiosks(kiosks, active_sessions)
    print_queue(queue)
    print_inventory(inventory)
    print("1. Start Checkout")
    print("2. Complete Checkout")
    print("3. Process Van Delivery")
    print("4. View Inventory")
    print("5. Exit")
    print()


def print_receipt(customer_id, tier, visit_number, cart, subtotal, discount, total):
    print()
    print(LINE)
    print("               RECEIPT")
    print(LINE)
    print(f"Customer: {customer_id}  (visit #{visit_number}, {tier} tier)")
    print()
    for line in cart:
        print(f"  {line['name']:<18} x{line['quantity']:<3} Rs {line['line_total']}")
    print(LINE)
    print(f"Subtotal:            Rs {subtotal}")
    print(f"Loyalty discount:    Rs {discount}  ({TIER_DISCOUNTS[tier]}% - {tier})")
    print(LINE)
    print(f"TOTAL:               Rs {total}")
    print(LINE)


def print_restock_summary(manifest_id, updates):
    print()
    print(LINE)
    print("           RESTOCK SUMMARY")
    print(LINE)
    print(f"Manifest ID: {manifest_id}")
    print()
    for item_id, name, old_qty, new_qty in updates:
        print(f"  {name:<18} {old_qty} -> {new_qty}")
    print(LINE)


def read_nonempty(prompt, error_msg="Invalid ID."):
    while True:
        raw = input(prompt).strip()
        if raw == "":
            print(error_msg)
            continue
        return raw


def read_quantity(prompt, error_msg="Invalid quantity value."):
    while True:
        raw = input(prompt).strip()
        try:
            qty = int(raw)
        except ValueError:
            print(error_msg)
            continue
        if qty <= 0:
            print(error_msg)
            continue
        return qty


def ceil_percent(amount, percent):
    return (amount * percent + 99) // 100


def find_free_kiosk(kiosks):
    for kiosk_id in sorted(kiosks):
        if kiosks[kiosk_id] == "Free":
            return kiosk_id
    return None


def process_queue(kiosks, active_sessions, queue):
    if not queue:
        return
    kiosk_id = find_free_kiosk(kiosks)
    if kiosk_id is None:
        return
    next_customer = queue.pop(0)
    kiosks[kiosk_id] = "Busy"
    active_sessions[kiosk_id] = next_customer
    print(f"Kiosk {kiosk_id} is now free -> assigned to queued customer "
          f"{next_customer['customer_id']} ({next_customer['tier']}).")


def start_checkout(kiosks, active_sessions, queue, customers):
    customer_id = read_nonempty("Customer ID: ")
    visit_number = customers.get(customer_id, 0) + 1
    tier = compute_tier(visit_number)
    session = {"customer_id": customer_id, "tier": tier, "visit_number": visit_number}

    kiosk_id = find_free_kiosk(kiosks)
    if kiosk_id is None:
        queue.append(session)
        print(f"All kiosks are currently busy. {customer_id} added to queue. "
              f"Position: {len(queue)}")
        return

    kiosks[kiosk_id] = "Busy"
    active_sessions[kiosk_id] = session
    print(f"Kiosk {kiosk_id} assigned to {customer_id} (visit #{visit_number}, {tier} tier).")


def complete_checkout(inventory, kiosks, active_sessions, queue, customers):
    if not active_sessions:
        print("No active checkout sessions to complete.")
        return

    print("Active sessions:")
    for kiosk_id in sorted(active_sessions):
        s = active_sessions[kiosk_id]
        print(f"  {kiosk_id}: {s['customer_id']} ({s['tier']})")

    kiosk_id = input("Enter Kiosk ID to complete checkout: ").strip().upper()
    if kiosk_id not in active_sessions:
        print("No active session at that kiosk.")
        return

    session = active_sessions.pop(kiosk_id)
    customer_id, tier, visit_number = session["customer_id"], session["tier"], session["visit_number"]

    print(f"Completing checkout for {customer_id} at Kiosk {kiosk_id}.")
    cart = []

    while True:
        item_id = input("Item ID (or 'done'): ").strip()
        if item_id.lower() == "done":
            break
        if item_id == "":
            print("Invalid ID.")
            continue
        if item_id not in inventory:
            print("That item ID does not exist in inventory.")
            continue

        qty = read_quantity("Quantity: ")
        available = inventory[item_id]["quantity"]
        if qty > available:
            print(f"Insufficient stock: only {available} unit(s) of {inventory[item_id]['name']} available.")
            continue

        inventory[item_id]["quantity"] -= qty
        line_total = qty * inventory[item_id]["price"]
        cart.append({"name": inventory[item_id]["name"], "quantity": qty, "line_total": line_total})
        print(f"Added: {inventory[item_id]['name']} x{qty}")

    save_inventory(INVENTORY_FILE, inventory)

    if not cart:
        print("No items purchased.")
    else:
        subtotal = sum(line["line_total"] for line in cart)
        discount = ceil_percent(subtotal, TIER_DISCOUNTS[tier])
        total = subtotal - discount
        print_receipt(customer_id, tier, visit_number, cart, subtotal, discount, total)
        customers[customer_id] = visit_number
        save_customers(CUSTOMERS_FILE, customers)

    kiosks[kiosk_id] = "Free"
    print(f"Kiosk {kiosk_id} released.")
    process_queue(kiosks, active_sessions, queue)


def process_van_delivery(inventory):
    manifest_id = read_nonempty("Van Manifest ID: ")
    print(f"Processing manifest {manifest_id}...")
    updates = []

    while True:
        item_id = input("Item ID (or 'done'): ").strip()
        if item_id.lower() == "done":
            break
        if item_id == "":
            print("Invalid ID.")
            continue
        if item_id not in inventory:
            print("That item ID does not exist in inventory.")
            continue

        qty = read_quantity("Quantity delivered: ")
        old_qty = inventory[item_id]["quantity"]
        inventory[item_id]["quantity"] += qty
        updates.append((item_id, inventory[item_id]["name"], old_qty, inventory[item_id]["quantity"]))
        print(f"Added: {inventory[item_id]['name']} +{qty}")

    save_inventory(INVENTORY_FILE, inventory)

    if not updates:
        print("No items delivered.")
    else:
        print_restock_summary(manifest_id, updates)
