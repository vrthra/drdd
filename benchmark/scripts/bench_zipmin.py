import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import signal


PROGRAM_DIR = Path(__file__).resolve().parent


def sha256_hex(path:Path) -> str:
	with path.open("rb") as f:
		h = hashlib.sha256()
		
		for chunk in iter(lambda: f.read(1 << 20), b""):
			h.update(chunk)
	
	return h.hexdigest()
	

def file_size_bytes(path:Path) -> int:
	return path.stat().st_size


def parse_minimize_stdout(stdout:str) -> Tuple[Optional[int], Optional[int]]:
	"""
	Parse minimize_xml stdout for:

	- Minimized length: <bytes>
 	- Oracle invocations: <count>
	"""
	
	RE_MIN_LEN   = re.compile(r"^\s*-\s*Minimized length:\s*(\d+)\s*$")
	RE_ORA_CALLS = re.compile(r"^\s*-\s*Oracle invocations:\s*(\d+)\s*$")
	
	min_len      = None
	oracle_calls = None

	for line in stdout.splitlines():
		if min_len is None and (match := RE_MIN_LEN.search(line)): min_len = int(match.group(1))
		if oracle_calls is None and (match := RE_ORA_CALLS.search(line)): oracle_calls = int(match.group(1))
		if min_len is not None and oracle_calls is not None: break

	if not all([min_len, oracle_calls]): raise RuntimeError("Malformed output - could not parse minimized length / oracle calls")

	return min_len, oracle_calls


def parse_perf_stat_csv(path:Path) -> Dict[str, float]:
	"""Parse perf stat CSV and return a dict of normalized keys to numeric values."""

	def norm_key(s:str) -> str:
		s = s.lower()
		
		return (
			s.replace(" ", "_")
			 .replace("-", "_")
			 .replace("/", "_per_")
			 .strip("_")
		)

	metrics: Dict[str, float] = {}

	try: txt = path.read_text(encoding="utf-8", errors="replace")
	except Exception: return metrics

	reader = csv.reader(txt.splitlines())

	for row in reader:
		if not row or row[0].startswith("#"): continue

		value, unit, event, runtime, scale, metric, description = row

		if value: metrics[f"{norm_key(event)}{f'({unit})' if unit else ''}"] = float(value)
		if metric: metrics[norm_key(description)]                            = float(metric)

	return metrics


def run_one(
	case_dir:Path, 
	rel_input:Path, 
	module:str,
	result_dir:str) -> Dict[str, object]:
	
	"""Run one minimization via perf + wrapper and gather metrics."""
	
	# prepare perf file path unique per run
	perf_dir = PROGRAM_DIR.parent / "runs" / result_dir / "perf"
	perf_out = perf_dir / f"perf_{case_dir.name}_{rel_input.stem}_{module.replace(".", "-")}.out"
	perf_out.parent.mkdir(parents=True, exist_ok=True)

	# prepare out file path per run
	min_dir = PROGRAM_DIR.parent / "runs" / result_dir / "minimized"
	min_out = min_dir / f"{case_dir.name}_{rel_input.stem}.min-{module.replace(".", "-")}.xml"
	min_out.parent.mkdir(parents=True, exist_ok=True)

	# prepare log file path per run
	log_dir    = PROGRAM_DIR.parent / "runs" / result_dir / "logs"
	log_stem   = f"{case_dir.name}_{rel_input.stem}_{module.replace(".", "-")}"
	stdout_out = log_dir / f"{log_stem}.stdout"
	stderr_out = log_dir / f"{log_stem}.stderr"
	stdout_out.parent.mkdir(parents=True, exist_ok=True)

	# build command
	scripts_dir = PROGRAM_DIR.parents[1] / "scripts"

	cmd = [str(scripts_dir / "basexserver_wrapper"), "--verbose", "--"]
	cmd += ["perf", "stat", "-x", ",", "-o", str(perf_out)]
	cmd += [
		str(scripts_dir / "minimize_xml"),
		"--module", module,
		"--ramdisk",
		"--verbose",
		str(case_dir),
		"--input", str(rel_input),
		"--output", str(min_out)
	]

	# stable number formatting for perf output
	env = os.environ.copy()
	env.setdefault("LC_ALL", "C")

	# force unbuffered Python for any Python children
	env["PYTHONUNBUFFERED"] = "1"

	stdout_buf = []
	stderr_buf = []

	# run test
	with stdout_out.open("w", encoding="utf-8") as f_out, \
		 stderr_out.open("w", encoding="utf-8") as f_err:
		 
		start_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
		
		proc = subprocess.Popen(
			cmd,
			stdout            = f_out,
			stderr            = f_err,
			env               = env,
			start_new_session = True
		)

		try: proc.wait()
		
		# send keyboard interrupt to child
		except KeyboardInterrupt:

			# ask child subprocess to stop
			try: os.killpg(proc.pid, signal.SIGINT)
			except ProcessLookupError: pass
			
			# escalate if timeout expired
			try: proc.wait(timeout=10)
			except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL)
			
			raise

		stdout = stdout_out.read_text(encoding="utf-8", errors="replace")
		stderr = stderr_out.read_text(encoding="utf-8", errors="replace")
		
		min_len, oracle_calls = parse_minimize_stdout(stdout)

		end_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

	# program outputs
	stdout = "".join(stdout_buf)
	stderr = "".join(stderr_buf)
	retcode = proc.returncode

	min_len, oracle_calls = parse_minimize_stdout(stdout)

	# metrics
	input_bytes = file_size_bytes(case_dir / rel_input)
	input_sha   = sha256_hex(case_dir / rel_input) if input_bytes >= 0 else ""

	output_bytes = file_size_bytes(min_out)
	output_sha   = sha256_hex(min_out)

	reduction_bytes = input_bytes - output_bytes if (input_bytes >= 0 and output_bytes >= 0) else ""
	reduction_ratio = (output_bytes / input_bytes) if (input_bytes > 0 and output_bytes >= 0) else ""

	perf = parse_perf_stat_csv(perf_out)

	row: Dict[str, object] = {
		"timestamp_start":    start_ts,
		"timestamp_end":      end_ts,
		"predicate":          case_dir.name,
		"variant":            rel_input.stem,
		"algorithm":          module,
		"return_code":        retcode,
		"minimized_length":   min_len,
		"oracle_invocations": oracle_calls,
		"input_bytes":        input_bytes,
		"input_sha256":       input_sha,
		"output_bytes":       output_bytes if output_bytes >= 0 else "",
		"output_sha256":      output_sha,
		"reduction_bytes":    reduction_bytes,
		"reduction_ratio":    reduction_ratio,
	}

	# merge perf metrics (prefix with "perf_")
	for k, v in perf.items():
		row[f"perf_{k}"] = v

	# optional troubleshooting logs (not used for CSV parsing)
	if retcode != 0:
		row["error"] = f"rc={retcode}"

	return row


def main():
	# result directory
	timestamp  = datetime.datetime.now().strftime("%d-%m-%Y_%H:%M")
	commit     = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
	result_dir = f"{timestamp}_git-{commit}"

	p = argparse.ArgumentParser(description=__doc__)
	
	p.add_argument(
		"--pred-root",
		default=str(PROGRAM_DIR.parents[1] / "predicates" / "xmlprocessor"),
		help="Path to predicates/xmlprocessor root"
	)
	
	p.add_argument(
		"--variants",
		default="1,2,3,4,5",
		help="Comma-separated variant indices (default: 1..5)"
	)
	
	p.add_argument(
		"--output", 
		default=str(PROGRAM_DIR.parent / "runs" / result_dir / "result.csv"), 
		help="Output CSV path"
	)

	args = p.parse_args()

	pred_root = Path(args.pred_root).resolve()
	out_csv   = Path(args.output)
	out_csv.parent.mkdir(parents=True, exist_ok=True)

	try: variant_ids = [int(x) for x in args.variants.split(",") if x]
	except ValueError: p.error("--variants must be comma-separated integers")

	cases = [c for c in pred_root.iterdir() if c.is_dir() and c.name.startswith("xml-")]

	print(f"""Benchmark: ZipMin vs. DDMin

Running dd.zipmin vs. dd.ddmin on {len(cases)} XML test cases of 
varying sizes. Using perf for additional profiling (note: run sudo 
sysctl -w kernel.perf_event_paranoid=0 for profiling CPU events).

Command: basexserver_wrapper --verbose -- perf stat -x , -o <path> minimize_xml --module <variant> --verbose --ramdisk <case_dir> --input <path> --output <path>
 
Test Cases: {"".join([f"\n - {case}" for case in cases])}

Outputs:
 - Benchmarking results: {out_csv}
 
See output parent dir for artefacts.

--- starting tests:\n""")

	# create task list in deterministic order
	tasks = []

	for case_dir in cases:
		for v in variant_ids:
			rel_input = Path("input.pick") / f"{v}.xml"

			if not (case_dir / rel_input).exists():
				print(f"Skipping missing variant: {case_dir / rel_input}", file=sys.stderr)
				continue

			for module in ("dd.ddmin", "dd.zipmin"):
				tasks.append((case_dir, rel_input, module))

	# run tasks in parallel according to --jobs
	rows = [None] * len(tasks)
	
	if not tasks: 
		print("No test candidates.")
		return
	
	for i, (case_dir, rel_input, module) in enumerate(tasks):
		print(f"[{datetime.datetime.now().strftime("%H:%M:%S")}] (start | id:{i}) {module}\t...\t{case_dir.name}/{rel_input}")

		try: rows[i] = run_one(case_dir, rel_input, module, result_dir)

		except Exception as e:
			rows[i] = {
				"timestamp_start": "",
				"timestamp_end":   "",
				"predicate":       case_dir.name,
				"variant":         rel_input.stem,
				"algorithm":       module,
				"return_code":     -1,
				"error":           f"exception: {e}"
			}

			print(f"[{datetime.datetime.now().strftime("%H:%M:%S")}]  (fail | id:{i}) exception: {e}")

	# build fieldnames in deterministic order: first by first appearance across rows
	fieldnames = []
	
	for row in rows:
		if not row:	continue
		
		for k in row.keys():
			if k not in fieldnames:	fieldnames.append(k)

	# write rows to csv
	with out_csv.open("w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=fieldnames)
		
		writer.writeheader()
		
		for r in rows:
			if r is None: continue
			
			writer.writerow(r)


if __name__ == "__main__":
	main()
