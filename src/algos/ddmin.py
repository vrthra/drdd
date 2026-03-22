from typing       import TypeVar
from core.oracle  import Oracle
from core.logging import RateLog


T = TypeVar("T")


def _complement_sweep(
	target :list[T],
	subsize:int,
	oracle :Oracle[T],
	log    :RateLog | None = None) -> list[T]:

	"""Identify benign chunks of target with variable granularity."""

	reduced = []
	tlen    = len(target)

	# test contiguous discrete subsets of size subsize
	for i in range(0, tlen, subsize):
		split = i + subsize

		# keep chunks whose removal would lose interesting-ness
		if not oracle(reduced + target[split:]): reduced.extend(target[i:split])
		
		if log: log(len(reduced) + len(target[split:]), subsize, force=tlen - i <= subsize)

	return reduced


def minimize(
	target:list[T],
	oracle:Oracle[T],
	log   :RateLog | None = None) -> list[T]:

	"""Delta-Debugging with halving complement sweep over an ordered sequence."""

	minimized = list(target)
	subsize   = max(1, len(target) // 2)

	while subsize and minimized:
		minimized = _complement_sweep(minimized, subsize, oracle, log)
		
		subsize //= 2

	return minimized
