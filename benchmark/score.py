"""Score saved RTTM predictions. No model inference, audio upload, or API calls."""
import argparse, concurrent.futures, hashlib, json
from pathlib import Path
from pyannote.core import Annotation, Segment, Timeline
from pyannote.metrics.diarization import DiarizationErrorRate
from .intervals import bridge
PRIMARY=['aishell4','alimeeting','ami','notsofar','ramc','dihard3','callhome']
def annotation(path,rid):
 a=Annotation(uri=rid)
 for i,line in enumerate(Path(path).read_text().splitlines()):
  v=line.split()
  if v and v[0]=='SPEAKER' and v[1]==rid and float(v[4])>0:a[Segment(float(v[3]),float(v[3])+float(v[4])),i]=v[7]
 return a
def one(args):
 j,refs,hyp,tau,empty=args;rid=j['id'];c=j['dataset'];h=Path(hyp)/c/(rid+'.rttm');r=Path(refs)/c/(rid+'.rttm');u=Path(refs)/c/(rid+'.uem')
 for f,key in [(r,'rttm_sha256'),(u,'uem_sha256')]:
  if hashlib.sha256(f.read_bytes()).hexdigest()!=j[key]:raise ValueError(f'Reference hash mismatch: {c}/{rid} {key}')
 if not h.exists() and c+'/'+rid not in empty:return {'dataset':c,'id':rid,'status':'missing'}
 region=Timeline(uri=rid)
 for line in u.read_text().splitlines():
  v=line.split()
  if v and v[0]==rid:region.add(Segment(float(v[2]),float(v[3])))
 if not region:raise ValueError('Missing scoring region')
 predicted=(bridge(h,rid,tau) if tau is not None else annotation(h,rid)) if h.exists() else Annotation(uri=rid)
 x=DiarizationErrorRate(collar=0,skip_overlap=False)(annotation(r,rid),predicted,uem=region,detailed=True)
 return {'dataset':c,'id':rid,'status':'scored','reference_seconds':x['total'],'miss':x['missed detection'],'false_alarm':x['false alarm'],'confusion':x['confusion'],'der':100*x['diarization error rate']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',default='datasets/manifest.json');p.add_argument('--references',required=True);p.add_argument('--hypotheses',required=True);p.add_argument('--tau',type=float,default=None,help='Omit for native diarizer RTTMs; use 0 for provider union or 1 for headline provider scores');p.add_argument('--datasets',default='');p.add_argument('--empty',action='append',default=[],help='Explicit dataset/id to count as no speech if absent');p.add_argument('--workers',type=int,default=4);p.add_argument('--output',required=True);a=p.parse_args()
 jobs=json.loads(Path(a.manifest).read_text());jobs=[j for j in jobs if not a.datasets or j['dataset'] in a.datasets.split(',')]
 with concurrent.futures.ProcessPoolExecutor(a.workers) as pool:rows=list(pool.map(one,[(j,a.references,a.hypotheses,a.tau,a.empty) for j in jobs],chunksize=4))
 per={}
 for c in sorted({j['dataset'] for j in jobs}):
  rr=[r for r in rows if r['dataset']==c];ok=[r for r in rr if r['status']=='scored'];den=sum(r['reference_seconds'] for r in ok)
  per[c]={'expected':len(rr),'scored':len(ok),'complete':len(rr)==len(ok),'der':100*sum(r['miss']+r['false_alarm']+r['confusion'] for r in ok)/den if len(rr)==len(ok) and den else None}
 macro=sum(per[c]['der'] for c in PRIMARY)/7 if all(c in per and per[c]['der'] is not None for c in PRIMARY) else None
 out={'protocol':{'collar':0,'overlap_included':True,'tau':a.tau},'per_corpus':per,'macro7':macro,'rows':rows};dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'per_corpus':per,'macro7':macro},indent=2))
if __name__=='__main__':main()
