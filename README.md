# ZipMin Delta Debugger (DD) Benchmarking

Repository containing benchamrking tools for improved Delta Debugging algorithms (ZipMin) and pipelines.

## Setup (Editable Install)

Install the project in editable mode so changes under `src/` are picked up without reinstalling.

### Prerequisites

- Python 3.8+
- `pip` and `venv`
- Java 11+ (required by the BaseX/Saxon utilities used in the benchmarking scripts)

### Steps

1. Create and activate a virtual environment

   ```Bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Upgrade build tools (optional but recommended)

   ```Bash
   python -m pip install -U pip setuptools wheel
   ```

3. Install this repo in editable mode (src-layout)

   ```Bash
   python -m pip install -e .
   ```

### Verify

- `python -c "import dd, inspect; print(dd.__file__)"` should print a path inside `src/dd`.

- Run tests: `PYTHONPATH=src python -m unittest -v` or use any provided scripts under `scripts/`.

### Notes

- The package discovery is configured for a `src/` layout via `pyproject.toml`, so editable installs work out-of-the-box.

- Re-run `pip install -e .` only when you change packaging metadata (dependencies, entry points) in `pyproject.toml`.
