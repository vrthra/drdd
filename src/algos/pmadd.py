from math         import exp
from random       import random
from typing       import TypeVar
from core.oracle  import Oracle
from core.logging import RateLog


T = TypeVar("T")


def _confidence(mono:int) -> float:
	"""Compute the PMA confidence function."""

	# clamp exponent to prevent overflow
	return 1 / (1 + exp(-max(-709, min(709, mono))))


def _bits(pairs:list[tuple[int, T]]) -> int:
	"""Build an integer bitmap from a list of (index, item) pairs."""

	b = 0
	
	for idx, _ in pairs:
		b |= 1 << idx
	
	return b


def _check_dominated(candidate:int, history:list[int]) -> bool:
	"""Check whether a candidate is eligible to be skipped under monotonicity."""

	return any((candidate & prior) == candidate for prior in history)


def _history_insert(candidate:int, history:list[int]) -> None:
	"""Insert a non-interesting bitmask into the antichain history."""

	# prune entries now dominated by the new one (prior ⊆ candidate)
	history[:] = [p for p in history if (p & candidate) != p]
	
	history.append(candidate)


def _complement_sweep(
	target :list[tuple[int, T]],
	subsize:int,
	oracle :Oracle[T],
	M      :int,
	history:list[int],
	log    :RateLog | None = None) -> tuple[list[tuple[int, T]], int]:

	"""Identify benign chunks of target with PMA-guided skipping."""

	reduced      = []
	tlen         = len(target)
	target_bits  = _bits(target)
	removed_bits = 0

	# test contiguous discrete subsets of size subsize
	for i in range(0, tlen, subsize):
		split = i + subsize

		subset_bits    = _bits(target[i:split])
		candidate_bits = target_bits & ~(subset_bits | removed_bits)
		skip_eligible  = _check_dominated(candidate_bits, history)

		# PMA-guided skip
		if skip_eligible and _confidence(M) > random(): interesting = False

		else:
			interesting = oracle([delta for _, delta in reduced + target[split:]])			
			
			# monotonicity assessment
			if interesting:

				# interesting subset of non-interesting prior = violation
				if skip_eligible: M -= 1
				else:             M += 1

			# skip_eligible = false guarantees entry is not redundant
			if not (interesting or skip_eligible): _history_insert(candidate_bits, history)

		if interesting:	removed_bits |= subset_bits
		else:           reduced.extend(target[i:split])

		if log: log(len(reduced) + len(target[split:]), subsize, force=tlen - i <= subsize)

	return reduced, M


def minimize(
	target:list[T],
	oracle:Oracle[T],
	log   :RateLog | None = None) -> list[T]:

	"""PMA-enhanced Delta-Debugging algorithm over an ordered sequence."""

	minimized = list(enumerate(target))
	subsize   = max(1, len(target) // 2)

	history = []

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

	return [delta for _, delta in minimized]
