import logic


def main():
    inventory = logic.load_inventory(logic.INVENTORY_FILE)
    customers = logic.load_customers(logic.CUSTOMERS_FILE)
    kiosks = {kiosk_id: "Free" for kiosk_id in logic.KIOSK_IDS}
    active_sessions = {}
    queue = []

    try:
        while True:
            logic.print_menu(inventory, kiosks, active_sessions, queue)
            choice = input("Enter choice: ").strip()

            if choice == "1":
                logic.start_checkout(kiosks, active_sessions, queue, customers)
            elif choice == "2":
                logic.complete_checkout(inventory, kiosks, active_sessions, queue, customers)
            elif choice == "3":
                logic.process_van_delivery(inventory)
            elif choice == "4":
                logic.print_inventory(inventory)
            elif choice == "5":
                logic.save_inventory(logic.INVENTORY_FILE, inventory)
                logic.save_customers(logic.CUSTOMERS_FILE, customers)
                print("Goodbye!")
                break
            else:
                print("Invalid choice.")

            print()
    except EOFError:
        pass


if __name__ == "__main__":
    main()
