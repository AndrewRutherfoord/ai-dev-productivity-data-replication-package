from neo4j import GraphDatabase
import pandas as pd
import matplotlib.pyplot as plt
from typing import Any, cast

HOST = "100.65.19.90"
URI = f"neo4j://{HOST}:7687"
USER = "neo4j"
PASSWORD = "neo4j123"

date_format = "yyyy-MM-dd HH:mm:ss"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def load_df(query: str) -> pd.DataFrame:
    with driver.session() as session:
        data = session.run(cast(Any, query)).data()
    return pd.DataFrame(data)