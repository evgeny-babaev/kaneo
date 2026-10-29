"""Проверка HTTPS MCP на синтетической задаче, удаляемой после проверки."""
import json,sys,urllib.request,urllib.error
from pathlib import Path
from import_linear import API,save
a=json.loads(Path(sys.argv[1]).read_text());s=json.loads(Path(sys.argv[2]).read_text())
api=API(a)
headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','Authorization':'Bearer '+api.token,'MCP-Protocol-Version':'2025-03-26'}
seq=0
def rpc(method,params):
    global seq
    seq+=1
    req=urllib.request.Request(a['url']+'/api/mcp',json.dumps({'jsonrpc':'2.0','id':seq,'method':method,'params':params}).encode(),headers,method='POST')
    with urllib.request.urlopen(req,timeout=45) as r:raw=r.read().decode()
    if raw.lstrip().startswith('{'):value=json.loads(raw)
    else:
        values=[json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith('data:')]
        value=next(v for v in values if v.get('id')==seq)
    if 'error' in value:raise RuntimeError(str(value['error']))
    return value['result']
def tool(name,args):
    r=rpc('tools/call',{'name':name,'arguments':args})
    if r.get('isError'):raise RuntimeError(str(r))
    return json.loads(next(c['text'] for c in r['content'] if c['type']=='text'))
init=rpc('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'global-deploy-smoke','version':'1'}})
tools=rpc('tools/list',{})['tools']
p=s['projects']['unprojected']
task=tool('create_task',{'projectId':p['id'],'title':'Проверка MCP развёртывания','description':'Синтетическая задача; удаляется проверкой.','priority':'high','status':p['statuses']['Todo'],'dueDate':'2026-11-01T12:00:00+03:00'})
tid=task['id']
try:
    tool('update_task_status',{'taskId':tid,'status':p['statuses']['Done']})
    result=tool('get_task',{'taskId':tid})
    assert result['status']==p['statuses']['Done'] and result['priority']=='high'
finally:
    tool('delete_task',{'taskId':tid})
req=urllib.request.Request(a['url']+'/api/mcp',b'{}',{'Content-Type':'application/json'},method='POST')
try:urllib.request.urlopen(req);raise AssertionError('Unauthenticated MCP accepted')
except urllib.error.HTTPError as e:assert e.code==401
with urllib.request.urlopen(a['url']+'/.well-known/oauth-protected-resource/api/mcp') as r:meta=json.load(r)
assert meta['resource']==a['url']+'/api/mcp'
report={'ok':True,'tools':len(tools),'protocol':init.get('protocolVersion'),'create_update_read_delete':True,'unauthenticated':401,'oauth_discovery':True}
save(Path(sys.argv[1]).parent/'mcp-verification.json',report)
print(json.dumps(report))
