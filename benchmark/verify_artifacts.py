"""Verify all immutable archived artifacts against the release provenance index."""
import gzip,hashlib,json
from pathlib import Path

def main():
 rows=json.loads(Path('provenance/artifacts.json').read_text());failures=[]
 for row in rows:
  p=Path(row['path']);raw=p.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=row['sha256']:failures.append(row['path'])
  if p.suffix=='.gz' and hashlib.sha256(gzip.decompress(raw)).hexdigest()!=row['payload_sha256']:failures.append(row['path']+' (decompressed)')
 print(f'{len(rows)} artifacts checked; {len(failures)} failures')
 if failures:raise SystemExit('\n'.join(failures))
if __name__=='__main__':main()
