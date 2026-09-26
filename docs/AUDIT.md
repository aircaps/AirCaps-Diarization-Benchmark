# Release verification

The audit uses the public scoring code on saved predictions and the frozen reference files. It does not rerun hosted APIs or claim bit-identical GPU inference.

- Every one of the **66 measured values in the website data** matches the website at two decimal places. The **29 published-only cells** are separately marked and copied consistently; they cannot be regenerated without original predictions.
- AirCaps, DiariZen, Nemotron, the measured 3D-Speaker datasets and both pyannote NOTSOFAR runs were independently rescored.
- All four website providers were converted again from saved raw responses and scored with 1.0-second bridging. Meta’s speaker events are converted into turns using the released parser.
- Reference and UEM hashes were checked for every scored recording. Preparation was independently regenerated from the original public annotations for 981 recordings across seven datasets; every generated reference matched. The licensed CALLHOME and DIHARD inputs were checked as frozen references, without reacquiring those source distributions.
- The website table manifest, primary and additional HTML tables, and three PNG files match this repository. The relative table uses the same full-precision source averages. DiariZen’s website dataset cells were historically stored at two decimal places; rescoring retains more precision but reproduces the displayed values and average.
- The website’s AISHELL-4 description was corrected to the actual eight-channel mean-to-mono preparation.

`results/verification.json` is the machine-readable cell audit. `results/recomputed/` contains per-recording errors, pooled scores and completeness counts. The figure-generation scripts also regenerate all three PNGs byte-for-byte. The synthetic tests exercise overlap speaker-time, missing versus no-speech outputs, clipping, blocked gap bridging and Meta terminal events.

## Artifact provenance and disclosure audit

`provenance/artifacts.json` records the released and original hashes of archived artifacts. RTTM bytes are retained. JSON is normalized, deterministically gzip-compressed and stripped of deployment paths, signed URLs, authentication/account fields and storage details. `provenance/redactions.json` describes removed field paths. Original-byte hashes bind the sanitized release to the source archive without exposing its private location.

AirCaps contributes only final RTTMs and scoring outcomes. No AirCaps implementation, architecture, training code, checkpoints, weights or internal variant identifiers are included. The release is scanned in decompressed form before Git staging; no source audio, original reference annotations or environment credential files are included.

## Repeat the checks

```bash
python -m benchmark.reproduce --references data --output recomputed
python -m benchmark.verify_results --scores recomputed
python -m benchmark.verify_artifacts
python -m unittest discover -s tests
# Optional: additionally compare a local website checkout:
python -m benchmark.verify_results --website /path/to/research-site
```

New GPU/API runs can change because of hardware, library differences or provider updates. The historical Nemotron model revision was not recorded; its source revision and offline settings were. These limitations do not affect reproducing the published scores from the supplied predictions.
