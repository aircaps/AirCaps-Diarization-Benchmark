"""Reference-independent same-speaker union and optional gap bridging."""
import bisect
from pathlib import Path
from pyannote.core import Annotation, Segment
def merged(iv):
 out=[]
 for a,b in sorted(iv):
  if out and a<=out[-1][1]:out[-1][1]=max(out[-1][1],b)
  else:out.append([a,b])
 return out
def bridge(path,rid,tau):
 by={}
 for l in Path(path).read_text().splitlines():
  v=l.split()
  if v and v[0]=='SPEAKER' and v[1]==rid and float(v[4])>0:by.setdefault(v[7],[]).append((float(v[3]),float(v[3])+float(v[4])))
 by={k:merged(v) for k,v in by.items()};h=Annotation(uri=rid)
 for sp,segs in by.items():
  oth=merged([s for o,v in by.items() if o!=sp for s in v]);starts=[s[0] for s in oth];cmax=[];m=-1
  for s in oth:m=max(m,s[1]);cmax.append(m)
  out=[list(segs[0])]
  for a,b in segs[1:]:
   ga,gb=out[-1][1],a;i=bisect.bisect_left(starts,gb)
   busy=i>0 and cmax[i-1]>ga
   if gb-ga<=tau and not busy:out[-1][1]=b
   else:out.append([a,b])
  for a,b in out:h[Segment(a,b),len(h)]=sp
 return h
