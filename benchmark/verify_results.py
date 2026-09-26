"""Check recomputed scores and optional website HTML against the release tables."""
import argparse,json,re,hashlib
from pathlib import Path
MODEL_IDS={'AirCaps Diarization-v1':'aircaps-v1','DiariZen Large v2':'diarizen','Nemotron 3 Diarization':'nemotron','pyannote Community-1':'community','pyannote 3.1':'pyannote31','3D-Speaker':'3d-speaker','ElevenLabs Scribe v2':'elevenlabs','AssemblyAI U3.5 Pro':'assemblyai','Meta Muse Voice Transcribe':'meta','Grok Voice Transcribe 2.0':'grok'}
PUBLISHED={'pyannoteAI Precision-3':None,'pyannote Community-1':{'notsofar'},'pyannote 3.1':{'notsofar'},'3D-Speaker':{'notsofar','ramc','dihard3','callhome','msdwild'}}
def main():
 p=argparse.ArgumentParser();p.add_argument('--website',help='Optional website checkout path');p.add_argument('--scores',default='results/recomputed');p.add_argument('--output',default='results/verification.json');a=p.parse_args()
 d=json.loads(Path('results/website.json').read_text());checks=[];failures=[]
 for m in d['models']:
  name=m['name'];ident=MODEL_IDS.get(name);score=json.loads((Path(a.scores)/(ident+'.json')).read_text()) if ident else None
  for c,v in zip(d['corpora'],m['values']):
   if v is None:continue
   measured=name not in PUBLISHED or (PUBLISHED[name] is not None and c in PUBLISHED[name])
   row={'model':name,'dataset':c,'displayed':f'{v:.2f}','origin':'rescored' if measured else 'published-only'}
   if measured:
    got=score['per_corpus'][c]['der'];row.update(recomputed=got,match=got is not None and f'{got:.2f}'==f'{v:.2f}')
    if not row['match']:failures.append(row)
   checks.append(row)
  canonical=sum(m['values'][d['corpora'].index(c)] for c in d['primary_corpora'])/7
  if abs(canonical-m['macro7'])>1e-9:failures.append({'model':name,'error':'macro7 is not the mean of canonical cells'})
  if score and score['macro7'] is not None and f"{score['macro7']:.2f}"!=f"{m['macro7']:.2f}":failures.append({'model':name,'error':'rescored macro differs'})
 if a.website:
  from bs4 import BeautifulSoup
  site=Path(a.website);s=BeautifulSoup((site/'diarization.html').read_text(),'html.parser')
  if json.loads((site/'docs/diarization-results.json').read_text())!=d:failures.append({'error':'website JSON differs'})
  by={m['name']:m for m in d['models']}
  for table,columns,macro in [('primary-results',d['primary_corpora'],True),('additional-results',d['additional_corpora'],False)]:
   for tr in s.select('#'+table+' tbody tr'):
    cells=[td.get_text(' ',strip=True) for td in tr.select('td')];name=cells[0];m=by.get(name)
    if not m:failures.append({'error':'unknown HTML model','model':name});continue
    expected=[f"{m['values'][d['corpora'].index(c)]:.2f}" for c in columns]+([f"{m['macro7']:.2f}"] if macro else [])
    actual=[re.search(r'\d+\.\d+',x).group() if re.search(r'\d+\.\d+',x) else x for x in cells[1:]]
    if actual!=expected:failures.append({'error':'HTML table differs','model':name,'table':table,'expected':expected,'actual':actual})
  for f in Path('figures').glob('*.png'):
   if hashlib.sha256(f.read_bytes()).digest()!=hashlib.sha256((site/'assets'/f.name).read_bytes()).digest():failures.append({'error':'figure bytes differ','figure':f.name})
 result={'passed':not failures,'display_precision':2,'measured_cells':sum(x['origin']=='rescored' for x in checks),'published_only_cells':sum(x['origin']=='published-only' for x in checks),'cells':checks,'failures':failures}
 Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cells'},indent=2))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
