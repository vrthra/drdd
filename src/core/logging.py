import sys
import time

from typing import TextIO


class Log:
	"""Base logger."""

	def __init__(self, stream:TextIO=sys.stdout) -> None:
		self._stream = stream
		self._istty  = getattr(self._stream, "isatty", lambda: False)()


	def __call__(self, *args, **kwargs) -> None: ...


	def _emit(self, line:str, commit:bool=True) -> None:
		"""Write optionally transient log line."""

		# skip if log stream is not a TTY
		if not commit and not self._istty: return

		prefix = "\r" if self._istty else ""

		print(f"{prefix}{line}",

			end   = "\n" if commit else "",
			file  = self._stream,
			flush = True

		)


class RateLog(Log):
	"""Logger with time-based rate-limiting."""

	def __init__(self, stream:TextIO=sys.stdout, interval:float=0.0) -> None:
		super().__init__(stream)
		
		self._interval = interval
		self._last_log = time.perf_counter()


	def __call__(self, *args, force:bool=False) -> None:
		"""Real-time rate limited logging."""

		now  = time.perf_counter()
		edge = force or now - self._last_log >= self._interval

		self._log(*args, edge=edge)

		if edge: self._last_log = now


	def _log(self, *args, edge:bool=False): ...