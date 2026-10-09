# Grocery-Warehouse
# Grocery Self-Checkout & Restocking System

A terminal app that simulates a grocery store's self-checkout kiosks and van restocking. Stock is saved in a CSV file, so it is remembered between runs.

## Features

- 4 checkout kiosks, with a first-come-first-served queue when all are busy
- Stock saved in `inventory.csv`
- Loyalty discount worked out automatically from visit count
- Van deliveries add stock back
- Items at 5 units or fewer are flagged `[LOW STOCK]`

## Loyalty tiers

| Visit | Tier | Discount |
|---|---|---|
| 1 | Basic | 0% |
| 2 to 9 | Silver | 5% |
| 10+ | Gold | 10% |

## Run it

Needs Python 3.6 or newer. Keep `main.py`, `logic.py` and `inventory.csv` in the same folder.

```bash
python main.py
```

## Menu

```
1. Start Checkout      (claim a kiosk, or join the queue)
2. Complete Checkout   (enter the cart, get the bill)
3. Process Van Delivery
4. View Inventory
5. Exit
```

To see the queue, use option 1 for five different customers. The fifth will wait in line.

## Files

| File | Purpose |
|---|---|
| `main.py` | Starts the program and runs the menu |
| `logic.py` | All the checkout, restock and file logic |
| `test_logic.py` | Unit tests |
| `inventory.csv` | Stock data |
| `customers.csv` | Visit history (created automatically) |

## Run the tests

```bash
python -m unittest test_logic.py -v
```
