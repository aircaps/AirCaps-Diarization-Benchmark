"""Rebuild cloud RTTMs and rescore all measured website systems, without inference."""
import argparse,subprocess,sys
from pathlib import Path
MODELS=['aircaps-v1','diarizen','nemotron','3d-speaker','pyannote31','community','elevenlabs','assemblyai','meta','grok']
CLOUD=['elevenlabs','assemblyai','meta','grok']
def main():
 p=argparse.ArgumentParser();p.add_argument('--references',required=True);p.add_argument('--output',default='recomputed');p.add_argument('--workers',type=int,default=4);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 for model in MODELS:
  hypotheses=f'outputs/rttm/{model}'
  if model in CLOUD:
   hypotheses=str(out/'rttm'/model)
   subprocess.run([sys.executable,'-m','benchmark.convert','--provider',model,'--raw',f'outputs/raw/{model}','--output',hypotheses],check=True)
  args=[sys.executable,'-m','benchmark.score','--references',a.references,'--hypotheses',hypotheses,'--workers',str(a.workers),'--output',str(out/(model+'.json'))]
  if model in CLOUD:args+=['--tau','1']
  subprocess.run(args,check=True)
 subprocess.run([sys.executable,'-m','benchmark.verify_results','--scores',str(out),'--output',str(out/'verification.json')],check=True)
if __name__=='__main__':main()
