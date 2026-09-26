"""Archived provider requests with portable local persistence and environment credentials.
These adapters do not submit requests until the CLI is explicitly invoked.
"""
import asyncio, json, time, uuid, os, sys, argparse
from pathlib import Path
import aiohttp
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmark.provider_intervals import meta_events
SECRETS={k:os.environ.get(k,'') for k in ['ELEVENLABS_API_KEY','ASSEMBLYAI_API_KEY','META_API_KEY','GROK_API_KEY','GEMINI_API_KEY','SONIOX_API_KEY']}
def safe(x):
 x=str(x)
 for v in SECRETS.values():
  if v:x=x.replace(v,'<redacted>')
 return x[:1500]
def url(j):
 if not j.get('audio_url'):raise ValueError('Provide your own accessible audio_url in the jobs manifest for this provider')
 return j['audio_url']
async def persist(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False))
class Rejected(Exception):
 def __init__(self,status,body):self.status=status;self.body=body;super().__init__(f'HTTP {status}: '+safe(body))

async def response(r):
 data=await r.text()
 if r.status>=400:raise Rejected(r.status,data)
 try:return json.loads(data)
 except json.JSONDecodeError:raise ValueError('non_json_response')

async def meta_stream(client,j,state):
 # Realtime DIARIZATION on the whole recording: same model, PCM16 16 kHz, paced at 1.0x (server rejects faster).
 import wave
 hs={'model':'muse-voice-transcribe-1.0','mode':'DIARIZATION','audioEncoding':'PCM_16KHZ','partialMode':'CUMULATIVE','emitAudioProgress':True,'authorization':{'accessToken':'Bearer '+SECRETS['META_API_KEY']}}
 events=[];errors=[];state['stream_session_id']=sid=str(uuid.uuid4())
 async with client.ws_connect('wss://api.meta.ai/v1/asr/realtime',params={'sessionId':sid},heartbeat=30,max_msg_size=0) as ws:
  await ws.send_str(json.dumps(hs))
  ack=json.loads((await asyncio.wait_for(ws.receive(),30)).data)
  if ack.get('type')=='error':raise ValueError('meta_handshake_error: '+safe(ack))
  events.append(ack)
  async def receive():
   async for m in ws:
    if m.type!=aiohttp.WSMsgType.TEXT:continue
    e=json.loads(m.data);events.append(e)
    if e.get('type')=='error':errors.append(e)
  rx=asyncio.create_task(receive())
  with wave.open(j['meta_audio'],'rb') as w:
   if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(16000,1,2):raise ValueError('meta_stream_audio_not_16k_mono_pcm16')
   t0=time.monotonic();k=0
   while True:
    chunk=w.readframes(1600)
    if not chunk:break
    if errors:break
    await ws.send_bytes(chunk);k+=1
    delay=t0+k*0.1-time.monotonic()
    if delay>0:await asyncio.sleep(delay)
  await ws.send_str(json.dumps({'type':'endStream'}))
  try:await asyncio.wait_for(rx,600)
  except asyncio.TimeoutError:rx.cancel();raise ValueError('meta_stream_no_close_after_end')
 if errors:raise ValueError('meta_terminal_error: '+safe(errors[0]))
 from benchmark.provider_intervals import meta_events
 return {'sessionId':sid,'transport':'realtime_websocket_paced_1x','events':events,'turns':meta_events(events)}

async def provider_call(client,p,j,st,state):
 if p=='elevenlabs':
  form=aiohttp.FormData()
  for k,v in {'model_id':'scribe_v2','cloud_storage_url':url(j),'diarize':'true','timestamps_granularity':'word','tag_audio_events':'false','no_verbatim':'false','temperature':'0'}.items():form.add_field(k,v)
  async with client.post('https://api.elevenlabs.io/v1/speech-to-text',headers={'xi-api-key':SECRETS['ELEVENLABS_API_KEY']},data=form) as r:return await response(r)
 if p=='assemblyai':
  headers={'authorization':SECRETS['ASSEMBLYAI_API_KEY']}
  if not state.get('job_id'):
   async with client.post('https://api.assemblyai.com/v2/transcript',headers=headers,json={'audio_url':url(j),'speech_models':['universal-3-5-pro'],'speaker_labels':True,'language_detection':True}) as r:d=await response(r)
   state['job_id']=d['id'];state['phase']='submitted';await persist(st,state)
  while True:
   async with client.get('https://api.assemblyai.com/v2/transcript/'+state['job_id'],headers=headers) as r:d=await response(r)
   if d['status']=='completed':
    d.pop('audio_url',None);return d
   if d['status']=='error':raise ValueError('provider_job_error: '+str(d.get('error')))
   await asyncio.sleep(5)
 if p=='meta' and '--meta-stream' in sys.argv:return await meta_stream(client,j,state)
 if p=='grok':
  # Synchronous batch endpoint; server-side download from a presigned URL. No language hint (auto).
  form=aiohttp.FormData(default_to_multipart=True)
  for k,v in {'model':'grok-voice-transcribe-2.0','diarize':'true','filler_words':'true','url':url(j)}.items():form.add_field(k,v)
  async with client.post('https://api.x.ai/v1/stt',headers={'Authorization':'Bearer '+SECRETS['GROK_API_KEY']},data=form) as r:return await response(r)
 if p=='soniox':
  headers={'Authorization':'Bearer '+SECRETS['SONIOX_API_KEY']};base='https://api.soniox.com/v1/transcriptions'
  if not state.get('job_id'):
   async with client.post(base,headers=headers,json={'model':'stt-async-v5','audio_url':url(j),'enable_speaker_diarization':True,'enable_language_identification':True,'client_reference_id':state['request_id']}) as r:d=await response(r)
   state['job_id']=d['id'];state['phase']='submitted';await persist(st,state)
  while True:
   async with client.get(base+'/'+state['job_id'],headers=headers) as r:d=await response(r)
   if d['status']=='completed':break
   if d['status']=='error':raise ValueError('provider_job_error: '+safe(d.get('error_message')))
   await asyncio.sleep(5)
  async with client.get(base+'/'+state['job_id']+'/transcript',headers=headers) as r:t=await response(r)
  return {'transcription':d,'tokens':t.get('tokens'),'text':t.get('text')}
 if p=='meta':
  form=aiohttp.FormData();form.add_field('request',json.dumps({'mode':'DIARIZATION','model':'muse-voice-transcribe-1.0','audioEncoding':'WAV'}),content_type='application/json')
  with open(j['meta_audio'],'rb') as f:
   form.add_field('audio',f,filename=j['id']+'.wav',content_type='audio/wav')
   async with client.post('https://api.meta.ai/v1/asr/transcribe',params={'sessionId':state['request_id']},headers={'Authorization':'Bearer '+SECRETS['META_API_KEY'],**({'Accept':'text/event-stream'} if '--retry-meta-timeouts' in sys.argv else {})},data=form) as r:
    if r.status>=400 or '--retry-meta-timeouts' not in sys.argv:return await response(r)
    events=[];data=[]
    async for line in r.content:
     line=line.decode().strip()
     if line.startswith('data:'):data.append(line[5:].strip())
     elif not line and data:
      event=json.loads('\n'.join(data));data=[];events.append(event)
      if event.get('type')=='error':raise ValueError('meta_terminal_error: '+safe(event))
    if data:events.append(json.loads('\n'.join(data)))
    from benchmark.provider_intervals import meta_events
    return {'sessionId':state['request_id'],'transport':'file_upload_sse_response','events':events,'turns':meta_events(events)}
 if p=='gemini':
  h={'x-goog-api-key':SECRETS['GEMINI_API_KEY']}
  if not state.get('file_uri'):
   path=Path(j['audio']);mime='audio/flac' if path.suffix=='.flac' else 'audio/wav'
   async with client.post('https://generativelanguage.googleapis.com/upload/v1beta/files',headers={**h,'X-Goog-Upload-Protocol':'resumable','X-Goog-Upload-Command':'start','X-Goog-Upload-Header-Content-Length':str(path.stat().st_size),'X-Goog-Upload-Header-Content-Type':mime},json={'file':{'display_name':j['dataset']+'__'+j['id']}}) as r:
    if r.status>=400:await response(r)
    upload=r.headers['X-Goog-Upload-URL']
   with path.open('rb') as f:
    async with client.post(upload,headers={'X-Goog-Upload-Offset':'0','X-Goog-Upload-Command':'upload, finalize','Content-Length':str(path.stat().st_size)},data=f) as r:d=await response(r)
   state.update(file_uri=d['file']['uri'],file_name=d['file']['name'],mime_type=mime);await persist(st,state)
  async with client.post('https://generativelanguage.googleapis.com/v1beta/interactions',headers=h,json={'model':'gemini-3.5-transcribe','input':[{'type':'audio','uri':state['file_uri'],'mime_type':state['mime_type']}],'generation_config':{'transcription_config':{'mode':{'type':'verbatim','diarization_mode':'speaker','timestamp_granularities':['word']}}}}) as r:return await response(r)
 raise ValueError(p)
async def main():
 p=argparse.ArgumentParser();p.add_argument('--provider',required=True,choices=['elevenlabs','assemblyai','meta','grok','gemini','soniox']);p.add_argument('--jobs',required=True);p.add_argument('--output',required=True);p.add_argument('--concurrency',type=int,default=1);p.add_argument('--meta-stream',action='store_true',default=True);a=p.parse_args()
 if a.provider=='meta' and '--meta-stream' not in sys.argv:sys.argv.append('--meta-stream')
 jobs=json.loads(Path(a.jobs).read_text());out=Path(a.output);sem=asyncio.Semaphore(a.concurrency)
 async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None,sock_read=7200)) as client:
  async def one(j):
   dest=out/(j['dataset']+'__'+j['id']+'.json');statefile=out/'state'/dest.name
   if dest.exists():return
   if statefile.exists():raise RuntimeError('Existing request state: inspect before resubmitting a paid request')
   async with sem:
    state={'request_id':str(uuid.uuid4())};await persist(statefile,state)
    result=await provider_call(client,a.provider,j,statefile,state)
    await persist(dest,{'provider':a.provider,'dataset':j['dataset'],'recording_id':j['id'],'audio_sha256':j['audio_sha256'],'response':result})
  await asyncio.gather(*(one(j) for j in jobs))
if __name__=='__main__':asyncio.run(main())
