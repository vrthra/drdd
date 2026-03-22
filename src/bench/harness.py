"""Generic benchmark harness for DD minimizer benchmarks."""

import csv
import hashlib
import subprocess
import time

from datetime        import datetime, timezone, timedelta
from dataclasses     import dataclass
from pathlib         import Path
from typing          import Callable
from drivers.logging import MinimizerLog
from bench.logging   import HarnessLog
from utils.fmt       import fmt_bytes


@dataclass
class BenchTask:
	fn        :Callable[..., dict]
	input_path:Path
	predicate :str
	algorithm :str
	label     :str


def _sha256_hex(path:Path) -> str:
	"""Compute hash of file contents."""

	try:    return hashlib.sha256(path.read_bytes()).hexdigest()
	except FileNotFoundError: return ""


def _file_size_bytes(path:Path) -> int:
	"""Compute file size in bytes."""

	try: return path.stat().st_size
	except FileNotFoundError: return -1


def _run_one(task:BenchTask, log:HarnessLog) -> dict:
	"""Run one minimization and gather metrics."""

	ts_start   = datetime.now(timezone.utc)
	start_perf = time.perf_counter()

	result = None

	try: result = task.fn(log=log)

	except KeyboardInterrupt: result = { "error": "interrupted" }

	except Exception as e: result = { "error": str(e) }

	finally: end_perf = time.perf_counter()

	wall_time = end_perf - start_perf
	ts_end    = ts_start + timedelta(seconds=wall_time)

	row = {
		
		"ts_start"          : ts_start.isoformat(),
		"ts_end"            : ts_end.isoformat(),
		"predicate"         : task.predicate,
		"input_bytes"       : _file_size_bytes(task.input_path),
		"input_sha256"      : _sha256_hex(task.input_path),
		"algorithm"         : task.algorithm,
		"minimized_length"  : (result or {}).get("minimized_length", ""),
		"oracle_invocations": (result or {}).get("oracle_invocations", "")
	
	}

	if result and result.get("error"): row["error"] = result["error"]

	return row


def _write_csv(rows:list[dict], out_csv:Path) -> None:
	"""Write a list of rows to an output CSV."""

	out_csv.parent.mkdir(parents=True, exist_ok=True)

	fieldnames = []

	for row in rows:
		for k in row.keys():
			if k not in fieldnames: fieldnames.append(k)

	with out_csv.open("w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=fieldnames)

		writer.writeheader()

		for r in rows:
			writer.writerow(r)


def result_dir(label: str) -> str:
	"""Construct result directory name."""

	ts     = datetime.now().strftime("%d-%m-%Y_%H:%M")
	commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()

	return f"{label}_{ts}_git-{commit}"


def run_all(tasks:list[BenchTask], run_dir:Path) -> None:
	"""Run a series of benchmark tasks."""

	if not tasks:
		print("No tasks to run.")
		
		return

	n_tasks = len(tasks)
	out_csv = run_dir / "result.csv"
	log_dir = run_dir / "logs"
	algo_w  = max(len(t.algorithm) for t in tasks)

	run_dir.mkdir(parents=True, exist_ok=True)
	log_dir.mkdir(parents=True, exist_ok=True)

	rows      = []
	interrupt = False

	try:
		for i, task in enumerate(tasks):
			input_bytes = _file_size_bytes(task.input_path)
			counter_str = f"{i + 1:>{len(str(n_tasks))}}/{n_tasks}"
			size_str    = fmt_bytes(input_bytes)

			log_path = log_dir / f"{i:04d}_{task.predicate}_{task.algorithm}.log"

			with log_path.open("w", encoding="utf-8", buffering=1) as lf:
				ts_start = datetime.now(timezone.utc)

				lf.write(f"predicate  : {task.predicate}\n")
				lf.write(f"algorithm  : {task.algorithm}\n")
				lf.write(f"input_size : {input_bytes} B\n")
				lf.write(f"started    : {ts_start.isoformat()}\n\n")

				log = HarnessLog(

					file_log    = MinimizerLog(stream=lf, interval=5.0),
					counter_str = counter_str,
					algo        = task.algorithm,
					algo_w      = algo_w,
					label       = task.label,
					size_str    = size_str,

				)

				rows.append(_run_one(task, log))
				
				row     = rows[-1]
				elapsed = (datetime.fromisoformat(row["ts_end"]) - datetime.fromisoformat(row["ts_start"])).total_seconds()

				log.finalize(row)

				if row.get("error"): lf.write(f"\n\n{row['error'].upper()}\n")

				lf.write(f"\nminimized : {row.get('minimized_length', 'N/A')} B\n")
				lf.write(f"oracle    : {row.get('oracle_invocations', 'N/A')} invocations\n")
				lf.write(f"elapsed   : {elapsed:.1f}s\n")

				if row.get("error") == "interrupted":
					interrupt = True
					
					break

	except KeyboardInterrupt: interrupt = True

	errs = sum(1 for r in rows if r.get("error"))

	if interrupt: print(f"\nInterrupted after {len(rows)} task(s) ({errs} failed).\n")
	else:         print(f"\nCompleted {n_tasks} task(s) ({errs} failed).\n")

	if rows: _write_csv(rows, out_csv)
