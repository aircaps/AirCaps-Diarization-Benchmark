"""Rebuild native RTTMs from saved API responses, enforcing the requested model."""
import argparse,gzip,json
from pathlib import Path
from .provider_intervals import rttm,meta_events

def main():
 p=argparse.ArgumentParser();p.add_argument('--provider',required=True);p.add_argument('--manifest',default='datasets/manifest.json');p.add_argument('--raw',required=True);p.add_argument('--output',required=True);a=p.parse_args();jobs=json.loads(Path(a.manifest).read_text());audit=[]
 for j in jobs:
  f=Path(a.raw)/(j['dataset']+'__'+j['id']+'.json.gz');plain=f.with_suffix('');dest=Path(a.output)/j['dataset']/(j['id']+'.rttm')
  if not f.exists() and not plain.exists():continue
  data=json.loads(gzip.decompress(f.read_bytes()) if f.exists() else plain.read_bytes());response=data.get('response',data)
  try:
   if a.provider=='meta' and 'events' in response:response={**response,'turns':meta_events(response['events'])}
   if a.provider=='assemblyai' and response.get('speech_model_used')!='universal-3-5-pro':raise ValueError('substitute_model_excluded')
   if a.provider=='grok' and j['dataset']=='dihard3' and j['id']=='DH_EVAL_0181' and not response.get('words'):
    text,clipped='',0  # Published protocol: retain this recording as no speech.
   else:text,clipped=rttm(a.provider,response,j['id'],j['duration'])
   # A valid response with zero speech intervals is scored as silence.
   # Missing/invalid responses still raise in provider_intervals.
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text);audit.append({'dataset':j['dataset'],'id':j['id'],'status':'converted','clipped':clipped})
  except ValueError as e:
   if dest.exists():dest.unlink()
   audit.append({'dataset':j['dataset'],'id':j['id'],'status':str(e)})
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True);(out/'conversion.json').write_text(json.dumps(audit,indent=2))
if __name__=='__main__':main()
