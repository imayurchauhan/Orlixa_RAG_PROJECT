import json
from app.router import route_query
try:
    print(route_query("test", "hii"))
except Exception as e:
    import traceback
    traceback.print_exc()
