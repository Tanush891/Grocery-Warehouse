import logic2 as data

LINE = "-" * 44


# Calculations

def compute_tier(visit_number):
    if visit_number >= data.GOLD_AT_VISIT:
        return "Gold"
    if visit_number >= data.SILVER_AT_VISIT:
        return "Silver"
    return "Basic"


def ceil_percent(amount, percent):
    return (amount * percent + 99) // 100


def calculate_bill(cart, tier):
    subtotal = sum(line["line_total"] for line in cart)
    discount = ceil_percent(subtotal, data.TIER_DISCOUNTS[tier])
    return subtotal, discount, subtotal - discount


# Printing

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
        flag = "  [LOW STOCK]" if info["quantity"] <= data.LOW_STOCK_THRESHOLD else ""
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
    print(f"Loyalty discount:    Rs {discount}  ({data.TIER_DISCOUNTS[tier]}% - {tier})")
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


# Input

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


# Queue

def process_queue(kiosks, active_sessions, queue):
    if not queue:
        return
    kiosk_id = data.find_free_kiosk(kiosks)
    if kiosk_id is None:
        return
    next_customer = data.take_from_queue(queue)
    data.assign_kiosk(kiosks, active_sessions, kiosk_id, next_customer)
    print(f"Kiosk {kiosk_id} is now free -> assigned to queued customer "
          f"{next_customer['customer_id']} ({next_customer['tier']}).")


# Checkout

def start_checkout(kiosks, active_sessions, queue, customers):
    customer_id = read_nonempty("Customer ID: ")
    visit_number = data.get_visits(customers, customer_id) + 1
    tier = compute_tier(visit_number)
    session = {"customer_id": customer_id, "tier": tier, "visit_number": visit_number}

    kiosk_id = data.find_free_kiosk(kiosks)
    if kiosk_id is None:
        position = data.add_to_queue(queue, session)
        print(f"All kiosks are currently busy. {customer_id} added to queue. "
              f"Position: {position}")
        return

    data.assign_kiosk(kiosks, active_sessions, kiosk_id, session)
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

        data.deduct_stock(inventory, item_id, qty)
        line_total = qty * inventory[item_id]["price"]
        data.add_to_cart(cart, inventory[item_id]["name"], qty, line_total)
        print(f"Added: {inventory[item_id]['name']} x{qty}")

    data.save_inventory(data.INVENTORY_FILE, inventory)

    if not cart:
        print("No items purchased.")
    else:
        subtotal, discount, total = calculate_bill(cart, tier)
        print_receipt(customer_id, tier, visit_number, cart, subtotal, discount, total)
        data.record_visit(customers, customer_id, visit_number)
        data.save_customers(data.CUSTOMERS_FILE, customers)

    data.release_kiosk(kiosks, kiosk_id)
    print(f"Kiosk {kiosk_id} released.")
    process_queue(kiosks, active_sessions, queue)


# Van restock

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
        data.add_stock(inventory, item_id, qty)
        updates.append((item_id, inventory[item_id]["name"], old_qty, inventory[item_id]["quantity"]))
        print(f"Added: {inventory[item_id]['name']} +{qty}")

    data.save_inventory(data.INVENTORY_FILE, inventory)

    if not updates:
        print("No items delivered.")
    else:
        print_restock_summary(manifest_id, updates)
