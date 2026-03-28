import os
import subprocess
import tempfile

from importlib       import import_module
from pathlib         import Path
from algos           import ALGORITHMS
from core.oracle     import Oracle
from drivers.logging import MinimizerLog


_SHM      = shm if (shm := Path("/dev/shm")).is_dir() else None
_ASAN_ENV = { **os.environ, "ASAN_OPTIONS": "halt_on_error=1" }


class FFmpegOracle(Oracle[int]):
	"""Oracle that runs an ASAN-instrumented ffmpeg binary."""

	def __init__(self, ffmpeg_path:Path, filter_expr:str, target:str=".mp4") -> None:

		super().__init__()

		self._ffmpeg_path   = ffmpeg_path
		self._filter_expr   = filter_expr
		self._target        = target
		self._tmp_path:Path = None         # type: ignore[assignment]
		self._out_path:Path = None         # type: ignore[assignment]
		self._cmd:list[str] = None         # type: ignore[assignment]


	def __enter__(self) -> "FFmpegOracle":
		"""Create tempfile context for oracle."""

		# create input tempfile for oracle 
		fd, tmp = tempfile.mkstemp(dir=_SHM, prefix="dd_")
		os.close(fd)

		# create output tempfile with extension for target
		fd, out = tempfile.mkstemp(dir=_SHM, prefix="dd_out_", suffix=self._target)
		os.close(fd)
		
		self._tmp_path = Path(tmp)
		self._out_path = Path(out)

		self._cmd = [

			str(self._ffmpeg_path), 
			
			"-nostdin", 
			"-y",
			"-i",                      str(self._tmp_path),
			"-threads",                "1", 
			"-filter_complex_threads", "1",
			"-filter_complex",         self._filter_expr,
			
			str(self._out_path),

		]

		return self


	def _call(self, candidate) -> bool:
		self._tmp_path.write_bytes(bytes(candidate))

		try:
			proc = subprocess.run(self._cmd,

				stdout  = subprocess.DEVNULL,
				stderr  = subprocess.PIPE,
				env     = _ASAN_ENV,
				timeout = 30,

			)
		
		except subprocess.TimeoutExpired: return False

		return b"Sanitizer" in proc.stderr


	def __exit__(self, *_) -> None:
		"""Clean up temporary resources."""

		self._tmp_path.unlink(missing_ok=True)
		self._out_path.unlink(missing_ok=True)


def ffmpeg_minimizer(
	input_path :Path,
	algorithm  :str,
	ffmpeg_path:Path,
	filter_expr:str,
	target     :str                 = ".mp4",
	output_path:Path | None         = None,
	log        :MinimizerLog | None = None) -> dict:

	"""Run a DD minimization over an FFmpeg ASAN oracle."""

	if algorithm not in ALGORITHMS: raise ValueError(f"Unknown algorithm '{algorithm}'. Available: {', '.join(ALGORITHMS)}")

	original = input_path.read_bytes()
	minimize = getattr(import_module(f"algos.{algorithm}"), "minimize")

	oracle = FFmpegOracle(

		ffmpeg_path = ffmpeg_path,
		filter_expr = filter_expr,
		target      = target,

	)

	if log: log.bind(len(original), oracle)

	with oracle:
		minimized = minimize(
			target = original,
			oracle = oracle,
			log    = log,
		)

	if output_path: output_path.write_bytes(bytes(minimized))

	return {
		"minimized_length"  : len(minimized),
		"oracle_invocations": oracle.calls,
	}
