# Running the third-party models

The checked reproduction route is saved-output scoring. These adapters also expose the actual model loading, inference and provider requests used for the released predictions. They do not contain AirCaps implementation or weights. Upstream implementations are dependencies fetched from their original repositories, not reimplemented here. All runs use the same frozen audio selection and no oracle speaker counts.

## Environment separation

Use Linux with a CUDA GPU for diarizers. Keep scoring in its own environment (`requirements.txt`). Community-1 uses a newer pyannote stack than the legacy models. The recorded full package inventories are `runners/community-packages.txt`, `runners/pyannote31-packages.txt`, and `runners/3d-speaker-packages.txt`; they are environment evidence, not requirements for a CPU scorer.

The measured pyannote/3D-Speaker run used RTX 5090 GPUs, PyTorch and TorchAudio 2.11.0+cu128, two CPU threads per worker and seed 1337. Install that CUDA build from the PyTorch cu128 index, then use pyannote.audio 3.3.2 for 3D-Speaker/3.1 or pyannote.audio 4.0.4 for Community-1. The inventories record the other exact packages. `check_legacy.py` supplies the removed TorchAudio metadata aliases needed by the old stack.

```bash
# In a separate model environment, after installing its Torch/pyannote stack:
pip install huggingface_hub modelscope==1.40.1 funasr==1.4.16
export HF_TOKEN=your_personal_token
python runners/setup_assets.py --runtime runtime
export BENCHMARK_RUNTIME=runtime
python runners/pipelines.py --model 3d-speaker --jobs datasets/manifest.json
# In the appropriate separate environments:
python runners/pipelines.py --model pyannote31 --jobs datasets/manifest.json
python runners/pipelines.py --model community --jobs datasets/manifest.json
```

Accept the upstream gated model terms before downloading. Never commit your token. Outputs go to `runtime/rttm/{model}/{dataset}/`. The runner selects the five measured 3D-Speaker datasets and NOTSOFAR for the two pyannote pipelines. Use `--shard N --shards K` to distribute jobs, setting `CUDA_VISIBLE_DEVICES` externally.

## DiariZen Large v2

`runners/setup_assets.py` fetches `BUTSpeechFIT/DiariZen@844f5555b0a98acd0931511fc641a8c5b8ba92c7`, its forked pyannote implementation, diarizer weights at `027b3e221b9d81dce2be794084f1dbd3ba2da403`, and the WeSpeaker embedding at `837717ddb9ff5507820346191109dc79c958d614`. Install the pinned checkout’s dependencies in a separate environment (follow its README), then:

```bash
python runners/diarizen.py --runtime runtime --jobs datasets/manifest.json \
  --output runtime/rttm/diarizen
```

The runner imports the pinned fork, disables TF32, uses four CPU threads, segmentation and embedding batch sizes of 128, and resets Torch seed to 0 for each recording. It verifies input audio hashes. Legacy checkpoints require trusted pickle loading; use only the pinned upstream downloads.

## Nemotron 3 Diarization, offline

The recorded NeMo version was `3.1.0+5dbdde6`, resolved to `NVIDIA/NeMo@5dbdde68d3897c03faeda1b0d9655cd90b1c5e08`.

```bash
pip install 'nemo_toolkit[asr] @ git+https://github.com/NVIDIA/NeMo.git@5dbdde68d3897c03faeda1b0d9655cd90b1c5e08'
python runners/nemotron.py --jobs datasets/manifest.json --config offline \
  --output runtime/rttm/nemotron --batch-size 8
```

This loads `nvidia/Nemotron-3-Diarization`, uses BF16 autocast, and sets speaker cache 264, FIFO 40, chunk 340, right context 40 and cache update period 300 (80 ms frames). This is a 30.4-second input buffer. Predictions are written at three decimal places. The historical model download did not record an immutable Hugging Face revision; the model identifier alone cannot guarantee fresh inference is byte-identical. The released predictions and verified scores preserve the actual run.

## 3D-Speaker and pyannote pins

- 3D-Speaker source: `065629c313eaf1a01c65c640c46d77e61e9607b4`; native `Diarization3Dspeaker` with overlap enabled and default clustering. The segmentation loader is overridden to use the frozen local pyannote checkpoint. ModelScope CAMPPlus identifier: `iic/speech_campplus_sv_zh_en_16k-common_advanced` (`v1.0.0`); FSMN VAD uses `v2.0.4`. ModelScope resolves these through the pinned upstream pipeline; retain its downloaded asset report when rerunning.
- Community-1 model: `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`; use regular `speaker_diarization`, not exclusive output.
- Pyannote 3.1 model: `84fd25912480287da0247647c3d2b4853cb3ee5d`.
- Segmentation 3.0: `e66f3d3b9eb0873085418a7b813d3b369bf160bb`.
- WeSpeaker embedding: `837717ddb9ff5507820346191109dc79c958d614`.

## Four cloud providers

`runners/cloud_asr.py` contains the archived HTTP/WebSocket request logic with local persistence and environment-only credentials. It makes paid requests only when invoked. Copy `.env.example` as a reminder of the variable names; the script reads the environment, not the file automatically.

Create a private jobs JSON from `datasets/manifest.json`. For Scribe, AssemblyAI and Grok, add an `audio_url` for each exact prepared audio file, accessible to that provider. Keep these URLs out of Git. Meta instead uses the local `meta_audio` PCM16 path generated by `python -m benchmark.pcm16`. Keep whole recordings; do not split them.

| Adapter | Recorded request |
| --- | --- |
| `elevenlabs` | Scribe `scribe_v2`; diarize true, word timestamps, audio-event tags false, no_verbatim false, temperature 0; file-URL batch request. |
| `assemblyai` | `speech_models: [universal-3-5-pro]`, speaker labels true, language detection true; submit once and poll the async transcript endpoint. |
| `meta` | `muse-voice-transcribe-1.0`, DIARIZATION mode, PCM_16KHZ, cumulative partials; whole-file WebSocket paced at 1× realtime, followed by endStream and terminal completion. The public display name is Meta Muse Voice Transcribe. |
| `grok` | `grok-voice-transcribe-2.0`, diarize true, filler_words true, automatic language; file-URL batch request. |

```bash
python runners/cloud_asr.py --provider elevenlabs --jobs private-jobs.json \
  --output new-results/elevenlabs --concurrency 1
python -m benchmark.convert --provider elevenlabs --raw new-results/elevenlabs \
  --output new-rttm/elevenlabs
python -m benchmark.score --references data --hypotheses new-rttm/elevenlabs \
  --tau 1 --output recomputed/new-elevenlabs.json
```

Set concurrency to your account’s supported capacity; concurrency does not define the scoring protocol. Do not infer universal quotas from the original run. Existing request state prevents silent duplicate paid submissions; inspect failed state before explicitly retrying. API responses and private jobs created by new runs may contain personal or access metadata: do not commit them without the same release audit.

Supplemental Gemini and Soniox adapters are retained with their original settings but are not part of the website comparison. No inference runner exists for AirCaps or Precision-3: AirCaps is outputs-only by design, and Precision-3 cells are authors’ published numbers.
