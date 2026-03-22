import sys

from datetime     import datetime
from typing       import TextIO
from core.oracle  import Oracle
from core.logging import RateLog
from utils.fmt    import fmt_bytes, progress_bar


class MinimizerLog(RateLog):
	"""Progress logger for a DD minimization run — writes to a stream."""

	def __init__(self, stream:TextIO=sys.stdout, interval:float=0.0) -> None:
		super().__init__(stream, interval)

		self._oracle:Oracle = None  # type: ignore[assignment]
		self._input_size    = 0


	def bind(self, input_size:int, oracle:Oracle) -> "MinimizerLog":
		"""Attach oracle state."""

		self._oracle     = oracle
		self._input_size = input_size

		return self


	def _log(self, size:int, subsize:int, edge:bool=False) -> None:
		"""In-place updates + timed log line commits."""
		
		pct   = 100 * (1 - size / self._input_size)
		col_w = len(fmt_bytes(self._input_size))

		line = (
		
			f"[{datetime.now().strftime('%H:%M:%S')}]  "
			f"{progress_bar(pct)}  {fmt_bytes(size):…>{col_w + 3}}  │  "
			f"k= {subsize:…>{col_w}}   #= {self._oracle.calls:…>6}"
		
		)

		self._emit(line, edge)