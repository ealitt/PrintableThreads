import json,sys
from fusion_mcp import post
_,session=post({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'thread-fix','version':'1'}}})
post({'jsonrpc':'2.0','method':'notifications/initialized','params':{}},session)
payload=json.loads(sys.stdin.read())
result,_=post({'jsonrpc':'2.0','id':2,'method':payload.pop('method','tools/call'),'params':payload},session)
print(json.dumps(result,indent=2))
