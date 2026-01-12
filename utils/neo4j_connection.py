from neo4j import GraphDatabase
from django.conf import settings

class Neo4jConnection:
    def __init__(self):
        config = settings.NEO4J_CONFIG
        self.driver = GraphDatabase.driver(
            config['URI'],  
            auth=(config['USERNAME'], config['PASSWORD'])  
        )
    
    def close(self):
        self.driver.close()
    
    def get_session(self):
        config = settings.NEO4J_CONFIG
        return self.driver.session(database=config.get('DATABASE', 'neo4j'))

neo4j_conn = Neo4jConnection()