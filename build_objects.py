#!/usr/bin/env python3
"""build_objects.py — collapse every frame into a content-addressed object store.

objects/<hash[:2]>/<frame_hash>.json  ->  the frame, addressed by its wave hash.
objects/index.json                    ->  every payload_hash / frame_hash / rappid -> path.

Given any quantum key you construct the raw URL directly (frame_hash is the filename);
payload_hash and rappid resolve through the index. No search, no database.
"""
import json, os, glob

OBJ = "objects"
os.makedirs(OBJ, exist_ok=True)
index = {}
nframes = 0

for fpath in sorted(glob.glob("snapshots/*/frames.jsonl")):
    snap = fpath.split("/")[1]
    for line in open(fpath):
        line = line.strip()
        if not line:
            continue
        fr = json.loads(line)                       # preserves 11-key order
        fh, ph = fr["frame_hash"], fr["payload_hash"]
        shard = os.path.join(OBJ, fh[:2])
        os.makedirs(shard, exist_ok=True)
        rel = f"{OBJ}/{fh[:2]}/{fh}.json"
        with open(os.path.join(shard, fh + ".json"), "w") as o:
            json.dump(fr, o, ensure_ascii=False, separators=(",", ":"))
        index[fh] = {"path": rel, "kind": "frame.wave", "snapshot": snap, "seq": fr["seq"]}
        index[ph] = {"path": rel, "kind": "frame.particle", "snapshot": snap, "seq": fr["seq"]}
        nframes += 1

for rp in sorted(glob.glob("snapshots/*/rappid.public.json")):
    snap = rp.split("/")[1]
    d = json.load(open(rp))
    index[d["rappid"]] = {"path": f"snapshots/{snap}/", "kind": "twin.rappid", "snapshot": snap}

with open(os.path.join(OBJ, "index.json"), "w") as f:
    json.dump({"schema": "rapp-objects-index/1.0", "count": nframes,
               "note": "Every frame is an object addressed by its frame_hash. payload_hash and rappid resolve here too. The key is the address.",
               "objects": index}, f, ensure_ascii=False, indent=0, sort_keys=True)

print(f"wrote {nframes} frame objects across {len(glob.glob(OBJ+'/*/'))} shards; {len(index)} index entries")
