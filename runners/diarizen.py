"""Pinned DiariZen Large v2 inference; no AirCaps implementation."""
import argparse, hashlib, json, os, sys, types
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--jobs',default='datasets/manifest.json');p.add_argument('--runtime',default='runtime');p.add_argument('--output',required=True);p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=1);a=p.parse_args()
 root=Path(a.runtime).resolve();repo=root/'DiariZen'
 sys.path[:0]=[str(repo/'pyannote-audio'),str(repo)]
 import pyannote
 pyannote.__path__=[str(repo/'pyannote-audio/pyannote'),*pyannote.__path__]
 v=types.ModuleType('pyannote.audio.version');v.__version__=(repo/'pyannote-audio/version.txt').read_text().strip();v.git_version='844f5555b0a98acd0931511fc641a8c5b8ba92c7';sys.modules[v.__name__]=v
 # These legacy checkpoints use pickle: only load the pinned, trusted upstream assets.
 os.environ['TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD']='1'
 import torch
 from diarizen.pipelines.inference import DiariZenPipeline
 torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
 pipe=DiariZenPipeline(root/'models/diarizer',str(root/'models/embedding/pytorch_model.bin'))
 pipe._segmentation.batch_size=128;pipe.embedding_batch_size=128
 jobs=json.loads(Path(a.jobs).read_text())[a.shard::a.shards]
 for j in jobs:
  if hashlib.sha256(Path(j['audio']).read_bytes()).hexdigest()!=j['audio_sha256']:raise ValueError('Audio checksum mismatch: '+j['id'])
  dest=Path(a.output)/j['dataset']/(j['id']+'.rttm')
  if dest.exists():continue
  torch.manual_seed(0)
  with torch.inference_mode():hyp=pipe(j['audio'],sess_name=j['id'])
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(hyp.to_rttm());print(j['dataset'],j['id'],flush=True)
if __name__=='__main__':main()
