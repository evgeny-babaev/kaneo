"""Полная read-only сверка миграции с PostgreSQL, без доступа к таблицам паролей."""
import collections, datetime, json, subprocess, sys
from pathlib import Path
from import_linear import description, due, comment_parts, relation_set, PRIORITIES, save

def main():
    source,state_path=map(Path,sys.argv[1:3])
    m=json.loads((source/'manifest.json').read_text());s=json.loads(state_path.read_text())
    issues=[i for f in m['issue_files'] for i in json.loads((source/f).read_text())]
    docs={d['id']:d for d in (json.loads(p.read_text()) for p in source.glob('document-*.json'))}
    for i in issues:i['documents']=[docs.get(d['id'],d) for d in i.get('documents') or []]
    tables=['task','project','column','label','activity','task_relation','custom_field_value']
    pairs=','.join("'"+t+"',(SELECT coalesce(json_agg(t),'[]'::json) FROM \""+t+"\" t)" for t in tables)
    raw=subprocess.check_output(['docker','exec','kaneo-global-postgres-1','psql','-U','kaneo','-d','kaneo','-At','-c','SELECT json_build_object('+pairs+');'])
    db=json.loads(raw);tasks={t['id']:t for t in db['task']};comments={c['id']:c for c in db['activity'] if c['type']=='comment'}
    errors=[]
    def check(ok,message):
        if not ok:errors.append(message)
    check(len(tasks)==len(issues),'task count')
    check(len(db['project'])==len(s['projects']),'project count')
    fields={(f['task_id'],f['field_id']):f['value'] for f in db['custom_field_value']}
    labels=collections.defaultdict(set)
    for l in db['label']:
        if l['task_id']:labels[l['task_id']].add(l['name'])
    for i in issues:
        tid=s['tasks'][i['uuid']];t=tasks.get(tid);p=s['projects'][i.get('projectId') or 'unprojected']
        if not t:errors.append(i['id']+' missing');continue
        expected={'title':f"[{i['id']}] {i['title']}",'description':description(i),'project_id':p['id'],'priority':PRIORITIES[(i.get('priority') or {}).get('value',0)],'status':'archived' if i.get('archivedAt') else p['statuses'][i['status']],'assignee_id':s['userId'] if i.get('assigneeId')==m['user']['id'] else None}
        for key,value in expected.items():check(t[key]==value,i['id']+' '+key)
        expected_due=due(i)
        actual=t['due_date']
        if expected_due:
            actual_dt=datetime.datetime.fromisoformat(actual)
            if actual_dt.tzinfo is None:actual_dt=actual_dt.replace(tzinfo=datetime.timezone.utc)
            check(actual_dt==datetime.datetime.fromisoformat(expected_due),i['id']+' due')
        else:check(actual is None,i['id']+' unexpected due')
        expected_labels=set(i.get('labels') or [])
        if i.get('archivedAt'):expected_labels.add('Linear: Archived')
        check(labels[tid]==expected_labels,i['id']+' labels')
        if i.get('estimate') is not None:check(fields.get((tid,p['estimateField']))==str(i['estimate']['value']),i['id']+' estimate')
        for c in i.get('comments') or []:
            for cid,text,author in comment_parts(c):
                row=comments.get(s['comments'][cid],{})
                check(row.get('task_id')==tid and row.get('content')==text,i['id']+' comment '+cid)
    actual_rel={(r['relation_type'],r['source_task_id'],r['target_task_id']) for r in db['task_relation']}
    expected_rel={(kind,s['tasks'][a],s['tasks'][b]) for kind,a,b in relation_set(issues)}
    def canonical(rows):
        return {(kind,*sorted([a,b])) if kind=='related' else (kind,a,b) for kind,a,b in rows}
    check(canonical(actual_rel)==canonical(expected_rel),'relations')
    check(len(comments)==len(s['comments']),'comments count')
    check(all(not p['is_public'] for p in db['project']),'public projects')
    report={'ok':not errors,'tasks':len(tasks),'projects':len(db['project']),'comments':len(comments),'relations':len(actual_rel),'history':sum(len(i.get('stateHistory') or []) for i in issues),'errors':errors}
    save(source/'verification.json',report);print(json.dumps(report,ensure_ascii=False))
    if errors:sys.exit(1)
if __name__=='__main__':main()
