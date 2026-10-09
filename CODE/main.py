import logic1
import logic2


def main():
    inventory = logic2.load_inventory(logic2.INVENTORY_FILE)
    customers = logic2.load_customers(logic2.CUSTOMERS_FILE)
    kiosks = logic2.new_kiosks()
    active_sessions = {}
    queue = []

    try:
        while True:
            logic1.print_menu(inventory, kiosks, active_sessions, queue)
            choice = input("Enter choice: ").strip()

            if choice == "1":
                logic1.start_checkout(kiosks, active_sessions, queue, customers)
            elif choice == "2":
                logic1.complete_checkout(inventory, kiosks, active_sessions, queue, customers)
            elif choice == "3":
                logic1.process_van_delivery(inventory)
            elif choice == "4":
                logic1.print_inventory(inventory)
            elif choice == "5":
                logic2.save_inventory(logic2.INVENTORY_FILE, inventory)
                logic2.save_customers(logic2.CUSTOMERS_FILE, customers)
                print("Goodbye!")
                break
            else:
                print("Invalid choice.")

            print()
    except EOFError:
        pass


if __name__ == "__main__":
    main()
