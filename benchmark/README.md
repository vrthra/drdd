# Benchmark Suite

Runs all five algorithms against XML and FFmpeg predicates and writes a timestamped CSV per run.

## XML

Requires Java 11+ and `nc`.

```bash
python benchmark/scripts/bench_xml.py
```

Discovers all `ticket-*` cases under `predicates/xml/`, runs every algorithm × every input variant (1–5), and writes results under `benchmark/runs/`.

Seed inputs (`input.pick/1.xml` … `5.xml`) are already checked in. Regenerate them when predicate inputs change:

```bash
make -C predicates/xml clean     # remove all input.pick/ dirs
make -C predicates/xml           # build all missing variants
```

## FFmpeg

```bash
python benchmark/scripts/bench_ffmpeg.py
```

Discovers all `ticket-*` cases under `predicates/ffmpeg/` (excluding `x-ticket-*`), runs every algorithm against each case's `input` binary. No server setup required.

Requires `predicates/ffmpeg/lib/ffmpeg_g`. Build it first if missing:

```bash
make -C predicates/ffmpeg
```

## Output

Each run creates a directory under `benchmark/runs/` named `<label>_<DD-MM-YYYY>_<HH:MM>_git-<sha>/` containing:

| File | Contents |
|------|----------|
| `result.csv` | Per-task metrics |
| `logs/<n>_<predicate>_<algo>.log` | Full minimization trace |
