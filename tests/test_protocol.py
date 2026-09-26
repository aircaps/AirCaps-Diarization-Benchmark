import hashlib,json,tempfile,unittest
from pathlib import Path
from benchmark.intervals import bridge
from benchmark.provider_intervals import rttm,meta_events
from benchmark.score import one

class ProtocolTests(unittest.TestCase):
 def test_bridge_only_unoccupied_gaps(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'x.rttm'
   p.write_text('SPEAKER x 1 0 1 <NA> <NA> A <NA> <NA>\nSPEAKER x 1 1.5 1 <NA> <NA> A <NA> <NA>\n')
   self.assertAlmostEqual(bridge(p,'x',1).get_timeline().duration(),2.5)
   p.write_text(p.read_text()+'SPEAKER x 1 1.1 0.2 <NA> <NA> B <NA> <NA>\n')
   a=bridge(p,'x',1);self.assertAlmostEqual(a.label_timeline('A').duration(),2)
 def test_clipping_and_units(self):
  text,clipped=rttm('assemblyai',{'status':'completed','utterances':[{'start':-100,'end':1200,'speaker':'A'}]},'x',1)
  self.assertIn('0.000000 1.000000',text);self.assertEqual(clipped,1)
 def test_valid_silence_and_invalid_missing_data(self):
  self.assertEqual(rttm('elevenlabs',{'words':[]},'x',1)[0],'')
  with self.assertRaisesRegex(ValueError,'missing_words'):rttm('grok',{},'x',1)
 def test_meta_terminal_events(self):
  events=[{'type':'speechStart','turnId':'t','audioProcessedMs':0},{'type':'speaker','turnId':'t','audioProcessedMs':500,'label':'A'}]
  with self.assertRaisesRegex(ValueError,'incomplete'):meta_events(events)
  self.assertEqual(meta_events(events+[{'type':'speechComplete','turnId':'t'}])[0]['endMs'],500)
 def test_overlap_counts_speaker_time_and_empty_counts_misses(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'c').mkdir();rt=root/'c/x.rttm';ut=root/'c/x.uem'
   rt.write_text('SPEAKER x 1 0 2 <NA> <NA> A <NA> <NA>\nSPEAKER x 1 1 1 <NA> <NA> B <NA> <NA>\n');ut.write_text('x 1 0 2\n')
   j={'dataset':'c','id':'x','rttm_sha256':hashlib.sha256(rt.read_bytes()).hexdigest(),'uem_sha256':hashlib.sha256(ut.read_bytes()).hexdigest()}
   row=one((j,str(root),str(root/'absent'),None,['c/x']))
   self.assertEqual(row['reference_seconds'],3);self.assertEqual(row['miss'],3);self.assertEqual(row['der'],100)
   row=one((j,str(root),str(root/'absent'),None,[]));self.assertEqual(row['status'],'missing')
   j['rttm_sha256']='wrong'
   with self.assertRaisesRegex(ValueError,'hash mismatch'):one((j,str(root),str(root),None,[]))
if __name__=='__main__':unittest.main()
