"""NVIDIA Nemotron inference on a portable evaluation manifest."""
import argparse, json, os, time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

CONFIGS = {  # spkcache_len, fifo_len, chunk_len, chunk_right_context, spkcache_update_period (80 ms frames)
    "offline": (264, 40, 340, 40, 300),   # 30.4 s input buffer
    "1s": (264, 264, 9, 4, 222),          # 1.04 s input buffer
}


def load_audio(path):
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    if sr != 16000:
        raise ValueError(f"{path}: sample rate {sr}, expected 16000")
    return x[:, 0], x.shape[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jobs", required=True); p.add_argument("--config", required=True, choices=CONFIGS)
    p.add_argument("--output", required=True); p.add_argument("--shard", type=int, default=0)
    p.add_argument("--shards", type=int, default=1); p.add_argument("--device", default="cuda:0")
    p.add_argument("--batch-size", type=int, default=8)
    a = p.parse_args()

    from nemo.collections.asr.models import SortformerEncLabelModel
    model = SortformerEncLabelModel.from_pretrained("nvidia/Nemotron-3-Diarization", map_location=a.device)
    model.eval()
    sm = model.sortformer_modules
    sm.spkcache_len, sm.fifo_len, sm.chunk_len, sm.chunk_right_context, sm.spkcache_update_period = CONFIGS[a.config]
    model._check_streaming_parameters()

    jobs = json.load(open(a.jobs))
    jobs = [j for i, j in enumerate(jobs) if i % a.shards == a.shard]
    out = Path(a.output)
    todo = [j for j in jobs if not (out / j["dataset"] / f"{j['id']}.rttm").exists()]
    todo.sort(key=lambda j: j["duration"])  # similar lengths per batch
    log = {"config": a.config, "params": CONFIGS[a.config], "shard": a.shard, "jobs": len(jobs), "todo": len(todo),
           "multichannel_inputs": [], "batches": []}
    for b in range(0, len(todo), a.batch_size):
        batch = todo[b:b + a.batch_size]
        audios = []
        for j in batch:
            x, ch = load_audio(j["audio"])
            if ch != 1:
                log["multichannel_inputs"].append([j["id"], ch])
            audios.append(x)
        t0 = time.time()
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            segs = model.diarize(audio=audios, batch_size=len(audios), sample_rate=16000)
        dt = time.time() - t0
        for j, s in zip(batch, segs):
            d = out / j["dataset"]; d.mkdir(parents=True, exist_ok=True)
            lines = []
            for seg in s:
                st, en, spk = seg.split() if isinstance(seg, str) else seg
                st, en = float(st), float(en)
                if en > st:
                    lines.append(f"SPEAKER {j['id']} 1 {st:.3f} {en - st:.3f} <NA> <NA> {spk} <NA> <NA>\n")
            tmp = d / f".{j['id']}.rttm.tmp"
            tmp.write_text("".join(lines)); os.replace(tmp, d / f"{j['id']}.rttm")
        log["batches"].append({"n": len(batch), "audio_s": sum(j["duration"] for j in batch), "seconds": dt})
        print(f"[{a.config} shard {a.shard}] {b + len(batch)}/{len(todo)} rtfx={sum(j['duration'] for j in batch) / dt:.0f}", flush=True)
    (out / f"worker-{a.config}-{a.shard}.json").write_text(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
