from math         import ceil
from typing       import TypeVar
from core.oracle  import Oracle
from core.logging import RateLog


T = TypeVar("T")


def _remove_last(
	target :list[T],
	postfix:list[T],
	oracle :Oracle[T]) -> tuple[list[T], list[T]]:

	"""Move the last target element to the postfix if required."""

	prefix = target[:-1]

	if oracle(prefix + postfix): return prefix, postfix
	else:                        return prefix, [target[-1]] + postfix


def _complement_sweep(
	target :list[T],
	postfix:list[T],
	subsize:int,
	oracle :Oracle[T],
	log    :RateLog | None = None) -> list[T]:

	"""Identify benign chunks of target with variable granularity."""

	reduced = []
	tlen    = len(target)
	plen    = len(postfix)

	# test contiguous discrete subsets of size subsize
	for i in range(0, tlen, subsize):
		split = i + subsize

		# keep chunks whose removal would lose interesting-ness
		if not oracle(reduced + target[split:] + postfix): reduced.extend(target[i:split])

		if log: log(len(reduced) + len(target[split:]) + plen, subsize, force=tlen - i <= subsize)

	return reduced


def minimize(
	target:list[T],
	oracle:Oracle[T],
	log   :RateLog | None = None) -> list[T]:

	"""TicTocMin Delta-Debugging algorithm."""

	minimized = list(target)
	subsize   = max(1, len(target) // 2)
	postfix   = []
	
	sweep_step = True

	while subsize and minimized:

		# alternate between complement sweep...
		if sweep_step:
			prev_size = len(minimized)
			minimized = _complement_sweep(minimized, postfix, subsize, oracle, log)
			deficit   = max(ceil(prev_size / subsize) - (prev_size - len(minimized)), 0)

			subsize //= 2

		# ...and deficit-guided zipping
		else:
			for _ in range(deficit):
				minimized, postfix = _remove_last(minimized, postfix, oracle)

			if log: log(len(minimized) + len(postfix), subsize)

		sweep_step = not sweep_step

	return minimized + postfix
