import os,sys,json,time,argparse,traceback,random
from pathlib import Path
os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD']='1'
os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['PYANNOTE_METRICS_ENABLED']='0'
R=Path(os.environ.get('BENCHMARK_RUNTIME','.'))
credentials={'HF_TOKEN':os.environ.get('HF_TOKEN','')}
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d))
def upload(p):pass
import numpy as np,torch,soundfile as sf
p=argparse.ArgumentParser();p.add_argument('--model',required=True,choices=['3d-speaker','pyannote31','community']);p.add_argument('--jobs',default='datasets/manifest.json');p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=1);p.add_argument('--pilot',action='store_true');a=p.parse_args()
torch.set_num_threads(2);random.seed(1337);np.random.seed(1337);torch.manual_seed(1337)
manifest=Path(a.jobs)
jobs=json.loads(manifest.read_text());jobs=[j for j in jobs if a.model=='3d-speaker' or j['dataset']=='notsofar']
if a.model=='3d-speaker':jobs=[j for j in jobs if j['dataset'] in ['notsofar','ramc','dihard3','callhome','msdwild']]
if a.pilot:jobs=[next(j for j in jobs if j['dataset']=='notsofar')]
else:jobs=sorted(jobs,key=lambda j:j['duration'],reverse=True)[a.shard::a.shards]
if a.model!='community':import check_legacy
from pyannote.audio import Pipeline
if a.model=='3d-speaker':
 sys.path.insert(0,str(R/'3D-Speaker'))
 from speakerlab.bin import infer_diarization as module
 from pyannote.audio import Model,Inference
 def segmentation(token,device=None):
  model=Model.from_pretrained(str(R/'models/segmentation/pytorch_model.bin'),strict=False)
  return Inference(model,duration=model.specifications.duration,step=.1*model.specifications.duration,skip_aggregation=True,batch_size=32,device=device)
 module.get_segmentation_model=segmentation
 pipeline=module.Diarization3Dspeaker(device='cuda:0',include_overlap=True,hf_access_token=credentials['HF_TOKEN'],model_cache_dir=str(R/'modelscope'))
elif a.model=='pyannote31':
 import yaml
 cfg=yaml.safe_load((R/'models/pyannote31/config.yaml').read_text())
 cfg['pipeline']['params']['segmentation']=str(R/'models/segmentation/pytorch_model.bin');cfg['pipeline']['params']['embedding']=str(R/'models/embedding/pytorch_model.bin')
 path=R/'configs/pyannote31.yaml';path.parent.mkdir(exist_ok=True);path.write_text(yaml.safe_dump(cfg))
 pipeline=Pipeline.from_pretrained(path).to(torch.device('cuda:0'))
else:pipeline=Pipeline.from_pretrained(str(R/'models/community')).to(torch.device('cuda:0'))
print('MODEL_READY',a.model,'jobs',len(jobs),'gpu',torch.cuda.get_device_name(),flush=True)
failures=[];done=0
for j in jobs:
 rid=j['dataset']+'__'+j['id'];result=R/'results'/a.model/(rid+'.json');hyp=R/'rttm'/a.model/j['dataset']/(j['id']+'.rttm')
 if result.exists() and hyp.exists():done+=1;continue
 start=time.time()
 try:
  x,sr=sf.read(j['audio'],dtype='float32',always_2d=True);assert sr==16000 and x.shape[1]==1
  with torch.inference_mode():
   if a.model=='3d-speaker':segments=pipeline(x[:,0],wav_fs=sr)
   else:
    output=pipeline({'waveform':torch.from_numpy(x.T.copy()),'sample_rate':sr})
    ann=output.speaker_diarization if hasattr(output,'speaker_diarization') else output
    segments=[(s.start,s.end,str(sp)) for s,_,sp in ann.itertracks(yield_label=True)]
  segments=[(float(s),float(e),str(sp)) for s,e,sp in segments]
  assert all(np.isfinite(s) and np.isfinite(e) and e>=s for s,e,_ in segments)
  hyp.parent.mkdir(parents=True,exist_ok=True);tmp=hyp.with_suffix('.tmp');tmp.write_text(''.join(f'SPEAKER {j["id"]} 1 {s:.6f} {e-s:.6f} <NA> <NA> {sp} <NA> <NA>\n' for s,e,sp in segments if e>s));tmp.replace(hyp)
  write(result,{'dataset':j['dataset'],'id':j['id'],'model':a.model,'audio_sha256':j['audio_sha256'],'duration':j['duration'],'elapsed_seconds':time.time()-start,'completed_at':time.time(),'segments':segments,'oracle_speaker_count':False})
  upload(result);upload(hyp);done+=1
  print('DONE',a.model,rid,round(time.time()-start,2),len(segments),flush=True)
 except Exception as e:
  error={'id':rid,'model':a.model,'error_type':type(e).__name__,'error':str(e).replace(credentials['HF_TOKEN'],'<redacted>') if credentials['HF_TOKEN'] else str(e),'at':time.time()}
  path=R/'errors'/a.model/(rid+'.json');write(path,error);upload(path);failures.append(rid);traceback.print_exc()
  if a.pilot:raise
status=R/'status'/f'{a.model}-{a.shard}{"-pilot" if a.pilot else ""}.json';write(status,{'model':a.model,'expected':len(jobs),'done':done,'failures':failures,'finished_at':time.time()});upload(status)
if failures:sys.exit(2)
