from typing       import TypeVar
from core.oracle  import Oracle
from core.logging import RateLog


T = TypeVar("T")


def _complement_sweep(
	target     :list[T],
	granularity:int,
	oracle     :Oracle[T],
	log        :RateLog | None = None) -> tuple[int, list[T]]:

	"""Identify benign chunks of target with variable granularity."""

	# range error guard
	if len(target) < 2: return granularity, target

	reduced = []
	tlen    = len(target)
	subsize = tlen // granularity

	for i in range(0, tlen, subsize):
		split      = i + subsize
		complement = reduced + target[split:]

		if log: log(len(complement), subsize, force=tlen - i <= subsize)

		# causal restart
		if oracle(complement): return _complement_sweep(complement, max(granularity - 1, 2), oracle, log)
			
		reduced.extend(target[i:split])

	return granularity, reduced


def minimize(
	target:list[T],
	oracle:Oracle[T],
	log   :RateLog | None = None) -> list[T]:

	"""Classical Delta-Debugging as presented in the DebuggingBook."""

	minimized   = list(target)
	granularity = 2

	while True:
		granularity, minimized = _complement_sweep(minimized, granularity, oracle, log)
		
		if granularity == len(minimized): break

		granularity = min(granularity * 2, len(minimized))

	return minimized
