import argparse
import json
import os
import re
import sys
from decimal import Decimal

DEFAULT_FILE = "products.json"

PRICE_INPUT_PATTERN = re.compile(r"[0-9]+(\.[0-9]{1,2})?")
PRICE_STORED_PATTERN = re.compile(r"[0-9]+\.[0-9]{2}")
QUANTITY_PATTERN = re.compile(r"[0-9]+")
ID_PATTERN = re.compile(r"[1-9][0-9]*")


class UserError(Exception):
    pass


class DataError(Exception):
    pass


def name_type(value):
    name = value.strip()
    if not name:
        raise argparse.ArgumentTypeError("name must not be empty or whitespace")
    return name


def price_type(value):
    if not PRICE_INPUT_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "price must be a nonnegative number with at most two decimal places, e.g. 12.99"
        )
    return format(Decimal(value), ".2f")


def quantity_type(value):
    if not QUANTITY_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("quantity must be a nonnegative whole number")
    return int(value)


def id_type(value):
    if not ID_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("ID must be a positive integer")
    return int(value)


def threshold_type(value):
    if not QUANTITY_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("threshold must be a nonnegative whole number")
    return int(value)


def load_data(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return {"next_id": 1, "products": []}
    except UnicodeDecodeError as exc:
        raise DataError(f"cannot read {path}: not valid UTF-8") from exc
    except OSError as exc:
        raise DataError(f"cannot read {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataError(f"{path} is not valid JSON: {exc}") from exc
    validate_data(data, path)
    return data


def validate_data(data, path):
    if not isinstance(data, dict):
        raise DataError(f"{path}: top level must be a JSON object")
    if set(data) != {"next_id", "products"}:
        raise DataError(f"{path}: expected exactly the keys 'next_id' and 'products'")
    next_id = data["next_id"]
    if isinstance(next_id, bool) or not isinstance(next_id, int) or next_id < 1:
        raise DataError(f"{path}: 'next_id' must be a positive integer")
    products = data["products"]
    if not isinstance(products, list):
        raise DataError(f"{path}: 'products' must be a JSON array")
    seen_ids = set()
    for index, product in enumerate(products):
        if not isinstance(product, dict):
            raise DataError(f"{path}: product {index} must be a JSON object")
        if set(product) != {"id", "name", "price", "quantity"}:
            raise DataError(
                f"{path}: product {index} must have exactly the keys "
                "'id', 'name', 'price', 'quantity'"
            )
        product_id = product["id"]
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id < 1:
            raise DataError(f"{path}: product {index} has an invalid 'id'")
        if product_id in seen_ids:
            raise DataError(f"{path}: duplicate product id {product_id}")
        if product_id >= next_id:
            raise DataError(f"{path}: product id {product_id} is not smaller than 'next_id'")
        seen_ids.add(product_id)
        name = product["name"]
        if not isinstance(name, str) or not name.strip():
            raise DataError(f"{path}: product {index} has an invalid 'name'")
        price = product["price"]
        if not isinstance(price, str) or not PRICE_STORED_PATTERN.fullmatch(price):
            raise DataError(f"{path}: product {index} has an invalid 'price'")
        quantity = product["quantity"]
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise DataError(f"{path}: product {index} has an invalid 'quantity'")


def save_data(path, data):
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_path, path)
    except OSError as exc:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise DataError(f"cannot write {path}: {exc}") from exc


def find_product(data, product_id):
    for product in data["products"]:
        if product["id"] == product_id:
            return product
    return None


def cmd_add(args):
    data = load_data(args.file)
    product = {
        "id": data["next_id"],
        "name": args.name,
        "price": args.price,
        "quantity": args.quantity,
    }
    data["next_id"] += 1
    data["products"].append(product)
    save_data(args.file, data)
    print(json.dumps(product, ensure_ascii=False))


def cmd_list(args):
    data = load_data(args.file)
    products = sorted(data["products"], key=lambda product: product["id"])
    print(json.dumps(products, ensure_ascii=False, indent=2))


def cmd_low_stock(args):
    data = load_data(args.file)
    products = sorted(
        (product for product in data["products"] if product["quantity"] <= args.threshold),
        key=lambda product: product["id"],
    )
    print(json.dumps(products, ensure_ascii=False, indent=2))


def cmd_get(args):
    data = load_data(args.file)
    product = find_product(data, args.id)
    if product is None:
        raise DataError(f"product with ID {args.id} not found")
    print(json.dumps(product, ensure_ascii=False))


def cmd_update(args):
    if args.name is None and args.price is None and args.quantity is None:
        raise UserError("update requires at least one of --name, --price, --quantity")
    data = load_data(args.file)
    product = find_product(data, args.id)
    if product is None:
        raise DataError(f"product with ID {args.id} not found")
    if args.name is not None:
        product["name"] = args.name
    if args.price is not None:
        product["price"] = args.price
    if args.quantity is not None:
        product["quantity"] = args.quantity
    save_data(args.file, data)
    print(json.dumps(product, ensure_ascii=False))


def cmd_delete(args):
    if not args.yes:
        raise UserError("delete requires the --yes flag")
    data = load_data(args.file)
    product = find_product(data, args.id)
    if product is None:
        raise DataError(f"product with ID {args.id} not found")
    data["products"] = [
        product for product in data["products"] if product["id"] != args.id
    ]
    save_data(args.file, data)
    print(json.dumps({"deleted_id": args.id}))


def main():
    parser = argparse.ArgumentParser(
        prog="products.py",
        description="Command-line product inventory tool.",
    )
    parser.add_argument(
        "--file",
        default=DEFAULT_FILE,
        help="path to the JSON data file (default: %(default)s)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new product")
    add_parser.add_argument("--name", required=True, type=name_type, help="product name")
    add_parser.add_argument("--price", required=True, type=price_type, help="price, e.g. 12.99")
    add_parser.add_argument("--quantity", required=True, type=quantity_type, help="stock quantity")
    add_parser.set_defaults(func=cmd_add)

    list_parser = subparsers.add_parser("list", help="List all products")
    list_parser.set_defaults(func=cmd_list)

    low_stock_parser = subparsers.add_parser(
        "low-stock", help="List products with quantity at or below a threshold"
    )
    low_stock_parser.add_argument(
        "--threshold",
        required=True,
        type=threshold_type,
        help="maximum stock quantity to report (nonnegative integer)",
    )
    low_stock_parser.set_defaults(func=cmd_low_stock)

    get_parser = subparsers.add_parser("get", help="Show a product by ID")
    get_parser.add_argument("id", type=id_type, help="product ID (positive integer)")
    get_parser.set_defaults(func=cmd_get)

    update_parser = subparsers.add_parser("update", help="Update an existing product")
    update_parser.add_argument("id", type=id_type, help="product ID (positive integer)")
    update_parser.add_argument("--name", type=name_type, help="new product name")
    update_parser.add_argument("--price", type=price_type, help="new price, e.g. 12.99")
    update_parser.add_argument("--quantity", type=quantity_type, help="new stock quantity")
    update_parser.set_defaults(func=cmd_update)

    delete_parser = subparsers.add_parser("delete", help="Delete a product by ID")
    delete_parser.add_argument("id", type=id_type, help="product ID (positive integer)")
    delete_parser.add_argument("--yes", action="store_true", help="confirm the deletion")
    delete_parser.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    try:
        args.func(args)
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    except DataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
