"""Development client for the user-enabled local Fusion MCP server."""
import json,sys,urllib.request,os
URL=os.environ.get('FUSION_MCP_URL','http://127.0.0.1:27182/mcp')

def post(payload,session=None):
    headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
    if session:headers['MCP-Session-Id']=session
    request=urllib.request.Request(URL,json.dumps(payload).encode(),headers)
    with urllib.request.urlopen(request,timeout=240) as response:
        raw=response.read().decode();session=response.headers.get('MCP-Session-Id',session)
    if raw.startswith('event:') or raw.startswith('data:'):
        raw=next(line[5:].strip() for line in raw.splitlines() if line.startswith('data:'))
    return json.loads(raw) if raw else None,session

if __name__=='__main__':
    payload=json.loads(open(sys.argv[1]).read())
    _,session=post({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'PrintableThreads-development','version':'1.0'}}})
    post({'jsonrpc':'2.0','method':'notifications/initialized','params':{}},session)
    result,_=post({'jsonrpc':'2.0','id':2,'method':'tools/call','params':payload},session)
    print(json.dumps(result,indent=2))
