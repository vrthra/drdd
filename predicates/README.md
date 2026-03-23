# Predicates

Two families of real-world bug reproducers. A predicate is a shell script (`r.sh`) that exits 0 when an input is "interesting" (reproduces the bug) and non-zero otherwise.

---

## XML (`xml/`)

Five cases (`ticket-1e9bc83-{1..5}`) sourced from the artifact of Zhang et al. ("Toward a Better Understanding of Probabilistic Delta Debugging"). Each encodes a query-processing discrepancy between two BaseX versions: the predicate succeeds when an input XML document triggers incorrect output on the bad version (`816b386`) while the good version (`1e9bc83`) remains correct.

**Case layout:**

```
ticket-1e9bc83-<n>/
  input.xml          — original input
  input.pick/        — pre-shrunk seed variants (variant k ≤ k KB)
    1.xml … 5.xml
  query.xq           — discriminating XQuery
  config.toml        — good_version / bad_version
lib/                 — BaseX JARs
```

**Regenerate seed variants** (requires Java 11+, `nc`):

```bash
make -C predicates/xml           # all 5 cases × 5 variants
make -C predicates/xml clean     # remove all input.pick/ dirs
```

---

## FFmpeg (`ffmpeg/`)

ASAN-detected bugs across two FFmpeg commits. Each predicate fires when the instrumented binary triggers a sanitizer report on the input file. Directories prefixed `x-` are excluded from benchmarks (non-reproducible on the current build).

| Directory | Filter | Commit |
|-----------|--------|--------|
| `ticket-10686/` | `afireqsrc` | [#10686](https://trac.ffmpeg.org/ticket/10686) — `466799d` |
| `ticket-10688/` | `bwdif` | [#10688](https://trac.ffmpeg.org/ticket/10688) — `466799d` |
| `ticket-10691/` | `dialoguenhance` | [#10691](https://trac.ffmpeg.org/ticket/10691) — `466799d` |
| `ticket-10699/` | `blurdetect` | [#10699](https://trac.ffmpeg.org/ticket/10699) — `466799d` |
| `ticket-10702/` | `transpose,gradfun` | [#10702](https://trac.ffmpeg.org/ticket/10702) — `466799d` |
| `ticket-10744/` | `alimiter` | [#10744](https://trac.ffmpeg.org/ticket/10744) — `8d24a28` |
| `ticket-10745/` | `swaprect` | [#10745](https://trac.ffmpeg.org/ticket/10745) — `8d24a28` |
| `ticket-10746/` | `stereowiden` | [#10746](https://trac.ffmpeg.org/ticket/10746) — `8d24a28` |
| `ticket-10747/` | `stereotools` | [#10747](https://trac.ffmpeg.org/ticket/10747) — `8d24a28` |
| `ticket-10749/` | `showspectrumpic` | [#10749](https://trac.ffmpeg.org/ticket/10749) — `8d24a28` |
| `ticket-10754/` | `separatefields` | [#10754](https://trac.ffmpeg.org/ticket/10754) — `8d24a28` |
| `ticket-10756/` | `showwaves` | [#10756](https://trac.ffmpeg.org/ticket/10756) — `8d24a28` |
| `ticket-10758/` | `minterpolate` | [#10758](https://trac.ffmpeg.org/ticket/10758) — `8d24a28` |

### Build

```bash
make -C predicates/ffmpeg           # build lib/ffmpeg_g-<commit>
make -C predicates/ffmpeg clean     # remove the binaries
```

Clones FFmpeg at each commit, configures with clang and debug symbols, injects `-fsanitize=address`, builds, and leaves `lib/ffmpeg_g-<full-commit-hash>`.

Two deviations from the configure flags in the bug reports:

- **No `--toolchain=clang-asan`**: FFmpeg's configure runs `nm` on an ASAN-compiled test file, causing it to detect `__odr_asan_gen_` as `extern_prefix` and break the link step. ASAN flags are injected into `ffbuild/config.mak` after configure instead.
- **`--disable-x86asm`**: The `clang-asan` preset adds `-DPREFIX` to NASM flags, giving assembly symbols a leading `_` the C linker doesn't expect. The bugs are in C filter code so disabling assembly doesn't affect reproducibility.

### Reproduce

Run from `predicates/ffmpeg/lib/`:

```bash
ASAN_OPTIONS=halt_on_error=1 ./ffmpeg_g-466799d4f5 -y -i ../ticket-10699/input \
    -filter_complex blurdetect /tmp/out.mp4

ASAN_OPTIONS=halt_on_error=1 ./ffmpeg_g-466799d4f5 -y -i ../ticket-10702/input \
    -filter_complex "transpose,gradfun" /tmp/out.mp4

ASAN_OPTIONS=halt_on_error=1 ./ffmpeg_g-8d24a28d06 -y -i ../ticket-10745/input \
    -filter_complex swaprect /tmp/out.mp4
```

`halt_on_error=1` ensures a non-zero exit on any sanitizer report.

### Minimize

```bash
scripts/minimize_ffmpeg predicates/ffmpeg/ticket-10699 \
    --algorithm ddmin --verbose
# minimized output → ticket-10699/input.min
```
