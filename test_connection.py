import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FNeo.settings')
django.setup()

from utils.neo4j_connection import neo4j_conn

def test_connection():
    try:
        with neo4j_conn.get_session() as session:
            result = session.run("RETURN 'Connected!' AS message")
            message = result.single()["message"]
            print(f"✅ {message}")
        
        with neo4j_conn.get_session() as session:
            result = session.run("SHOW DATABASES")
            databases = [record["name"] for record in result]
            print(f"📊 Available databases: {databases}")
            
        # Check config
        from django.conf import settings
        print(f"📋 Config: {settings.NEO4J_CONFIG}")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()