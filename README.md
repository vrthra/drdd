# Delta Debugging Benchmark Suite

> Implementations and benchmarks of five Delta Debugging algorithms against real-world bug-reproducing predicates.

Delta Debugging isolates the minimal input that causes a program to fail. This repo implements five algorithms — from the classical baseline to probabilistic and monotonicity-aware variants — and benchmarks them against two families of real-world predicates: XML query discrepancy bugs and FFmpeg memory-safety crashes.

## Algorithms

| Module | Algorithm | Strategy |
|--------|-----------|----------|
| `dd.ddmin` | **DDMin** | Classical binary search over subsets |
| `dd.cdd` | **CDD** | Adaptive subset sizing with probabilistic decay |
| `dd.probdd` | **ProbDD** | Per-element removal probabilities, updated on failure |
| `dd.pmadd` | **PmaDD** | Monotonicity-aware skipping via confidence scoring |
| `dd.ttmin` | **TTMin** | Alternating prefix-zip and complement sweep |

All algorithms share the same interface: `minimize(target, oracle, ...)` operates on any ordered sequence and accepts any callable predicate.

## Predicates

| Family | Cases | Bug type |
|--------|-------|----------|
| [`predicates/xml/`](predicates/xml/) | 5 × 5 variants | XQuery output discrepancy between BaseX versions |
| [`predicates/ffmpeg/`](predicates/ffmpeg/) | 13 cases | ASAN heap-buffer-overflow / LeakSanitizer |

## Setup

Requires **Python 3.11+**. Java 11+ and `nc` are additionally needed for XML predicates.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Verify:

```bash
python -c "import algos; print(algos.ALGORITHMS)"
# ('cdd', 'ddmin', 'pmadd', 'probdd', 'ttmin')
```

## Quick Start

**Minimize an XML file** (starts a BaseX server pair internally):

```bash
python scripts/minimize_xml predicates/xml/ticket-1e9bc83-1 \
    --input input.pick/1.xml --algorithm ttmin --verbose
```

**Minimize an FFmpeg input** (no server needed):

```bash
python scripts/minimize_ffmpeg predicates/ffmpeg/ticket-10699 \
    --algorithm pmadd --verbose
```

**Use an algorithm directly:**

```python
from algos.ddmin import minimize

result = minimize(
    target = list("aaaaabaaaa"),
    oracle = lambda s: "b" in "".join(s),
)

print("".join(result))  # "b"
```

## Repository Layout

| Path | Description |
|------|-------------|
| `src/algos/` | Minimization algorithms (`ddmin`, `cdd`, `probdd`, `pmadd`, `ttmin`) |
| `src/bench/` | Benchmark harness and minimizer wrapper |
| `src/core/` | Oracle base class and logging |
| `src/drivers/` | FFmpeg, XML (saxonche), and BaseX drivers |
| `src/utils/` | Text formatting utilities |
| `scripts/` | `minimize_xml`, `minimize_ffmpeg`, `cherrypick_xml` |
| `predicates/xml/` | XML query discrepancy bugs — 5 cases × 5 variants |
| `predicates/ffmpeg/` | FFmpeg ASAN bugs — 13 cases |
| `benchmark/` | `bench_xml.py`, `bench_ffmpeg.py`, result runs |
| `tests/` | Sanity tests |

## Benchmarking

```bash
python benchmark/scripts/bench_xml.py      # XML: all 5 algorithms × 25 inputs
python benchmark/scripts/bench_ffmpeg.py   # FFmpeg: all 5 algorithms × 4 inputs
```

Results are written to `benchmark/runs/<label>_<date>_git-<sha>/result_*.csv`.

## Tests

```bash
python -m unittest -v
```
