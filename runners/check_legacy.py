import collections,torchaudio,torch
# Compatibility for removed decoder-discovery APIs. Inputs are already loaded
# waveforms, so these APIs are not used to decode or modify evaluation audio.
if not hasattr(torchaudio,'AudioMetaData'):torchaudio.AudioMetaData=collections.namedtuple('AudioMetaData','sample_rate num_frames num_channels bits_per_sample encoding')
if not hasattr(torchaudio,'list_audio_backends'):torchaudio.list_audio_backends=lambda:['soundfile']
if not hasattr(torchaudio,'get_audio_backend'):torchaudio.get_audio_backend=lambda:'soundfile'
if not hasattr(torchaudio,'set_audio_backend'):torchaudio.set_audio_backend=lambda backend:None
