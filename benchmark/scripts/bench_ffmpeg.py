import sys
import tomllib

from functools      import partial
from itertools      import product
from pathlib        import Path
from algos          import ALGORITHMS
from bench.harness  import BenchTask, result_dir, run_all
from drivers.ffmpeg import ffmpeg_minimizer


PROGRAM_DIR = Path(__file__).resolve().parent


def main():
	pred_root = PROGRAM_DIR.parents[1] / "predicates" / "ffmpeg"
	run_dir   = PROGRAM_DIR.parent / "runs" / result_dir("ffmpeg")

	cases   = sorted(c for c in pred_root.iterdir() if c.is_dir() and c.name.startswith("ticket-"))
	missing = [c for c in cases if not (c / "input").exists()]

	if missing:
		for c in missing: print(f"  missing: {c.name}/input", file=sys.stderr)
		
		sys.exit(1)

	print(f"\nFFmpeg Benchmark\n")
	print(f"cases      : {len(cases)}")
	print(f"algorithms : {', '.join(ALGORITHMS)}")
	print(f"output     : {run_dir}\n")

	configs = {}
	
	for case_dir in cases:
		config_path = case_dir / "config.toml"
		config      = tomllib.loads(config_path.read_text())
	
		for key in ("commit", "filter", "target"):
			if key not in config:
				print(f"  missing '{key}' in {config_path}", file=sys.stderr)
				
				sys.exit(1)
		
		configs[case_dir] = config

	tasks = [
		BenchTask(

			fn         = partial(ffmpeg_minimizer,

				input_path  = case_dir / "input",
				algorithm   = algorithm,
				ffmpeg_path = pred_root / "lib" / f"ffmpeg_g-{configs[case_dir]['commit']}",
				filter_expr = configs[case_dir]["filter"],
				target      = configs[case_dir]["target"],

			),
			input_path = case_dir / "input",
			predicate  = case_dir.name,
			algorithm  = algorithm,
			label      = case_dir.name,

		)

		for case_dir, algorithm in product(cases, ALGORITHMS)
	]

	run_all(tasks, run_dir)


if __name__ == "__main__":
	main()
