from interact_with_neo4j import driver, load_df

nodes_query = """
MATCH (n)
RETURN labels(n)[0] AS label, count(*) AS count
ORDER BY count DESC;
"""

relations_query = """
MATCH ()-[r]->()
RETURN type(r) AS type, count(*) AS count
ORDER BY count DESC;
"""

with driver.session() as session:
    nodes_df = load_df(nodes_query)
    relations_df = load_df(relations_query)

    print("Node counts:")
    print(nodes_df)
    print("\nRelation counts:")
    print(relations_df)
