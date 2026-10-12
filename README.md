Author: Ryan Nganga

# Inventory Management System (Flask + CLI)

A Flask REST API with CRUD operations for inventory, OpenFoodFacts integration,
and a command-line interface. Data is stored in an in-memory list (simulated DB).

## Setup
```bash
git clone <your-repo-url>
cd inventory-system
python -m venv venv
venv\Scripts\activate        # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## Run the API
```bash
python app.py
```
The API runs at http://127.0.0.1:5000 in Flask debug mode.

## API Endpoints
| Method | Route | Description |
|---|---|---|
| GET | /inventory | Fetch all items |
| GET | /inventory/<id> | Fetch one item |
| POST | /inventory | Add item (`product_name` required) |
| PATCH | /inventory/<id> | Update item (price, stock, ...) |
| DELETE | /inventory/<id> | Remove item |
| GET | /external/search?barcode=... or ?name=... | Query OpenFoodFacts |
| POST | /inventory/<id>/enrich | Add OpenFoodFacts details to an item |

## CLI Usage (run the API first, in another terminal)
```bash
python cli.py list
python cli.py view 1
python cli.py add --name "Oat Milk" --brand Oatly --price 3.2 --stock 30
python cli.py update 1 --price 5.49 --stock 20
python cli.py delete 2
python cli.py find --barcode 3017620422003
python cli.py find --name nutella
python cli.py enrich 3
```

## Tests
```bash
python -m pytest -v
```
Tests use `unittest.mock` to simulate OpenFoodFacts and API responses.
## Notes
OpenFoodFacts name search is sometimes unavailable and returns 503. The API handles this and returns a 502 error message. Barcode lookup is the more reliable option.

