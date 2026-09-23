# Copyright 2026 Google LLC
# Seed script for Firestore collection table_profiles

import datetime
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-bffdb63e0ac7"
COLLECTION_NAME = "table_profiles"


def seed_firestore():
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection(COLLECTION_NAME)

    profiles = [
        {
            "table_name": "users",
            "row_count": 50000,
            "columns": [
                {"name": "user_id", "type": "UUID", "is_pk": True},
                {"name": "email", "type": "VARCHAR", "is_pk": False},
                {"name": "status", "type": "VARCHAR", "is_pk": False},
                {"name": "created_at", "type": "TIMESTAMP", "is_pk": False},
            ],
            "foreign_keys": [],
            "distributions": {
                "email": "domain_distribution: 60% gmail.com, 40% company.com",
                "status": "categorical: 80% active, 15% pending, 5% suspended",
            },
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "table_name": "orders",
            "row_count": 120000,
            "columns": [
                {"name": "order_id", "type": "UUID", "is_pk": True},
                {"name": "user_id", "type": "UUID", "is_pk": False},
                {"name": "amount", "type": "NUMERIC", "is_pk": False},
                {"name": "order_date", "type": "TIMESTAMP", "is_pk": False},
            ],
            "foreign_keys": [
                {"column": "user_id", "target_table": "users", "target_column": "user_id"}
            ],
            "distributions": {
                "amount": "normal: mean=85.50, stddev=25.00, min=5.00, max=500.00",
            },
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "table_name": "order_items",
            "row_count": 350000,
            "columns": [
                {"name": "item_id", "type": "UUID", "is_pk": True},
                {"name": "order_id", "type": "UUID", "is_pk": False},
                {"name": "product_id", "type": "VARCHAR", "is_pk": False},
                {"name": "quantity", "type": "INT", "is_pk": False},
                {"name": "unit_price", "type": "NUMERIC", "is_pk": False},
            ],
            "foreign_keys": [
                {"column": "order_id", "target_table": "orders", "target_column": "order_id"}
            ],
            "distributions": {
                "quantity": "poisson: lambda=2.5, min=1, max=10",
                "unit_price": "uniform: min=1.99, max=99.99",
            },
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    for profile in profiles:
        doc_id = profile["table_name"]
        collection_ref.document(doc_id).set(profile)
        print(f"Seeded table profile document: {doc_id}")

    print("Firestore seeding complete!")


if __name__ == "__main__":
    seed_firestore()
