# Product Inventory CLI

A Python 3 command-line tool for managing a small store's product inventory.
Products are stored in a local JSON file, and each invocation performs exactly
one operation (create, read, update, delete, or a custom low-stock report) and
exits — no interactive menus.

## Requirements

- Python 3 (standard library only; no third-party packages)
- Any terminal (Windows, macOS, or Linux)

## Running the tool

From this folder, use the following invocation pattern:

```
python products.py [--file PATH] COMMAND [OPTIONS]
```

- On Windows, `py -3 products.py ...` can be used instead of `python3 products.py ...`.
- The optional `--file PATH` flag selects a different JSON data file and must
  appear **before** the command. The default is `products.json` in the current
  working directory; relative paths are resolved from that directory.
- Paths and names containing spaces should be quoted.

## Product fields

| Field      | Type                          | Rules                                                                 |
|------------|-------------------------------|-----------------------------------------------------------------------|
| `id`       | positive integer              | Assigned automatically, starting at 1; never reused after deletion    |
| `name`     | string                        | Trimmed; at least one non-whitespace character; duplicates allowed    |
| `price`    | string, two decimal places    | Nonnegative; e.g. `"4.50"`; rejects signs, symbols, exponents         |
| `quantity` | nonnegative integer           | Zero allowed; negative or fractional values rejected                  |

## Commands

### add — create a product

All three flags are required. The tool assigns the next ID, saves the record,
and prints the new product as a JSON object.

```
python products.py add --name "Notebook" --price 4.5 --quantity 10
{"id": 1, "name": "Notebook", "price": "4.50", "quantity": 10}
```

### list — show all products

Prints a JSON array sorted by numeric ID, or `[]` when the store is empty.

```
python products.py list
[
  {
    "id": 1,
    "name": "Notebook",
    "price": "4.50",
    "quantity": 10
  }
]
```

### get — show one product by ID

```
python products.py get 1
{"id": 1, "name": "Notebook", "price": "4.50", "quantity": 10}
```

### update — change one product

Requires at least one field flag. Only the supplied fields change; the ID and
all other fields are preserved.

```
python products.py update 1 --quantity 12
{"id": 1, "name": "Notebook", "price": "4.50", "quantity": 12}

python products.py update 1 --name "Dot Notebook" --price 5
{"id": 1, "name": "Dot Notebook", "price": "5.00", "quantity": 12}
```

### delete — remove one product

Requires `--yes` to confirm; there is no interactive prompt. Prints the
deleted ID as a JSON object.

```
python products.py delete 2 --yes
{"deleted_id": 2}
```

## Storage format and ID assignment

Data is saved as UTF-8 JSON with a `next_id` counter and a `products` array:

```json
{
  "next_id": 2,
  "products": [
    {"id": 1, "name": "Notebook", "price": "4.50", "quantity": 10}
  ]
}
```

- A missing data file is treated as an empty store (`next_id` starts at 1);
  the first successful `add` creates the file.
- Each successful `add` uses `next_id` and then increments it. Updates and
  deletions never change `next_id`, so deleted IDs are never reused.
- Writes are atomic: data is written to a temporary file and then moved into
  place, so a failed write never corrupts or replaces existing data.
- Read-only commands (`list`, `get`, `low-stock`, and `--help`) never create
  or modify the data file.

## Validation and error handling

- `name`: leading/trailing whitespace is trimmed; empty or whitespace-only
  names are rejected. Duplicate names are allowed.
- `price`: digits with an optional decimal point followed by one or two digits
  (`0`, `4.5`, and `4.50` are accepted). Signs, currency symbols, exponent
  notation, and more than two decimal places are rejected. Prices are stored
  and printed as strings with exactly two decimal places.
- `quantity`: nonnegative integers only (zero is valid).
- IDs for `get`, `update`, and `delete` must be positive integers.

Exit codes:

| Code | Meaning                                                                  |
|------|--------------------------------------------------------------------------|
| 0    | Success, including an empty result or a `--help` request                 |
| 1    | Product ID not found, invalid stored data, or a file read/write failure  |
| 2    | Invalid syntax, missing arguments, or invalid input values               |

Failures print a concise explanation to standard error (including the
requested ID when a product is missing) and never print JSON to standard
output. Expected errors never show a Python traceback, and a failed command
never alters the data file or consumes an ID.

## Custom feature: low-stock report

**Who it helps:** small store owners who need a quick restocking checklist.

**Why it is useful:** instead of scanning a full inventory list, the owner can
see at a glance which products have fallen to or below a chosen stock level
(including out-of-stock items with quantity 0) so they know what to reorder.

**Command syntax:**

```
python products.py low-stock --threshold N
```

`--threshold` is required and must be a nonnegative integer (zero is allowed).
The command reads the store, selects every product whose `quantity` is less
than or equal to the threshold, and prints them as a JSON array sorted by
numeric ID. If nothing matches, it prints `[]` and exits successfully. The
command is read-only and supports the global `--file PATH` option.

**Example** (continuing from an empty store):

```
python products.py add --name "Notebook" --price 4.5 --quantity 12
python products.py add --name "Pencil" --price 1.25 --quantity 5
python products.py low-stock --threshold 5
[
  {
    "id": 2,
    "name": "Pencil",
    "price": "1.25",
    "quantity": 5
  }
]
```

**Edge case** — nothing matches: with all quantities above the threshold, the
command prints an empty array and exits 0:

```
python products.py low-stock --threshold 0
[]
```

## Acknowledgment

This project was developed with assistance from the Viber Coding Agent, which
helped implement features, run tests, and review the code against the
assignment requirements. I reviewed every change, directed the incremental
design, verified the behavior myself, and can explain the code and file
handling in my own words.
