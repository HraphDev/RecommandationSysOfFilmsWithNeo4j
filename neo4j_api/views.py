from django.http import JsonResponse
from utils.neo4j_connection import Neo4jConnection
from django.conf import settings

def test_connection(request):
    try:
        uri = getattr(settings, 'NEO4J_URI', 'neo4j://127.0.0.1:7687')
        user = getattr(settings, 'NEO4J_USER', 'neo4j')
        password = getattr(settings, 'NEO4J_PASSWORD', 'password')
        conn = Neo4jConnection(uri, user, password)
        result = conn.query("RETURN 'Connection successful!' as message")
        conn.close()
 
        return JsonResponse({'status': 'success','message': 'Neo4j working','data': result  })
        
    except Exception as e:
        return JsonResponse({'status': 'erreur','message': str(e)}, status=500)