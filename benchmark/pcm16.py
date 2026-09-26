"""Create the exact whole-file PCM16 inputs used by the Meta adapter."""
import argparse,hashlib,json,shutil
from pathlib import Path
import soundfile as sf

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',default='datasets/manifest.json');a=p.parse_args()
 for j in json.loads(Path(a.manifest).read_text()):
  source=Path(j['audio']);dest=Path(j['meta_audio']);dest.parent.mkdir(parents=True,exist_ok=True);info=sf.info(source)
  if info.subtype=='PCM_16' and source.suffix=='.wav':shutil.copyfile(source,dest)
  else:
   x,sr=sf.read(source,dtype='float64');sf.write(dest,x,sr,subtype='PCM_16')
  if hashlib.sha256(dest.read_bytes()).hexdigest()!=j['meta_audio_sha256']:raise ValueError('PCM16 hash mismatch: '+j['id'])
if __name__=='__main__':main()
