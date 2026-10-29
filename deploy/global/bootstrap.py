"""Первый владелец через локальный API до подключения публичного маршрута."""
import json, os, urllib.request, urllib.error
from pathlib import Path

p=Path('/opt/configs/kaneo/access.json')
a=json.loads(p.read_text())
base=os.environ['KANEO_IMPORT_BASE']
def call(path,body):
    req=urllib.request.Request(base+path,json.dumps(body).encode(),{'Content-Type':'application/json','Origin':a['url']},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
    except urllib.error.HTTPError as e:
        detail=e.read().decode()
        raise RuntimeError(str(e.code)+' '+detail[:300]) from None
try:
    r=call('/api/auth/sign-in/email',{'email':a['email'],'password':a['password']})
except RuntimeError as e:
    if not str(e).startswith('401'):raise
    r=call('/api/auth/sign-up/email',{'email':a['email'],'password':a['password'],'name':a['name']})
a['userId']=r['user']['id']
p.write_text(json.dumps(a,ensure_ascii=False,indent=2));p.chmod(0o600)
print('Owner created or verified:',a['userId'])
