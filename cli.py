"""Command-line interface for the Inventory API."""
import argparse
import json
import os
import sys

import requests

API_URL = os.environ.get("INVENTORY_API_URL", "http://127.0.0.1:5000")


def call_api(method, path, **kwargs):
    """Send a request to the API. Returns parsed JSON or None on failure."""
    try:
        r = requests.request(method, f"{API_URL}{path}", timeout=10, **kwargs)
    except requests.ConnectionError:
        print("Error: cannot reach the API. Is the Flask server running?")
        return None
    except requests.Timeout:
        print("Error: the API request timed out.")
        return None
    try:
        body = r.json()
    except ValueError:
        print(f"Error: invalid response from API (status {r.status_code}).")
        return None
    if r.status_code >= 400:
        print(f"Error {r.status_code}: {body.get('error', 'Unknown error')}")
        return None
    return body


def show(data):
    print(json.dumps(data, indent=2))


def build_parser():
    p = argparse.ArgumentParser(description="Inventory management CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="View all items")

    v = sub.add_parser("view", help="View one item")
    v.add_argument("id", type=int)

    a = sub.add_parser("add", help="Add a new item")
    a.add_argument("--name", required=True)
    a.add_argument("--brand", default="")
    a.add_argument("--barcode")
    a.add_argument("--price", type=float, default=0)
    a.add_argument("--stock", type=int, default=0)

    u = sub.add_parser("update", help="Update price or stock")
    u.add_argument("id", type=int)
    u.add_argument("--price", type=float)
    u.add_argument("--stock", type=int)

    d = sub.add_parser("delete", help="Delete an item")
    d.add_argument("id", type=int)

    f = sub.add_parser("find", help="Find a product on OpenFoodFacts")
    f.add_argument("--barcode")
    f.add_argument("--name")

    e = sub.add_parser("enrich", help="Add OpenFoodFacts details to an item")
    e.add_argument("id", type=int)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    result = None

    if args.command == "list":
        result = call_api("GET", "/inventory")
    elif args.command == "view":
        result = call_api("GET", f"/inventory/{args.id}")
    elif args.command == "add":
        payload = {"product_name": args.name, "brands": args.brand,
                   "barcode": args.barcode, "price": args.price, "stock": args.stock}
        result = call_api("POST", "/inventory", json=payload)
    elif args.command == "update":
        payload = {k: v for k, v in (("price", args.price), ("stock", args.stock)) if v is not None}
        if not payload:
            print("Error: provide --price and/or --stock.")
            return 1
        result = call_api("PATCH", f"/inventory/{args.id}", json=payload)
    elif args.command == "delete":
        result = call_api("DELETE", f"/inventory/{args.id}")
    elif args.command == "find":
        if not args.barcode and not args.name:
            print("Error: provide --barcode or --name.")
            return 1
        params = {"barcode": args.barcode} if args.barcode else {"name": args.name}
        result = call_api("GET", "/external/search", params=params)
    elif args.command == "enrich":
        result = call_api("POST", f"/inventory/{args.id}/enrich")

    if result is None:
        return 1
    show(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())