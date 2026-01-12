import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
    raise RuntimeError("Neo4j environment variables are not set")

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD)
)

def get_session():
    return driver.session()
def test_connection():
    try:
        with driver.session() as session:
            result = session.run("RETURN 'Neo4j Connected' AS message")
            return result.single()["message"]
    except Exception as e:
        return f"Connection failed: {e}"
