from typing import Callable
from math import ceil
from datetime import datetime


def complement_sweep(target:str, partlen:int, oracle:Callable) -> str:
	"""
	Identify benign chunks of target with variable granularity.

	:param target: input string.
	:param partlen: partition length.
	:param oracle: oracle function.
	:returns: reduced string.
	"""

	reduced = ""
	
	# test contiguous discrete chunks of size partlen for interestingness
	for i in range(0, len(target), partlen):
		split     = i + partlen
		removed   = target[i:split]
		remaining = target[split:]
		
		interesting = oracle(reduced + remaining)
		
		if not interesting: reduced += removed
	
	return reduced


def minimize(
	target:str, 
	oracle:Callable, 
	stats:bool  =False, 
	verbose:bool=False) -> tuple[str, int, int] | str:
	
	"""
	Classical Delta-Debugging algorithm.
	
	:param target: input string.
	:param oracle: oracle function.
	:param stats: data collection flag.
	:param verbose: verbose output flag.
	:returns: reduced string and optional stats.
	"""

	# count total oracle calls
	n_total_oracalls = 0

	# partition size
	partlen = len(target) // 2

	while partlen and target:
		if verbose: print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(target):.2E}\t...\t{partlen}")

		reduced = complement_sweep(target, partlen, oracle)
		
		if stats: n_total_oracalls += ceil(len(target) / partlen)

		# reduce partition size if no update 
		if reduced == target: partlen //= 2		
		
		target = reduced
	
	return (target, n_total_oracalls) if stats else target
