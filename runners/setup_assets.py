"""Download immutable third-party model revisions; never downloads AirCaps weights."""
import argparse,json,os,subprocess,hashlib
from pathlib import Path
from huggingface_hub import snapshot_download
MODELS={
'community':('pyannote/speaker-diarization-community-1','3533c8cf8e369892e6b79ff1bf80f7b0286a54ee'),
'pyannote31':('pyannote/speaker-diarization-3.1','84fd25912480287da0247647c3d2b4853cb3ee5d'),
'segmentation':('pyannote/segmentation-3.0','e66f3d3b9eb0873085418a7b813d3b369bf160bb'),
'embedding':('pyannote/wespeaker-voxceleb-resnet34-LM','837717ddb9ff5507820346191109dc79c958d614'),
'diarizer':('BUT-FIT/diarizen-wavlm-large-s80-md-v2','027b3e221b9d81dce2be794084f1dbd3ba2da403')}
REPOS={'DiariZen':('https://github.com/BUTSpeechFIT/DiariZen.git','844f5555b0a98acd0931511fc641a8c5b8ba92c7'),'3D-Speaker':('https://github.com/modelscope/3D-Speaker.git','065629c313eaf1a01c65c640c46d77e61e9607b4')}
def main():
 p=argparse.ArgumentParser();p.add_argument('--runtime',default='runtime');a=p.parse_args();root=Path(a.runtime);root.mkdir(parents=True,exist_ok=True)
 for name,(repo,rev) in REPOS.items():
  target=root/name
  if not target.exists():subprocess.run(['git','clone',repo,str(target)],check=True)
  subprocess.run(['git','-C',str(target),'checkout','--detach',rev],check=True)
 for name,(repo,rev) in MODELS.items():snapshot_download(repo,revision=rev,local_dir=root/'models'/name,token=os.environ.get('HF_TOKEN'))
 files={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (root/'models').rglob('*') if f.is_file() and '.cache' not in f.parts}
 (root/'downloaded-model-hashes.json').write_text(json.dumps(files,indent=2))
if __name__=='__main__':main()
