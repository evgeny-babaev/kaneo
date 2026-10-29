"""Импорт EVG: SNAPSHOT ACCESS STATE. Приватные файлы находятся вне Git."""
import json, os, re, sys, time
from pathlib import Path
import urllib.request, urllib.error

PRIORITIES={0:'no-priority',1:'urgent',2:'high',3:'medium',4:'low'}
def save(path,data):
    path=Path(path); tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    os.chmod(tmp,0o600); tmp.replace(path)
def markdown(value):
    return re.sub(r'<issue\b[^>]*href="([^"]+)"[^>]*>(.*?)</issue>',lambda m:f'[{m[2]}]({m[1]})',value or '',flags=re.S)
def due(i):
    return i['dueDate']+'T23:59:59+03:00' if i.get('dueDate') else None
def description(i):
    parts=[markdown(i.get('description')),'\n---\n## Источник Linear',f"Источник: [{i['id']}]({i['url']})",f"Linear UUID: {i['uuid']}",f"Статус Linear: {i['status']}"]
    for key in ['createdAt','updatedAt','completedAt','canceledAt','archivedAt','dueDate','assignee']:
        if i.get(key): parts.append(f'{key}: {i[key]}')
    if i.get('estimate') is not None: parts.append(f"Оценка Linear: {i['estimate']['value']} points (не часы)")
    if i['statusType'] in ['canceled','duplicate']:
        parts.append('Конечная колонка означает закрытость, а не выполненную работу.')
    if i.get('stateHistory'):
        parts.append('### История статусов Linear')
        for r in i['stateHistory']: parts.append(f"- {r.get('startedAt')} → {r.get('endedAt') or 'на момент выгрузки'}: {r['state']['name']}")
    for key in ['attachments','documents']:
        for item in i.get(key) or []:
            parts.append(f"- [{item.get('title') or item.get('name') or item.get('id')}]({item.get('url') or ''})")
            if item.get('content'): parts.append(markdown(item['content']))
    if i.get('relations'): parts.append('### Исходные связи Linear\n'+json.dumps(i['relations'],ensure_ascii=False))
    return '\n\n'.join(parts)
class API:
    def __init__(self,access):
        self.base=os.environ.get('KANEO_IMPORT_BASE',access['url']).rstrip('/');self.origin=access['url'];self.token=None
        r=self.call('/api/auth/sign-in/email','POST',{'email':access['email'],'password':access['password']})
        self.token=r['token'];self.user=r['user']['id']
    def call(self,path,method='GET',body=None):
        headers={'Content-Type':'application/json','Origin':self.origin}
        if self.token: headers['Authorization']='Bearer '+self.token
        for attempt in range(8):
            req=urllib.request.Request(self.base+path,json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers,method=method)
            try:
                with urllib.request.urlopen(req,timeout=60) as r:
                    raw=r.read();return json.loads(raw) if raw else None
            except urllib.error.HTTPError as e:
                detail=e.read().decode()
                if e.code==429: time.sleep(max(5,int(e.headers.get('Retry-After',15))));continue
                if e.code>=500 and method=='GET' and attempt<7: time.sleep(2+attempt);continue
                raise RuntimeError(f'{method} {path}: {e.code} {detail[:800]}') from None
        raise RuntimeError('Retry budget exhausted')
    def tasks(self,pid):
        result=[];page=1
        while True:
            r=self.call(f'/api/task/tasks/{pid}?page={page}&limit=100');b=r['data']
            result.extend(t for c in b['columns'] for t in c['tasks'])
            result.extend(b['plannedTasks']);result.extend(b['archivedTasks'])
            if page>=r['pagination']['totalPages']:return list({t['id']:t for t in result}.values())
            page+=1
def comment_parts(c):
    author=(c.get('author') or {}).get('name') or 'Linear'
    body=markdown(c.get('body'))
    if c.get('quotedText'):body+='\n\nЦитата: '+c['quotedText']
    for a in c.get('attachments') or []:body+=f"\n[{a.get('title') or 'Вложение'}]({a.get('url')})"
    chunks=[body[n:n+8500] for n in range(0,len(body),8500)] or ['']
    return [(f"{c['id']}:{n}",f"Импорт из Linear. Автор: {author}. Дата: {c.get('createdAt')}.\nLinear comment: {c['id']}:{n}\n\n"+v,author) for n,v in enumerate(chunks)]
def relation_set(issues):
    known={i['id']:i['uuid'] for i in issues};known.update({i['uuid']:i['uuid'] for i in issues});result=set()
    for i in issues:
        a=i['uuid']
        if i.get('parentId') in known:result.add(('subtask',known[i['parentId']],a))
        for kind,rows in (i.get('relations') or {}).items():
            if not rows:continue
            if isinstance(rows,dict):rows=[rows]
            for r in rows:
                b=known.get(r['id'])
                if not b or a==b:continue
                if kind=='blocks':result.add(('blocks',a,b))
                elif kind=='blockedBy':result.add(('blocks',b,a))
                else:result.add(('related',*sorted([a,b])))
    return result
def main():
    source,access_path,state_path=map(Path,sys.argv[1:4])
    m=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    issues=[i for f in m['issue_files'] for i in json.loads((source/f).read_text(encoding='utf-8'))]
    docs={d['id']:d for d in (json.loads(p.read_text(encoding='utf-8')) for p in source.glob('document-*.json'))}
    for i in issues:i['documents']=[docs.get(d['id'],d) for d in i.get('documents') or []]
    assert len(issues)==m['issue_count']==len({i['uuid'] for i in issues})
    api=API(json.loads(access_path.read_text(encoding='utf-8')))
    s=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {'projects':{},'tasks':{},'comments':{},'relations':{},'enriched':[]}
    checkpoint=lambda:save(state_path,s)
    ws=next((w for w in api.call('/api/auth/organization/list') if w['slug']=='evg'),None)
    if ws is None:ws=api.call('/api/auth/organization/create','POST',{'name':'Личные задачи','slug':'evg'})
    s['workspaceId']=ws['id'];s['userId']=api.user;checkpoint()
    api.call('/api/auth/organization/set-active','POST',{'organizationId':ws['id']})
    projects=m['projects']+[{'uuid':'unprojected','name':'Без проекта','description':''}]
    projects=[p for p in projects if any((i.get('projectId') or 'unprojected')==p['uuid'] for i in issues)]
    existing=api.call('/api/project?workspaceId='+ws['id'])
    for n,p in enumerate(projects):
        key=p['uuid'];slug='EVG'+str(n+1)
        if key not in s['projects']:
            matches=[x for x in existing if x['slug']==slug];assert len(matches)<=1
            q=matches[0] if matches else api.call('/api/project','POST',{'workspaceId':ws['id'],'name':p['name'],'icon':'folder','slug':slug})
            s['projects'][key]={'id':q['id']};checkpoint()
        target=s['projects'][key];pid=target['id']
        api.call('/api/project/'+pid,'PUT',{'name':p['name'],'icon':'folder','slug':slug,'description':markdown(p.get('description'))+f"\n\nLinear project UUID: {key}\n"+(p.get('url') or ''),'isPublic':False})
        cols={c['name']:c for c in api.call('/api/column/'+pid)}
        wanted=['Todo','In Progress','Done','Backlog','Canceled','Duplicate']
        wanted+=sorted({i['status'] for i in issues if (i.get('projectId') or 'unprojected')==key}-set(wanted))
        for name in wanted:
            if name=='Todo' and name not in cols and 'To Do' in cols:
                c=cols.pop('To Do');cols[name]=api.call('/api/column/'+c['id'],'PUT',{'name':name})
            if name not in cols:cols[name]=api.call('/api/column/'+pid,'POST',{'name':name,'isFinal':name in ['Done','Canceled','Duplicate']})
        target['statuses']={name:c['slug'] for name,c in cols.items()}
        fields=api.call('/api/custom-field/project/'+pid)
        field=next((f for f in fields if f['name']=='Оценка Linear (points)'),None)
        if field is None:field=api.call('/api/custom-field','POST',{'projectId':pid,'name':'Оценка Linear (points)','type':'number','required':False})
        target['estimateField']=field['id'];checkpoint()
        for t in api.tasks(pid):
            match=re.match(r'^\[(EVG-\d+)\]',t['title'])
            if match:
                src=next((i for i in issues if i['id']==match[1]),None)
                if src:
                    prev=s['tasks'].get(src['uuid']);assert not prev or prev==t['id'],'Duplicate marker'
                    s['tasks'][src['uuid']]=t['id']
        checkpoint()
    print('Projects ready:',len(projects),flush=True)
    labels={l['name']:l['id'] for l in api.call('/api/label/workspace/'+ws['id'])}
    for n,i in enumerate(sorted(issues,key=lambda x:int(x['id'].split('-')[1]))):
        target=s['projects'][i.get('projectId') or 'unprojected']
        if i['uuid'] not in s['tasks']:
            body={'title':f"[{i['id']}] {i['title']}",'description':description(i),'priority':PRIORITIES[(i.get('priority') or {}).get('value',0)],'status':'archived' if i.get('archivedAt') else target['statuses'][i['status']]}
            if i.get('assigneeId')==m['user']['id']:body['userId']=api.user
            if due(i):body['dueDate']=due(i)
            if i.get('estimate') is not None:body['customFields']=[{'fieldId':target['estimateField'],'value':str(i['estimate']['value'])}]
            t=api.call('/api/task/'+target['id'],'POST',body);s['tasks'][i['uuid']]=t['id'];checkpoint()
        tid=s['tasks'][i['uuid']]
        if i['uuid'] not in s['enriched']:
            names=list(i.get('labels') or [])
            if i.get('archivedAt'):names.append('Linear: Archived')
            assigned={l['name'] for l in api.call('/api/label/task/'+tid)}
            for name in names:
                if name not in labels:labels[name]=api.call('/api/label','POST',{'name':name,'color':'#64748b','workspaceId':ws['id']})['id']
                if name not in assigned:api.call('/api/label/'+labels[name]+'/task','PUT',{'taskId':tid})
            comments=api.call('/api/comment/'+tid) if i.get('comments') else []
            for c in i.get('comments') or []:
                for cid,text,author in comment_parts(c):
                    if cid in s['comments']:continue
                    matches=[x for x in comments if f'Linear comment: {cid}\n' in x['content']]
                    created=matches[0] if matches else api.call('/api/comment/'+tid,'POST',{'content':text,'externalUserName':author[:120],'externalSource':'linear'})
                    s['comments'][cid]=created['id'];checkpoint()
            s['enriched'].append(i['uuid']);checkpoint()
        if n%50==0:print('Tasks:',n+1,'/',len(issues),flush=True)
    for kind,a,b in sorted(relation_set(issues)):
        key=f'{kind}:{a}:{b}'
        if key in s['relations']:continue
        aid,bid=s['tasks'][a],s['tasks'][b]
        matches=[r for r in api.call('/api/task-relation/'+aid) if r['relationType']==kind and {r['sourceTaskId'],r['targetTaskId']}=={aid,bid}]
        result=matches[0] if matches else api.call('/api/task-relation','POST',{'sourceTaskId':aid,'targetTaskId':bid,'relationType':kind})
        s['relations'][key]=result['id'];checkpoint()
        if len(s['relations'])%100==0:print('Relations:',len(s['relations']),flush=True)
    assert len(s['tasks'])==len(issues)==len(s['enriched'])
    assert len(s['comments'])==sum(len(comment_parts(c)) for i in issues for c in i.get('comments') or [])
    assert len(s['relations'])==len(relation_set(issues))
    report={'tasks':len(s['tasks']),'projects':len(s['projects']),'comments':len(s['comments']),'relations':len(s['relations']),'history':sum(len(i.get('stateHistory') or []) for i in issues)}
    save(source/'import-result.json',report);print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
