from django.http import HttpResponse
from django.db import connections
from django.db.utils import OperationalError

def health_check(request):
    try:
        db_conn = connections['default']
        db_conn.cursor()
    except OperationalError:
        return HttpResponse("Database unavailable", status=503)
    return HttpResponse("OK")
