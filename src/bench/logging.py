"""Live terminal logger for benchmark tasks."""

import time

from datetime        import datetime
from core.oracle     import Oracle
from core.logging    import Log
from drivers.logging import MinimizerLog
from utils.fmt       import fmt_bytes, fmt_time, progress_bar, terminal_width, labelled_rule


_SIZE_W  = 9
_CALLS_W = 6

_LINE_W  = _SIZE_W + _CALLS_W + 18


class HarnessLog(Log):
	"""Live terminal logger for a single benchmark task."""

	def __init__(self,
		file_log   :MinimizerLog,
		counter_str:str,
		algo       :str,
		algo_w     :int,
		label      :str,
		size_str   :str) -> None:

		super().__init__()

		self._file_log      = file_log
		self._left          = f"{counter_str}  │  {algo:<{algo_w}} -> {label}  │"
		self._input_size    = 0
		self._oracle:Oracle = None                                 # type: ignore[assignment]
		self._t0            = time.perf_counter()
		self._ts_start      = datetime.now().strftime("%H:%M:%S")

		placeholder = f"{size_str}  starting..."

		self._line(f"{placeholder:<{_LINE_W}}", "00:00")


	def _line(self, content:str, ts:str, commit:bool=False) -> None:
		"""Overwrite the current terminal line with a status update."""

		self._emit(f"{self._left}  {content}  │  {ts}".ljust(terminal_width()), commit=commit)


	def bind(self, input_size:int, oracle:Oracle) -> "HarnessLog":
		"""Attach oracle state."""
		
		self._input_size = input_size
		self._oracle     = oracle
		
		self._file_log.bind(input_size, oracle)
		
		return self


	def __call__(self, size:int, subsize:int, force:bool=False) -> None:
		self._file_log(size, subsize, force=force)

		pct = 100.0 * (1.0 - size / self._input_size)
		ts  = fmt_time(time.perf_counter() - self._t0)

		self._line(f"{progress_bar(pct)} [{pct:…>5.1f}%]  {str(self._oracle.calls):…>{_CALLS_W}} calls", ts)


	def finalize(self, row:dict) -> None:
		"""Commit test result row."""
		
		ts_end = datetime.now().strftime("%H:%M:%S")
		ts     = f"{self._ts_start}-{ts_end}"

		# valid result row
		if isinstance(row.get("minimized_length"), int):
			length    = row["minimized_length"]
			calls     = row.get("oracle_invocations", "")
			reduction = 100.0 * (1.0 - length / (self._input_size or 1))

			self._line(f"{fmt_bytes(length):…>{_SIZE_W}}   {reduction:5.1f}%   {str(calls):…>{_CALLS_W}} calls", ts, commit=True)

		# error row
		elif row.get("error"): self._line(labelled_rule(_LINE_W, "FAILED"), ts, commit=True)

		# undetermined result
		else: self._line("-  (no result)", ts, commit=True)
