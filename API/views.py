from rest_framework.decorators import api_view
from rest_framework.response import Response
from .mongo import collection_version  # importer ta collection versions

# Health check
@api_view(["GET"])
def api_status(request):
    return Response({"status": "ok"})

# Liste des technologies
@api_view(["GET"])
def api_list(request):
    return Response({
        "technologies": [
            "cassandra",
            "cockroachdb",
            "mongodb",
            "neo4j",
            "redis",
            "tidb",
            "yugabyte"
        ]
    })

# Récupérer les versions depuis MongoDB
@api_view(["GET"])
def api_get_versions(request, tech):
    results = list(collection_version.find({"database": tech}, {"_id": 0}))
    if not results:
        return Response({"error": "no data found for this technology"}, status=404)
    return Response(results)  # ← Cette ligne doit être au même niveau que le if
