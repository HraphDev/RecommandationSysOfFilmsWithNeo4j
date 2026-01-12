from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "vivamaroc")
)

with driver.session() as session:
    result = session.run("RETURN 'CONNECTED' AS msg")
    print(result.single()["msg"])
