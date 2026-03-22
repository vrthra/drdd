# Predicates

Two families of real-world bug reproducers. A predicate is a shell script (`r.sh`) that exits 0 when an input is "interesting" (reproduces the bug) and non-zero otherwise.

---

## XML (`xml/`)

Five cases (`xml-1e9bc83-{1..5}`) sourced from the artifact of Zhang et al. ("Toward a Better Understanding of Probabilistic Delta Debugging"). Each encodes a query-processing discrepancy between two BaseX versions: the predicate succeeds when an input XML document triggers incorrect output on the bad version (`816b386`) while the good version (`1e9bc83`) remains correct.

**Case layout:**

```
xml-1e9bc83-<n>/
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

Four ASAN-detected bugs in FFmpeg commit `466799d`. Each predicate exits 0 when the instrumented binary (`ffmpeg_g`) triggers a sanitizer report on the input file.

| Directory | Filter | Bug |
|-----------|--------|-----|
| `ffmpeg-466799d-1/` | `blurdetect` | [#10699](https://trac.ffmpeg.org/ticket/10699) — heap-buffer-overflow |
| `ffmpeg-466799d-2/` | `afwtdn` | [#10700](https://trac.ffmpeg.org/ticket/10700) — heap-buffer-overflow |
| `ffmpeg-466799d-3/` | `colorcorrect` | [#10701](https://trac.ffmpeg.org/ticket/10701) — LeakSanitizer |
| `ffmpeg-466799d-4/` | `transpose,gradfun` | [#10702](https://trac.ffmpeg.org/ticket/10702) — heap-buffer-overflow |

### Build

```bash
make -C predicates/ffmpeg           # build lib/ffmpeg_g
make -C predicates/ffmpeg clean     # remove the binary
```

Clones FFmpeg at `466799d`, configures with clang and debug symbols, injects `-fsanitize=address`, builds, and leaves `lib/ffmpeg_g`.

Two deviations from the configure flags in the bug reports:

- **No `--toolchain=clang-asan`**: FFmpeg's configure runs `nm` on an ASAN-compiled test file, causing it to detect `__odr_asan_gen_` as `extern_prefix` and break the link step. ASAN flags are injected into `ffbuild/config.mak` after configure instead.
- **`--disable-x86asm`**: The `clang-asan` preset adds `-DPREFIX` to NASM flags, giving assembly symbols a leading `_` the C linker doesn't expect. The bugs are in C filter code so disabling assembly doesn't affect reproducibility.

### Reproduce

Run from `predicates/ffmpeg/lib/`:

```bash
ASAN_OPTIONS=halt_on_error=1 ./ffmpeg_g -y -i ../ffmpeg-466799d-1/input \
    -filter_complex blurdetect /tmp/out.mp4

ASAN_OPTIONS=halt_on_error=1 ./ffmpeg_g -y -i ../ffmpeg-466799d-2/input \
    -filter_complex afwtdn /tmp/out.mp4

ASAN_OPTIONS=halt_on_error=1 ./ffmpeg_g -y -i ../ffmpeg-466799d-3/input \
    -filter_complex colorcorrect /tmp/out.mp4

ASAN_OPTIONS=halt_on_error=1 ./ffmpeg_g -y -i ../ffmpeg-466799d-4/input \
    -filter_complex "transpose,gradfun" /tmp/out.mp4
```

Predicate 3 uses LeakSanitizer; `halt_on_error=1` ensures a non-zero exit in all cases.

### Quick oracle check

```bash
bash predicates/ffmpeg/ffmpeg-466799d-1/r.sh --input input
echo $?  # 0 = bug triggered, 1 = not triggered
```

### Minimize

```bash
scripts/minimize_ffmpeg predicates/ffmpeg/ffmpeg-466799d-1 \
    --algorithm ddmin --verbose
# minimized output → ffmpeg-466799d-1/input.min
```
