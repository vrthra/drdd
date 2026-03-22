from random       import shuffle
from typing       import TypeVar
from core.oracle  import Oracle
from core.logging import RateLog


T = TypeVar("T")


def _sort_indices(probs:list[float]) -> list[int]:
	"""Sort active elements by probability in ascending order."""

	groups = {}

	for idx, prob in enumerate(probs):
		
		# elements with probability 1 are no longer removable and skipped
		if prob >= 1.0: continue

		groups.setdefault(prob, []).append(idx)

	order = []

	# elements within a group (same probability) are shuffled
	for _, group in sorted(groups.items()):
		shuffle(group)
		order.extend(group)

	return order


def _compute_size(order:list[int], probs:list[float]) -> int:
	"""Compute the number of elements to remove in the next attempt."""

	best_gain = -1.0
	best_size = 0
	p_pass    = 1.0

	for size, idx in enumerate(order, start=1):
		p_pass *= 1 - probs[idx]
		gain    = size * p_pass

		# keep extending until expected gain starts decreasing
		if gain >= best_gain: best_gain, best_size = gain, size
		
		else: break

	return best_size


def _update_fail_probs(indices:list[int], probs:list[float]) -> None:
	"""Update probabilities after a failed deletion attempt."""

	p_fail = 1.0

	for idx in indices:
		p_fail *= 1 - probs[idx]

	for idx in indices:
		probs[idx] = min(probs[idx] / (1 - p_fail), 1.0)

		# clamp numerical noise from singleton updates to exact 1
		if probs[idx] > 1 - 1e-12: probs[idx] = 1.0


def minimize(
	target:list[T],
	oracle:Oracle[T],
	p_0   :float          = 0.1,
	log   :RateLog | None = None) -> list[T]:

	"""Probabilistic Delta-Debugging algorithm over an ordered sequence."""

	minimized = list(target)
	probs     = [p_0] * len(minimized)

	while True:
		order = _sort_indices(probs)

		# terminate when every remaining element has probability 1
		if not minimized or not order: break

		subsize   = _compute_size(order, probs)
		subset    = order[:subsize]
		marked    = set(subset)
		candidate = [item for i, item in enumerate(minimized) if i not in marked]

		# remove the attempted subset if it is removable
		if oracle(candidate):
			minimized = candidate
			probs     = [prob for i, prob in enumerate(probs) if i not in marked]

		# otherwise update probabilities of the attempted subset
		else: _update_fail_probs(subset, probs)

		if log: log(len(minimized), subsize)

	return minimized
