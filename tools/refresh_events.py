#!/usr/bin/env python3
"""Validate a Spotts connector snapshot and atomically update the website data."""
import collections, datetime, glob, json, math, os, pathlib, re, sys, tempfile
from urllib.parse import urlparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
PARTS=ROOT/'work-refresh'
audit_path=PARTS/'audit.json'
if not audit_path.exists(): raise SystemExit('Missing query audit; refusing to replace the published data.')
audit=json.loads(audit_path.read_text(encoding='utf-8-sig'))
if audit.get('fail') or audit.get('jobs',0)<103: raise SystemExit('Incomplete or failed query audit; keeping existing data.')
files=list(PARTS.glob('part-*.json'))
if not files: raise SystemExit('No result parts; keeping existing data.')
raw=[]
for file in files:
 value=json.loads(file.read_text(encoding='utf-8-sig'))
 if not isinstance(value,list): raise SystemExit('Invalid result part: '+str(file))
 raw.extend(value)
if len(raw)<100: raise SystemExit('Too few records; keeping existing data.')
html=(ROOT/'index.html').read_text(encoding='utf-8-sig')
marker='const DISTRICTS='
pos=html.index(marker)+len(marker)
features=json.JSONDecoder().raw_decode(html[pos:])[0]['features']
def polys(g): return [g['coordinates']] if g['type']=='Polygon' else g['coordinates']
def bbox(f):
 pts=[p for poly in polys(f['geometry']) for ring in poly for p in ring]
 return min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)
bboxes=[bbox(f) for f in features]
def inside(r,x,y):
 hit=False;j=len(r)-1
 for i in range(len(r)):
  xi,yi=r[i];xj,yj=r[j]
  if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:hit=not hit
  j=i
 return hit
def contains(g,x,y):return any(inside(p[0],x,y) and not any(inside(h,x,y) for h in p[1:]) for p in polys(g))
seen=set();results=[];excluded=collections.Counter()
for e in raw:
 if not isinstance(e,dict): excluded['invalid']+=1;continue
 url=e.get('url',''); host=urlparse(url).hostname
 if host not in ('spotts.kr','www.spotts.kr') or urlparse(url).scheme!='https' or not urlparse(url).path.startswith('/f/'): excluded['invalid_url']+=1;continue
 if url in seen:continue
 seen.add(url)
 if not isinstance(e.get('name'),str) or not e['name'].strip():excluded['invalid_name']+=1;continue
 if not all(isinstance(e.get(k),str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',e[k]) for k in ('start','end')):excluded['missing_date']+=1;continue
 try:
  begin=datetime.date.fromisoformat(e['start']); end=datetime.date.fromisoformat(e['end'])
 except ValueError:excluded['invalid_date']+=1;continue
 if end<begin or e.get('status') not in ('ongoing','upcoming'):excluded['inactive']+=1;continue
 x=e.get('longitude');y=e.get('latitude')
 if not isinstance(x,(int,float)) or isinstance(x,bool) or not isinstance(y,(int,float)) or isinstance(y,bool) or not math.isfinite(x) or not math.isfinite(y):excluded['no_coordinates']+=1;continue
 matches=[f for f,b in zip(features,bboxes) if b[0]<=x<=b[2] and b[1]<=y<=b[3] and contains(f['geometry'],x,y)]
 if len(matches)!=1:excluded['outside_boundary']+=1;continue
 f=matches[0]['properties'];results.append({k:e.get(k) for k in ('name','start','end','status','venue','latitude','longitude','url','category')}|{'region':f['SIG_KOR_NM'],'province':f['CTPRVN_CD']})
previous=ROOT/'events.json'
old_count=0
if previous.exists():
 try:old_count=len(json.loads(previous.read_text(encoding='utf-8-sig')).get('events',[]))
 except (ValueError,OSError):raise SystemExit('Existing data unreadable; refusing replacement.')
if len(results)<max(100,old_count//2):raise SystemExit('Unexpectedly few valid results; keeping existing data.')
results.sort(key=lambda e:(e['start'],e['name']))
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
data={'source':'Spotts','checked_at':now.isoformat(timespec='seconds'),'query_count':audit['jobs'],'capped_query_count':len(audit.get('cap',[])),'excluded':dict(excluded),'events':results}
fd,temp=tempfile.mkstemp(prefix='.events-',suffix='.tmp',dir=ROOT)
try:
 with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:json.dump(data,f,ensure_ascii=False,separators=(',',':'));f.write('\n')
 os.replace(temp,ROOT/'events.json')
finally:
 if os.path.exists(temp):os.unlink(temp)
print(json.dumps({'count':len(results),'checked_at':data['checked_at'],'capped':data['capped_query_count'],'excluded':data['excluded']},ensure_ascii=False))
