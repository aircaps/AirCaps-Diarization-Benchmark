# Scoring and reporting

## Frozen evaluation

`datasets/manifest.json` fixes recording IDs, durations, audio hashes, reference RTTM hashes and UEM hashes. The primary set contains 538 recordings: AISHELL-4 (20), AliMeeting (20), AMI-SDM (16), NOTSOFAR-1 (160), RAMC (43), DIHARD III (259) and CALLHOME (20). VoxConverse (232) and MSDWild (490) add 722 recordings.

We use `pyannote.metrics.DiarizationErrorRate(collar=0, skip_overlap=False)`. Speaker mapping is optimal separately for each recording. A dataset score pools error seconds and reference speaker-seconds across recordings: `100 × (miss + false alarm + confusion) / reference speaker-time`. It is not the mean of recording DERs. Overlapping reference speakers each contribute speaker-time. The seven-dataset average is the unweighted mean of dataset DERs. Round only for display.

The scorer rejects reference/UEM checksum mismatches. A missing prediction makes that dataset incomplete. A valid empty RTTM is a no-speech hypothesis and incurs missed-speech error. The `--empty dataset/id` option is an explicit no-speech policy override, not an automatic missing-file fallback.

## ASR conversion

`provider_intervals.py` preserves the original provider-specific extraction. Word or turn timestamps are converted to seconds, clipped to the audio duration, and written at six decimal places. Invalid timestamps and missing fields follow the recorded rejection rules. `convert.py` records accepted and rejected recordings in `conversion.json`.

For headline ASR scores, use `--tau 1`: union overlapping or touching intervals for each speaker, then bridge same-speaker gaps of at most 1.0 second only if no other predicted speaker occupies any part of the gap. The other-speaker check uses the original unioned predictions, not iteratively expanded masks. It never consults reference speech. `--tau 0` unions intervals without filling positive gaps. Omit `--tau` for native diarizer outputs.

Meta uses the same rule even though its outputs are already turn-level. The conversion retains valid no-speech outputs: two Scribe and two Meta MSDWild recordings produce zero positive-duration intervals and are scored as silence. They are not dropped from dataset denominators.

## Coverage exceptions

- **AssemblyAI:** accept only `speech_model_used == universal-3-5-pro`. Substituted-model and invalid responses are excluded. Strict conversion leaves 1,225 recordings: all 538 primary, 227/232 VoxConverse, 460/490 MSDWild. Additional datasets receive no score.
- **Grok:** the recovered `DH_EVAL_0034` uses the original settings. `DH_EVAL_0181` is explicitly counted as no speech. Thus DIHARD III includes all 259 recordings. Eleven invalid empty MSDWild responses make that dataset incomplete. The extra-dataset table excludes Grok.
- **Nemotron:** all predictions are archived, but VoxConverse is excluded from reported comparisons because the model card discloses test-set training. A raw rescoring file may contain its numerical result; that is diagnostic, not an eligible benchmark result.
- **Published baselines:** Precision-3 has no archived predictions. Pyannote 3.1 and Community-1 have measured NOTSOFAR predictions only. 3D-Speaker has predictions for NOTSOFAR, RAMC, DIHARD III, CALLHOME and MSDWild. The other cells retain the authors’ reported values and may use different dataset partitions. Their mixed-source averages are computed from the released website cells.

## Reference convention

Original utterance annotations can include internal pauses. Word-aligned references remove more silence. A pause-spanning model can incur false alarms on tight labels; a tight-label model can incur missed speech on utterance labels. NVIDIA’s AMI, AliMeeting and NOTSOFAR references differ from ours. DIHARD III uses the same reference release, but other evaluations may still differ in collar or subsets. Our CALLHOME selection is not NVIDIA’s multilingual selection.

We use official NOTSOFAR utterance annotations, including filler-only utterances. DiariZen’s published NOTSOFAR result uses a different reference preparation; our measured result is 19.31%. AirCaps averaged selected checkpoints, and parts of AMI, DIHARD III and NOTSOFAR were used for selection. No confidence intervals are reported.
