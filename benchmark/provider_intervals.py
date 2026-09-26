"""Native provider intervals -> RTTM; never use reference labels or bridge pauses."""
import math

def seconds(v):
 if isinstance(v,str):return float(v.removesuffix('s'))
 if isinstance(v,dict):return float(v.get('seconds',0))+float(v.get('nanos',0))/1e9
 return float(v)

def segments(provider,response):
 out=[]
 if provider=='elevenlabs':
  if 'words' not in response:raise ValueError('missing_words')
  for w in response['words']:
   if w.get('type')=='word' and w.get('speaker_id') is not None:out.append((w['start'],w['end'],str(w['speaker_id'])))
 elif provider=='assemblyai':
  if response.get('status')!='completed' or response.get('utterances') is None:raise ValueError('missing_utterances')
  for w in response['utterances']:
   if w.get('speaker') is not None:out.append((w['start']/1000,w['end']/1000,str(w['speaker'])))
 elif provider=='meta':
  if 'turns' not in response:raise ValueError('missing_turns')
  for w in response['turns']:
   if w.get('speaker') is not None:out.append((w['startMs']/1000,w['endMs']/1000,str(w['speaker'])))
 elif provider=='gemini':
  def walk(x):
   if isinstance(x,dict):
    if x.get('type')=='word_info':
     if x.get('speaker') is not None:out.append((seconds(x['start_offset']),seconds(x['end_offset']),str(x['speaker'])))
    else:
     for v in x.values():walk(v)
   elif isinstance(x,list):
    for v in x:walk(v)
  walk(response)
  if not out:raise ValueError('missing_word_info_annotations')
 elif provider=='grok':
  if 'words' not in response:raise ValueError('missing_words')
  for w in response['words']:
   if w.get('speaker') is not None:out.append((float(w['start']),float(w['end']),str(w['speaker'])))
 elif provider=='soniox':
  if 'tokens' not in response:raise ValueError('missing_tokens')
  for t in response['tokens']:
   if t.get('speaker') is not None and t.get('start_ms') is not None:out.append((t['start_ms']/1000,t['end_ms']/1000,str(t['speaker'])))
 else:raise ValueError(provider)
 if not out and any(response.get(k) for k in ['text','transcript']):raise ValueError('text_without_speaker_intervals')
 for a,b,sp in out:
  if not (math.isfinite(a) and math.isfinite(b)):raise ValueError('nonfinite_interval')
  if b<a and provider!='gemini':raise ValueError('invalid_interval')
 return out

def rttm(provider,response,rid,duration):
 out=[];clipped=0
 for a,b,sp in segments(provider,response):
  if b<a:clipped+=1;continue  # Gemini occasionally emits reversed word times; retain raw, discard impossible span.
  aa=max(0.,a);bb=min(duration,b);clipped+=int(aa!=a or bb!=b)
  if bb>aa:out.append(f'SPEAKER {rid} 1 {aa:.6f} {bb-aa:.6f} <NA> <NA> {sp.replace(" ","_")} <NA> <NA>\n')
 return ''.join(out),clipped


def meta_events(events):
 """Map Meta's native speaker events to intervals; preserve events for auditing."""
 turns={};active=None;out=[]
 for e in events:
  typ=e.get('type');rid=e.get('turnId',active)
  if typ=='speechStart':
   active=rid;turns[rid]={'start':e['audioProcessedMs'],'last':e['audioProcessedMs'],'complete':False}
  elif typ=='speaker':
   if rid not in turns:raise ValueError('speaker_without_speechStart')
   t=turns[rid];end=e['audioProcessedMs'];out.append({'turnId':rid,'startMs':t['last'],'endMs':end,'speaker':e['label']});t['last']=end
  elif typ=='speechComplete':
   if rid in turns:turns[rid]['complete']=True
 if any(not v['complete'] for v in turns.values()):raise ValueError('incomplete_meta_sse_turns')
 if not out and turns:raise ValueError('meta_sse_missing_speaker_events')
 return out
