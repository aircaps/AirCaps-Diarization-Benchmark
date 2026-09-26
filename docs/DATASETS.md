# Dataset acquisition and preparation

No source audio or original annotations are bundled. Obtain each dataset through its official distribution and accept its terms. The manifest is the exact evaluation selection; do not substitute a similarly named split.

| Dataset | Source | Exact selection and audio handling |
| --- | --- | --- |
| AISHELL-4 | [AISHELL/AISHELL-4](https://huggingface.co/datasets/AISHELL/AISHELL-4) | 20 test recordings; average the eight channels to mono, 16 kHz float WAV. |
| AliMeeting | [OpenSLR 119](https://www.openslr.org/119/) | 20 Test far-field recordings; first array channel, 16 kHz float WAV. |
| AMI-SDM | [AMI corpus](https://groups.inf.ed.ac.uk/ami/corpus/) | 16 recordings in DiariZen’s test selection; Array1-01, 16 kHz float WAV. |
| NOTSOFAR-1 | [microsoft/NOTSOFAR](https://huggingface.co/datasets/microsoft/NOTSOFAR) | 160 single-channel devices in eval_small_with_GT; device ch0, 16 kHz float WAV. |
| RAMC | [OpenSLR 123](https://www.openslr.org/123/) | Official 43-recording test split; original 16 kHz mono WAV unchanged. |
| DIHARD III | [LDC2022S14](https://catalog.ldc.upenn.edu/LDC2022S14) | Full evaluation, 259 recordings; original FLAC unchanged. Licensed access required. |
| CALLHOME | [LDC2026S08](https://catalog.ldc.upenn.edu/LDC2026S08) | Updated WebTrans English Part 2, 20 conversations. Crop first to last annotated turn; downmix to mono and resample to 16 kHz. Licensed access required. |
| VoxConverse | [joonson/voxconverse](https://github.com/joonson/voxconverse) | Official test, 232 recordings; original 16 kHz mono WAV unchanged. |
| MSDWild | [X-LANCE/MSDWILD](https://github.com/X-LANCE/MSDWILD) | The 490 IDs in `rttms/few.val.rttm`; original WAV unchanged. |

## Source versions

- DiariZen recipes: `BUTSpeechFIT/DiariZen@844f5555b0a98acd0931511fc641a8c5b8ba92c7`.
- AISHELL-4 dataset: `aada72727856313b19d4a030383c426364931dbf`.
- NOTSOFAR dataset: `ba8fd0f034ce185fe4d24f47e53b4b8194795f07`.
- VoxConverse annotation repository: `24bf60be297701cd7e4ef18550c6d390c1b87365`.
- MSDWild annotation repository: `b9f97946f7001e86f643d893811fbded918407bc`; independently checked to reproduce every frozen test reference.

AMI audio paths follow `https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/{id}/audio/{id}.Array1-01.wav`. AliMeeting’s test archive is `https://speech-lab-share-data.oss-cn-shanghai.aliyuncs.com/AliMeeting/openlr/Test_Ali.tar.gz`; use its far-field WAVs. The MSDWild README links its audio archive (published MD5 `0057f82daaddf2ce993d1bf0679929c4`). Other archive and model download links are provided by the sources above.

## Build the exact inputs

1. Download/extract the sources and checkout the pinned annotation repositories. Preserve original filenames. For NOTSOFAR preserve its full repository path structure.
2. Copy `datasets/sources.example.json` to `datasets/sources.local.json` and edit each path. `recipe` points to the pinned DiariZen checkout. `root`/`audio` point to extracted distributions.
3. Run `python -m benchmark.prepare --sources datasets/sources.local.json --output data`. Use `--datasets aishell4,ami` for a subset or `--references-only` when only rescoring outputs.
4. The script checks every generated file against frozen SHA256 values. An error is a source/preparation mismatch; do not override the manifest to silence it. SoundFile/FFmpeg versions can change audio container bytes; diagnose such differences explicitly.
5. For Meta inference, run `python -m benchmark.pcm16`. Existing PCM16 WAVs are copied; other formats are decoded as float64 and written to PCM16 WAV. The derived file hashes are also frozen.

### Reference construction

AMI, AISHELL-4 and AliMeeting use per-ID lines from the pinned DiariZen recipe `rttm` and `all.uem` files, preserving text formatting. NOTSOFAR uses each meeting’s `gt_transcription.json`: clip start/end to the device duration, retain all positive-duration speaker spans, write eight decimal places. RAMC converts `[start,end] speaker` TXT rows to RTTM with three decimals, excluding `G00000000`. VoxConverse uses the official test RTTMs unchanged. MSDWild filters `few.val.rttm` by recording ID without changing lines. DIHARD uses the original evaluation RTTM. The frozen whole-file UEM is written to three decimals for RAMC, VoxConverse, MSDWild and DIHARD.

CALLHOME reads `data/transcripts/updated/{id}.tsv`, retains positive-duration rows, crops the original `data/flac/{id}.flac` from minimum Beg to maximum End, and shifts annotations by the crop start. Speaker labels are `{id}_{Speaker}` and times have six decimal places. The FFmpeg command is captured in `benchmark/prepare.py`.

The release audit regenerated exact reference/UEM hashes from source annotations for the seven freely accessible datasets (981 recordings). CALLHOME and DIHARD scoring was verified against the frozen references; reacquiring and rebuilding those two licensed distributions was not part of the release audit. Their expected hashes and preparation code are provided for license holders.
