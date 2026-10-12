"""Flask REST API for the Inventory Management System."""
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

OFF_BASE = "https://world.openfoodfacts.org"
TIMEOUT = 10  # seconds for external API calls
# OpenFoodFacts asks every app to send a custom User-Agent: AppName/Version (ContactEmail)
# TODO: replace the email with your own
HEADERS = {"User-Agent": "InventoryLab/1.0 (ryan.nganga@student.moringaschool.com)"}

# Simulated database: a plain list of dicts (every item has an id)
inventory = [
    {"id": 1, "barcode": "3017620422003", "product_name": "Nutella",
     "brands": "Ferrero", "ingredients_text": "Sugar, palm oil, hazelnuts...",
     "price": 4.99, "stock": 25},
    {"id": 2, "barcode": "5449000000996", "product_name": "Coca-Cola",
     "brands": "Coca-Cola", "ingredients_text": "Carbonated water, sugar...",
     "price": 1.50, "stock": 100},
    {"id": 3, "barcode": None, "product_name": "Organic Almond Milk",
     "brands": "Silk", "ingredients_text": "Filtered water, almonds, cane sugar, ...",
     "price": 3.49, "stock": 40},
]
_next_id = 4


def find_item(item_id):
    """Return the inventory item with this id, or None."""
    return next((i for i in inventory if i["id"] == item_id), None)


def _clean_product(p):
    """Keep only the fields we care about from an OpenFoodFacts product."""
    return {
        "product_name": p.get("product_name", ""),
        "brands": p.get("brands", ""),
        "ingredients_text": p.get("ingredients_text", ""),
        "barcode": p.get("code"),
    }


def fetch_product_by_barcode(barcode):
    """Query OpenFoodFacts by barcode. Returns dict or None if not found."""
    r = requests.get(f"{OFF_BASE}/api/v2/product/{barcode}.json", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != 1:
        return None
    product = data["product"]
    product.setdefault("code", barcode)
    return _clean_product(product)


def fetch_product_by_name(name):
    """Search OpenFoodFacts by product name. Returns first match or None."""
    r = requests.get(
        f"{OFF_BASE}/cgi/search.pl",
        params={"search_terms": name, "search_simple": 1, "action": "process",
                "json": 1, "page_size": 1},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    products = r.json().get("products", [])
    return _clean_product(products[0]) if products else None


# ---------- CRUD routes ----------
@app.route("/inventory", methods=["GET"])
def get_inventory():
    return jsonify(inventory), 200


@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = find_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item), 200


@app.route("/inventory", methods=["POST"])
def add_item():
    global _next_id
    data = request.get_json(silent=True)
    if not data or not data.get("product_name"):
        return jsonify({"error": "product_name is required"}), 400
    try:
        price = float(data.get("price", 0))
        stock = int(data.get("stock", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "price must be a number and stock an integer"}), 400
    if price < 0 or stock < 0:
        return jsonify({"error": "price and stock cannot be negative"}), 400

    item = {
        "id": _next_id,
        "barcode": data.get("barcode"),
        "product_name": data["product_name"],
        "brands": data.get("brands", ""),
        "ingredients_text": data.get("ingredients_text", ""),
        "price": price,
        "stock": stock,
    }
    _next_id += 1
    inventory.append(item)
    return jsonify(item), 201


@app.route("/inventory/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    item = find_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400
    try:
        if "price" in data:
            price = float(data["price"])
            if price < 0:
                raise ValueError
            item["price"] = price
        if "stock" in data:
            stock = int(data["stock"])
            if stock < 0:
                raise ValueError
            item["stock"] = stock
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid price or stock value"}), 400
    for field in ("product_name", "brands", "ingredients_text", "barcode"):
        if field in data:
            item[field] = data[field]
    return jsonify(item), 200


@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = find_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    inventory.remove(item)
    return jsonify({"message": "Item deleted"}), 200


# ---------- External API routes ----------
@app.route("/external/search", methods=["GET"])
def external_search():
    barcode = request.args.get("barcode")
    name = request.args.get("name")
    if not barcode and not name:
        return jsonify({"error": "Provide ?barcode= or ?name="}), 400
    try:
        product = fetch_product_by_barcode(barcode) if barcode else fetch_product_by_name(name)
    except requests.RequestException as e:
        return jsonify({"error": f"External API failure: {e}"}), 502
    if not product:
        return jsonify({"error": "Product not found on OpenFoodFacts"}), 404
    return jsonify(product), 200


@app.route("/inventory/<int:item_id>/enrich", methods=["POST"])
def enrich_item(item_id):
    """Fill in an item's brand/ingredients using OpenFoodFacts data."""
    item = find_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    try:
        if item.get("barcode"):
            product = fetch_product_by_barcode(item["barcode"])
        else:
            product = fetch_product_by_name(item["product_name"])
    except requests.RequestException as e:
        return jsonify({"error": f"External API failure: {e}"}), 502
    if not product:
        return jsonify({"error": "No external data found"}), 404
    for field in ("brands", "ingredients_text"):
        if product.get(field):
            item[field] = product[field]
    if not item.get("barcode") and product.get("barcode"):
        item["barcode"] = product["barcode"]
    return jsonify(item), 200


if __name__ == "__main__":
    app.run(debug=True)  # Flask Debug Mode
