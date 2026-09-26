"""Prepare only the frozen evaluation selection from user-acquired source datasets.
See docs/DATASETS.md for download sources and the source-map schema.
"""
import argparse,csv,hashlib,json,math,re,shutil,subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

def unique(root,pattern):
 matches=list(Path(root).rglob(pattern))
 if len(matches)!=1:raise ValueError(f'Expected one {pattern} under {root}; found {len(matches)}')
 return matches[0]

def lines_for(path,rid,field):
 return ''.join(l+'\n' for l in Path(path).read_text().splitlines() if l.strip() and l.split()[field]==rid)

def ramc_reference(path,rid):
 lines=[]
 for line in Path(path).read_text().splitlines():
  m=re.match(r'\[([\d.]+),\s*([\d.]+)\]\s+(\S+)',line)
  if not m:continue
  start,end=float(m[1]),float(m[2]);speaker=m[3]
  if speaker!='G00000000' and end>start:lines.append(f'SPEAKER {rid} 1 {start:.3f} {end-start:.3f} <NA> <NA> {speaker} <NA> <NA>\n')
 return ''.join(lines)

def prepare(j,spec,out,references_only=False):
 c,rid=j['dataset'],j['id'];d=Path(out)/c;d.mkdir(parents=True,exist_ok=True)
 dur=j['duration'];audio=d/Path(j['audio']).name;rt=d/(rid+'.rttm');ut=d/(rid+'.uem')
 source=None;convert=False;mean=False
 if c in ['ami','aishell4','alimeeting']:
  recipe=Path(spec['recipe'])/'recipes/diar_ssl/data/AMI_AliMeeting_AISHELL4/test'/dict(ami='AMI',aishell4='AISHELL4',alimeeting='AliMeeting')[c]
  rt.write_text(lines_for(recipe/'rttm',rid,1));ut.write_text(lines_for(recipe/'all.uem',rid,0))
  if not references_only:
   pattern=rid+'.Array1-01.wav' if c=='ami' else rid+'*.wav' if c=='alimeeting' else rid+'.*'
   matches=[f for f in Path(spec['audio']).rglob(pattern) if f.suffix in ['.wav','.flac']]
   if len(matches)!=1:raise ValueError(f'{rid}: ambiguous or missing source audio: {len(matches)}')
   source=matches[0];convert=True;mean=c=='aishell4'
 elif c=='notsofar':
  meeting,device=rid.split('-',1);base=Path(spec['root'])/'benchmark-datasets/eval_set/240629.1_eval_small_with_GT/MTG'/meeting
  rows=json.loads((base/'gt_transcription.json').read_text())
  rt.write_text(''.join(f'SPEAKER {rid} 1 {max(0,x["start_time"]):.8f} {min(dur,x["end_time"])-max(0,x["start_time"]):.8f} <NA> <NA> {x["speaker_id"]} <NA> <NA>\n' for x in rows if min(dur,x['end_time'])>max(0,x['start_time'])))
  ut.write_text(f'{rid} 1 0 {dur:.8f}\n');source=base/device/'ch0.wav';convert=True
 elif c=='ramc':
  rt.write_text(ramc_reference(unique(spec['root'],rid+'.txt'),rid));ut.write_text(f'{rid} 1 0.000 {dur:.3f}\n')
  if not references_only:source=unique(spec['root'],rid+'.wav')
 elif c=='voxconverse':
  rt.write_bytes((Path(spec['annotations'])/'test'/(rid+'.rttm')).read_bytes());ut.write_text(f'{rid} 1 0.000 {dur:.3f}\n')
  if not references_only:source=unique(spec['audio'],rid+'.wav')
 elif c=='msdwild':
  rt.write_text(lines_for(Path(spec['annotations'])/'rttms/few.val.rttm',rid,1));ut.write_text(f'{rid} 1 0.000 {dur:.3f}\n')
  if not references_only:source=unique(spec['audio'],rid+'.wav')
 elif c=='dihard3':
  rt.write_bytes(unique(spec['root'],rid+'.rttm').read_bytes());ut.write_text(f'{rid} 1 0.000 {dur:.3f}\n')
  if not references_only:source=unique(spec['root'],rid+'.flac')
 elif c=='callhome':
  # Updated WebTrans English Part 2; crop to the annotated conversation window.
  transcript=unique(Path(spec['root'])/'data/transcripts/updated',rid+'.tsv')
  with transcript.open() as f:rows=[x for x in csv.DictReader(f,delimiter='\t') if float(x['End'])>float(x['Beg'])]
  start=min(float(x['Beg']) for x in rows);end=max(float(x['End']) for x in rows)
  rt.write_text(''.join(f'SPEAKER {rid} 1 {float(x["Beg"])-start:.6f} {float(x["End"])-float(x["Beg"]):.6f} <NA> <NA> {rid}_{x["Speaker"]} <NA> <NA>\n' for x in rows));ut.write_text(f'{rid} 1 0.000000 {dur:.6f}\n')
  if not references_only:
   source=unique(Path(spec['root'])/'data/flac',rid+'.flac')
   subprocess.run(['ffmpeg','-nostdin','-y','-ss',str(start),'-t',f'{end-start:.6f}','-i',str(source),'-ac','1','-ar','16000',str(audio)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);source=None
 else:raise ValueError(c)
 if not references_only and source is not None:
  if convert:
   x,sr=sf.read(source,dtype='float32',always_2d=True)
   if mean and x.shape[1]!=8:raise ValueError('AISHELL-4 expects eight channels')
   x=x.mean(1) if mean else x[:,0]
   if sr!=16000:
    g=math.gcd(sr,16000);x=resample_poly(x,16000//g,sr//g)
   sf.write(audio,x,16000,subtype='FLOAT')
  else:shutil.copyfile(source,audio)
 check=[(rt,'rttm_sha256'),(ut,'uem_sha256')]
 if not references_only:check.append((audio,'audio_sha256'))
 for path,key in check:
  actual=hashlib.sha256(path.read_bytes()).hexdigest()
  if actual!=j[key]:raise ValueError(f'{c}/{rid}: {key} mismatch; stop and inspect source version/preparation. Expected {j[key]}, got {actual}')
 return {'dataset':c,'id':rid,'verified':True}

def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',required=True);p.add_argument('--manifest',default='datasets/manifest.json');p.add_argument('--output',default='data');p.add_argument('--datasets',default='');p.add_argument('--references-only',action='store_true');a=p.parse_args()
 source=json.loads(Path(a.sources).read_text());jobs=json.loads(Path(a.manifest).read_text());audit=[]
 for j in jobs:
  if a.datasets and j['dataset'] not in a.datasets.split(','):continue
  audit.append(prepare(j,source[j['dataset']],a.output,a.references_only))
 (Path(a.output)/'preparation.json').write_text(json.dumps(audit,indent=2));print('Verified',len(audit),'recordings')
if __name__=='__main__':main()
