from math         import exp
from random       import random
from typing       import TypeVar
from core.oracle  import Oracle
from core.logging import RateLog


T = TypeVar("T")


def _confidence(mono:int) -> float:
	"""Compute the PMA confidence function."""

	return 1 / (1 + exp(-mono))


def _bits(pairs:list[tuple[int, T]]) -> int:
	"""Build an integer bitmap from a list of (index, item) pairs."""

	b = 0
	
	for idx, _ in pairs:
		b |= 1 << idx
	
	return b


def _skip_enabled(
	candidate:int,
	history  :list[tuple[int, bool]]) -> bool:

	"""Check whether a candidate is eligible to be skipped under monotonicity."""

	# skip if a previously executed superset was non-interesting
	return any((not interesting) and (candidate & prior) == candidate for prior, interesting in history)


def _mono_assr(
	candidate  :int,
	interesting:bool,
	history    :list[tuple[int, bool]]) -> bool | None:

	"""Assess monotonicity compliance of an executed candidate."""

	if not interesting: return None

	# ensure candidate is not a subset of any uninteresting priors
	return not any((not prior_interesting) and (candidate & prior) == candidate for prior, prior_interesting in history)


def _complement_sweep(
	target :list[tuple[int, T]],
	subsize:int,
	oracle :Oracle[T],
	M      :int,
	history:list[tuple[int, bool]],
	log    :RateLog | None = None) -> tuple[list[tuple[int, T]], int]:

	"""Identify benign chunks of target with PMA-guided skipping."""

	reduced = []
	tlen    = len(target)

	# test contiguous discrete subsets of size subsize
	for i in range(0, tlen, subsize):
		split     = i + subsize
		remaining = reduced + target[split:]
		candidate = _bits(remaining)

		# PMA-guided skip
		if _skip_enabled(candidate, history) and _confidence(M) > random(): interesting = False

		else:
			interesting = oracle([item for _, item in remaining])
			is_mono     = _mono_assr(candidate, interesting, history)

			if   is_mono is True:  M += 1
			elif is_mono is False: M -= 1

			history.append((candidate, interesting))

		if not interesting: reduced.extend(target[i:split])

		if log: log(len(reduced) + len(target[split:]), subsize, force=tlen - i <= subsize)

	return reduced, M


def minimize(
	target:list[T],
	oracle:Oracle[T],
	log   :RateLog | None = None) -> list[T]:

	"""PMA-enhanced Delta-Debugging algorithm over an ordered sequence."""

	minimized = list(enumerate(target))
	subsize   = max(1, len(target) // 2)

	# treat the input as an initially executed interesting test case
	history = [((1 << len(target)) - 1, True)]

	M = 0

	while subsize and minimized:
		minimized, M = _complement_sweep(
			
			target  = minimized,
			subsize = subsize,
			oracle  = oracle,
			M       = M,
			history = history,
			log     = log
		)

		subsize //= 2

	return [item for _, item in minimized]
