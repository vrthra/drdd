import sys
import tomllib

from functools     import partial
from itertools     import product
from pathlib       import Path
from algos         import ALGORITHMS
from bench.harness import BenchTask, result_dir, run_all
from drivers.xml   import xml_minimizer


PROGRAM_DIR = Path(__file__).resolve().parent
VARIANTS    = (1, 2, 3)


def main():
	pred_root = PROGRAM_DIR.parents[1] / "predicates" / "xml"
	run_dir   = PROGRAM_DIR.parent / "runs" / result_dir("xml")

	cases   = sorted(c for c in pred_root.iterdir() if c.is_dir() and c.name.startswith("ticket-"))
	missing = [(c, v) for c, v in product(cases, VARIANTS) if not (c / "input.pick" / f"{v}.xml").exists()]

	if missing:
		for c, v in missing: print(f"  missing: {c.name}/input.pick/{v}.xml", file=sys.stderr)

		sys.exit(1)

	print(f"\nXML Benchmark\n")
	print(f"cases      : {len(cases) * len(VARIANTS)}")
	print(f"algorithms : {', '.join(ALGORITHMS)}")
	print(f"output     : {run_dir}\n")

	lib_dir = pred_root / "lib"
	
	configs = {}
	
	for case_dir in cases:
		config_path = case_dir / "config.toml"
		config      = tomllib.loads(config_path.read_text())
		
		for key in ("good_version", "bad_version"):
			if key not in config:
				print(f"  missing '{key}' in {config_path}", file=sys.stderr)
		
				sys.exit(1)
		
		configs[case_dir] = config

	tasks = [
		BenchTask(

			fn         = partial(xml_minimizer,

				input_path = case_dir / "input.pick" / f"{v}.xml",
				algorithm  = algorithm,
				query_path = case_dir / "query.xq",
				good_jar   = lib_dir / f"basex-{configs[case_dir]['good_version']}.jar",
				bad_jar    = lib_dir / f"basex-{configs[case_dir]['bad_version']}.jar",

			),
			input_path = case_dir / "input.pick" / f"{v}.xml",
			algorithm  = algorithm,
			label      = f"{case_dir.name}-{v}",

		)

		for case_dir, v, algorithm in product(cases, VARIANTS, ALGORITHMS)
	]

	run_all(tasks, run_dir)


if __name__ == "__main__":
	main()
