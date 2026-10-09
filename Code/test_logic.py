import csv
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import logic
import main


def run_with_input(func, inputs, *args, **kwargs):
    buf = io.StringIO()
    with patch("builtins.input", side_effect=inputs), redirect_stdout(buf):
        result = func(*args, **kwargs)
    return result, buf.getvalue()


def sample_inventory():
    return {
        "I001": {"name": "Milk 1L", "quantity": 40, "price": 60},
        "I002": {"name": "Bread", "quantity": 25, "price": 40},
        "I004": {"name": "Rice 5kg", "quantity": 8, "price": 350},
        "I005": {"name": "Cooking Oil 1L", "quantity": 3, "price": 180},
    }


def fresh_kiosks():
    return {kiosk_id: "Free" for kiosk_id in logic.KIOSK_IDS}


class GroceryTestCase(unittest.TestCase):
    """Redirects logic's CSV paths to a temp dir per test."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.inventory_path = os.path.join(self.tmpdir.name, "inventory.csv")
        self.customers_path = os.path.join(self.tmpdir.name, "customers.csv")
        self._orig_inv, self._orig_cust = logic.INVENTORY_FILE, logic.CUSTOMERS_FILE
        logic.INVENTORY_FILE = self.inventory_path
        logic.CUSTOMERS_FILE = self.customers_path

    def tearDown(self):
        logic.INVENTORY_FILE, logic.CUSTOMERS_FILE = self._orig_inv, self._orig_cust
        self.tmpdir.cleanup()


class TestStartupInventory(GroceryTestCase):

    def test_TC01_inventory_loads_correctly(self):
        with open(self.inventory_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["item_id", "name", "quantity", "price"])
            w.writerow(["I001", "Milk 1L", "40", "60"])

        inventory = logic.load_inventory(self.inventory_path)
        self.assertEqual(inventory["I001"], {"name": "Milk 1L", "quantity": 40, "price": 60})


class TestMenuDisplay(unittest.TestCase):

    def test_TC02_menu_lists_expected_options(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            logic.print_menu(sample_inventory(), fresh_kiosks(), {}, [])
        output = buf.getvalue()
        for option in ["1. Start Checkout", "2. Complete Checkout",
                       "3. Process Van Delivery", "4. View Inventory", "5. Exit"]:
            self.assertIn(option, output)


class TestCheckoutBilling(GroceryTestCase):

    def test_TC03_subtotal_and_stock_deduction(self):
        inventory, kiosks, active, queue, customers = sample_inventory(), fresh_kiosks(), {}, [], {}
        run_with_input(logic.start_checkout, ["C1"], kiosks, active, queue, customers)
        kiosk_id = next(iter(active))
        _, output = run_with_input(logic.complete_checkout, [kiosk_id, "I001", "2", "done"],
                                    inventory, kiosks, active, queue, customers)
        self.assertEqual(inventory["I001"]["quantity"], 38)
        self.assertIn("Subtotal:            Rs 120", output)

    def test_TC04_gold_tier_discount_on_tenth_visit(self):
        inventory, kiosks, active, queue = sample_inventory(), fresh_kiosks(), {}, []
        customers = {"C_GOLD": 9}
        run_with_input(logic.start_checkout, ["C_GOLD"], kiosks, active, queue, customers)
        kiosk_id = next(iter(active))
        self.assertEqual(active[kiosk_id]["tier"], "Gold")
        _, output = run_with_input(logic.complete_checkout, [kiosk_id, "I004", "1", "done"],
                                    inventory, kiosks, active, queue, customers)
        self.assertIn("Loyalty discount:    Rs 35", output)
        self.assertIn("TOTAL:               Rs 315", output)

    def test_TC05_basic_tier_no_discount_on_first_visit(self):
        inventory, kiosks, active, queue, customers = sample_inventory(), fresh_kiosks(), {}, [], {}
        run_with_input(logic.start_checkout, ["C_NEW"], kiosks, active, queue, customers)
        kiosk_id = next(iter(active))
        _, output = run_with_input(logic.complete_checkout, [kiosk_id, "I004", "1", "done"],
                                    inventory, kiosks, active, queue, customers)
        self.assertIn("Loyalty discount:    Rs 0", output)


class TestCartValidation(GroceryTestCase):

    def test_TC06_insufficient_stock_rejected_and_unchanged(self):
        inventory, kiosks, active, queue, customers = sample_inventory(), fresh_kiosks(), {}, [], {}
        run_with_input(logic.start_checkout, ["C1"], kiosks, active, queue, customers)
        kiosk_id = next(iter(active))
        _, output = run_with_input(logic.complete_checkout, [kiosk_id, "I005", "10", "done"],
                                    inventory, kiosks, active, queue, customers)
        self.assertIn("Insufficient stock", output)
        self.assertEqual(inventory["I005"]["quantity"], 3)

    def test_EC02_unknown_item_id_rejected_cart_continues(self):
        inventory, kiosks, active, queue, customers = sample_inventory(), fresh_kiosks(), {}, [], {}
        run_with_input(logic.start_checkout, ["C1"], kiosks, active, queue, customers)
        kiosk_id = next(iter(active))
        _, output = run_with_input(logic.complete_checkout, [kiosk_id, "ZZZ", "I001", "1", "done"],
                                    inventory, kiosks, active, queue, customers)
        self.assertIn("does not exist in inventory", output)
        self.assertEqual(inventory["I001"]["quantity"], 39)

    def test_EC04_zero_or_negative_quantity_rejected(self):
        inventory, kiosks, active, queue, customers = sample_inventory(), fresh_kiosks(), {}, [], {}
        run_with_input(logic.start_checkout, ["C1"], kiosks, active, queue, customers)
        kiosk_id = next(iter(active))
        _, output = run_with_input(logic.complete_checkout, [kiosk_id, "I001", "0", "2", "done"],
                                    inventory, kiosks, active, queue, customers)
        self.assertIn("Invalid quantity value.", output)
        self.assertEqual(inventory["I001"]["quantity"], 38)


class TestKioskAndQueue(GroceryTestCase):

    def test_TC07_EC06_customer_queued_when_all_kiosks_busy(self):
        kiosks = {k: "Busy" for k in logic.KIOSK_IDS}
        active, queue, customers = {}, [], {}
        _, output = run_with_input(logic.start_checkout, ["C_LATE"], kiosks, active, queue, customers)
        self.assertEqual(queue[0]["customer_id"], "C_LATE")
        self.assertIn("added to queue", output)

    def test_TC08_kiosk_released_after_checkout(self):
        inventory, kiosks, active, queue, customers = sample_inventory(), fresh_kiosks(), {}, [], {}
        run_with_input(logic.start_checkout, ["C1"], kiosks, active, queue, customers)
        kiosk_id = next(iter(active))
        run_with_input(logic.complete_checkout, [kiosk_id, "I001", "1", "done"],
                        inventory, kiosks, active, queue, customers)
        self.assertEqual(kiosks[kiosk_id], "Free")
        self.assertNotIn(kiosk_id, active)

    def test_EC07_queue_processed_first_come_first_served(self):
        kiosks = {k: "Busy" for k in logic.KIOSK_IDS}
        active = {"K1": {"customer_id": "C_CURRENT", "tier": "Basic", "visit_number": 1}}
        queue = [
            {"customer_id": "C_FIRST", "tier": "Basic", "visit_number": 1},
            {"customer_id": "C_SECOND", "tier": "Basic", "visit_number": 1},
        ]
        kiosks["K1"] = "Free"
        del active["K1"]
        logic.process_queue(kiosks, active, queue)
        self.assertEqual(active["K1"]["customer_id"], "C_FIRST")
        self.assertEqual([c["customer_id"] for c in queue], ["C_SECOND"])


class TestVanRestock(GroceryTestCase):

    def test_TC09_restock_adds_to_existing_stock(self):
        inventory = sample_inventory()
        run_with_input(logic.process_van_delivery, ["VAN-001", "I005", "50", "done"], inventory)
        self.assertEqual(inventory["I005"]["quantity"], 53)
        self.assertEqual(logic.load_inventory(logic.INVENTORY_FILE)["I005"]["quantity"], 53)

    def test_TC10_EC08_restock_rejects_unknown_item(self):
        inventory = sample_inventory()
        _, output = run_with_input(logic.process_van_delivery, ["VAN-002", "ZZZ", "done"], inventory)
        self.assertIn("does not exist in inventory", output)
        self.assertIn("No items delivered.", output)

    def test_EC09_restock_rejects_zero_or_negative_quantity(self):
        inventory = sample_inventory()
        _, output = run_with_input(logic.process_van_delivery, ["VAN-003", "I001", "-5", "10", "done"], inventory)
        self.assertIn("Invalid quantity value.", output)
        self.assertEqual(inventory["I001"]["quantity"], 50)


class TestLowStockFlag(unittest.TestCase):

    def test_TC11_EC12_low_stock_flag_is_inclusive(self):
        inventory = {
            "I005": {"name": "Cooking Oil 1L", "quantity": logic.LOW_STOCK_THRESHOLD, "price": 180},
            "I004": {"name": "Rice 5kg", "quantity": logic.LOW_STOCK_THRESHOLD + 1, "price": 350},
        }
        buf = io.StringIO()
        with redirect_stdout(buf):
            logic.print_inventory(inventory)
        lines = buf.getvalue().splitlines()
        oil_line = [l for l in lines if "Cooking Oil" in l][0]
        rice_line = [l for l in lines if "Rice 5kg" in l][0]
        self.assertIn("[LOW STOCK]", oil_line)
        self.assertNotIn("[LOW STOCK]", rice_line)


class TestPersistence(GroceryTestCase):

    def test_TC12_inventory_persists_across_reload(self):
        inventory = sample_inventory()
        logic.save_inventory(self.inventory_path, inventory)
        run_with_input(logic.process_van_delivery, ["VAN-001", "I004", "20", "done"], inventory)
        reloaded = logic.load_inventory(self.inventory_path)
        self.assertEqual(reloaded["I004"]["quantity"], 28)


class TestMainLoop(GroceryTestCase):

    def test_TC13_exit_saves_inventory_and_prints_goodbye(self):
        logic.save_inventory(self.inventory_path, sample_inventory())
        buf = io.StringIO()
        with patch("builtins.input", side_effect=["5"]), redirect_stdout(buf):
            main.main()
        self.assertIn("Goodbye!", buf.getvalue())
        self.assertTrue(os.path.exists(self.inventory_path))

    def test_EC01_invalid_menu_choice_shows_message_and_reprompts(self):
        logic.save_inventory(self.inventory_path, sample_inventory())
        buf = io.StringIO()
        with patch("builtins.input", side_effect=["9", "5"]), redirect_stdout(buf):
            main.main()
        self.assertIn("Invalid choice.", buf.getvalue())
        self.assertIn("Goodbye!", buf.getvalue())


class TestMissingInventoryFile(unittest.TestCase):

    def test_EC10_missing_file_exits_cleanly_not_a_crash(self):
        with self.assertRaises(SystemExit):
            logic.load_inventory("this_file_does_not_exist.csv")


class TestEmptyCart(GroceryTestCase):

    def test_EC13_empty_cart_no_charge_kiosk_still_released(self):
        inventory, kiosks, active, queue, customers = sample_inventory(), fresh_kiosks(), {}, [], {}
        run_with_input(logic.start_checkout, ["C1"], kiosks, active, queue, customers)
        kiosk_id = next(iter(active))
        _, output = run_with_input(logic.complete_checkout, [kiosk_id, "done"],
                                    inventory, kiosks, active, queue, customers)
        self.assertIn("No items purchased.", output)
        self.assertNotIn("RECEIPT", output)
        self.assertEqual(kiosks[kiosk_id], "Free")
        self.assertNotIn("C1", customers)


if __name__ == "__main__":
    unittest.main(verbosity=2)
