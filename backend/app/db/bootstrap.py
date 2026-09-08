from sqlalchemy import Engine, text

DDL = [
    """CREATE TABLE IF NOT EXISTS dim_product (
        product_id INTEGER PRIMARY KEY, product_name TEXT NOT NULL, category TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS dim_region (
        region_id INTEGER PRIMARY KEY, region_name TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sales_fact (
        id INTEGER PRIMARY KEY, month DATE NOT NULL, product_id INTEGER NOT NULL,
        region_id INTEGER NOT NULL, revenue NUMERIC NOT NULL, cost NUMERIC NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY(product_id) REFERENCES dim_product(product_id),
        FOREIGN KEY(region_id) REFERENCES dim_region(region_id)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_sales_month ON sales_fact(month)",
    "CREATE INDEX IF NOT EXISTS idx_sales_product ON sales_fact(product_id)",
]


PRODUCTS = [(1, "工业传感器A", "传感器"), (2, "工业传感器B", "传感器"), (3, "控制器C", "控制器")]
REGIONS = [(1, "华东"), (2, "华南"), (3, "华北")]
SALES = [
    (1, "2026-01-01", 1, 1, 120000, 72000, 1000),
    (2, "2026-01-01", 2, 2, 95000, 57000, 760),
    (3, "2026-01-01", 3, 3, 135000, 82000, 520),
    (4, "2026-02-01", 1, 1, 112000, 73500, 910),
    (5, "2026-02-01", 2, 2, 90000, 59000, 705),
    (6, "2026-02-01", 3, 3, 130000, 83000, 500),
    (7, "2026-03-01", 1, 1, 98000, 75500, 770),
    (8, "2026-03-01", 2, 2, 86000, 60500, 660),
    (9, "2026-03-01", 3, 3, 126000, 84000, 480),
    (10, "2026-04-01", 1, 1, 91000, 76000, 700),
    (11, "2026-04-01", 2, 2, 84000, 61000, 635),
    (12, "2026-04-01", 3, 3, 123000, 85000, 465),
]


def bootstrap_database(engine: Engine) -> None:
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
        count = conn.execute(text("SELECT COUNT(*) FROM sales_fact")).scalar_one()
        if count:
            return
        conn.execute(
            text("INSERT INTO dim_product(product_id, product_name, category) VALUES (:id,:name,:category)"),
            [{"id": row[0], "name": row[1], "category": row[2]} for row in PRODUCTS],
        )
        conn.execute(
            text("INSERT INTO dim_region(region_id, region_name) VALUES (:id,:name)"),
            [{"id": row[0], "name": row[1]} for row in REGIONS],
        )
        conn.execute(
            text("""INSERT INTO sales_fact(id,month,product_id,region_id,revenue,cost,quantity)
                  VALUES (:id,:month,:product,:region,:revenue,:cost,:quantity)"""),
            [
                {"id": r[0], "month": r[1], "product": r[2], "region": r[3],
                 "revenue": r[4], "cost": r[5], "quantity": r[6]}
                for r in SALES
            ],
        )

