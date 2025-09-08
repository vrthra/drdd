from typing import Callable
from math import ceil
from datetime import datetime


def remove_last_char(
	pre:str, 
	target:str, 
	post:str, 
	oracle:Callable) -> tuple[str, str, str]:
	
	"""
	Zipping: add last char to postlude if needed.

	:param pre: target prelude.
	:param target: input string.
	:param post: target postlude.
	:param oracle: oracle function.
	:returns: tuple of (prelude, target, postlude) strings.
	"""

	interesting, well_formed = oracle(pre + target[:-1] + post)

	if interesting: return pre, target[:-1], post, well_formed
	else: return pre, target[:-1], target[-1] + post, well_formed


def complement_sweep(
	pre:str, 
	target:str, 
	post:str, 
	partlen:int, 
	oracle:Callable) -> tuple[str, int]:
	
	"""
	Identify benign chunks of target with variable granularity.

	:param pre: target prelude.
	:param target: input string.
	:param post: target postlude.
	:param partlen: partition length.
	:param oracle: oracle function.
	:returns: reduced string.
	"""
	
	# count no. of oracle calls that pass XML well-formedness pre-check
	n_good_oracalls = 0

	reduced = ""
	
	# test contiguous discrete chunks of size partlen for interestingness
	for i in range(0, len(target), partlen):
		split     = i + partlen
		removed   = target[i:split]
		remaining = target[split:]
		
		interesting, wellformed = oracle(pre + reduced + remaining + post)

		if wellformed: n_good_oracalls += 1

		if not interesting: reduced += removed
	
	return reduced, n_good_oracalls


def minimize(
	target:str, 
	oracle:Callable, 
	stats:bool  =False, 
	verbose:bool=False) -> tuple[str, int] | str:
	
	"""
	ZipMin Delta-Debugging aglorithm.
	
	:param target: input string.
	:param oracle: oracle function.
	:param stats: data collection flag.
	:param verbose: verbose output flag.
	:returns: reduced string and optional stats.
	"""

	# counters
	c_iteralt        = 0
	deficit          = 0
	n_total_oracalls = 0
	n_good_oracalls  = 0
		
	# pre and postludes
	pre  = ""
	post = ""

	# partition size
	partlen = len(target) // 2
	
	while partlen and target:
		if verbose: print(f"[{datetime.now().strftime('%H:%M:%S')}]  {len(pre + target + post):.2E}  {partlen}")

		# alternate between deficit-guided last zipping...
		if c_iteralt % 2: 
			for i in range(deficit):
				pre, target, post, wellformed = remove_last_char(pre, target, post, oracle)

				if stats and wellformed: n_good_oracalls += 1

			if stats: n_total_oracalls += deficit
			  
			deficit = 0
		
		# ...and complement sweep
		else:
			reduced, n_sweep_good_oracalls = complement_sweep(pre, target, post, partlen, oracle)
			
			n_sweep_total_oracalls = ceil(len(target) / partlen)
			
			# compute deficit: max(no. of oracle calls that lead to no change)
			deficit  = max(n_sweep_total_oracalls - (len(target) - len(reduced)), 0)

			if stats: 
				n_total_oracalls += n_sweep_total_oracalls
				n_good_oracalls += n_sweep_good_oracalls
	
			# reduce partition size if no update 
			if target == reduced: partlen //= 2
		
			target = reduced
		
		c_iteralt += 1

	# consolidate reduced target 
	target = pre + target + post
	
	return (target, n_total_oracalls, n_good_oracalls) if stats else target
