import os


_BAR_FILLER    = "░"
_BAR_SOLID     = "█"
_BAR_PARTIALS  = ("", "▒", "▓")


def terminal_width(max_cols:int=100, fallback:int=80) -> int:
	"""Return the current terminal width, capped at max_cols."""
	
	try:    return min(os.get_terminal_size().columns, max_cols)
	except: return fallback


def fmt_bytes(n:int) -> str:
	"""Format a byte count as a human-readable string."""
	
	if n < 0:       return "? B"
	if n < 2 ** 10: return f"{n} B"
	if n < 2 ** 20: return f"{n / 1024:.1f} KB"
	
	return f"{n / 1048576:.1f} MB"


def fmt_time(secs:float) -> str:
	"""Format an elapsed time in seconds as MM:SS or H:MM:SS."""
	
	s    = int(secs)
	m, s = divmod(s, 60)
	h, m = divmod(m, 60)
	
	if h: return f"{h}:{m:02d}:{s:02d}"
	
	return f"{m:02d}:{s:02d}"


def progress_bar(pct: float, width: int = 10) -> str:
	"""Construct a visual percentage progress bar."""

	granularity = len(_BAR_PARTIALS)

	total = round(width * granularity * pct / 100)
	full  = total // granularity
	frac  = total % granularity
	empty = width - full - (1 if frac else 0)

	return _BAR_SOLID * full + _BAR_PARTIALS[frac] + _BAR_FILLER * empty


def labelled_rule(width:int, label:str):
	"""Construct a horizontal rule with a label in the middle."""

	dashes = "─" * max(0, (width - (len(label) + 2)) // 2)

	return f"{dashes}<{label}>{dashes}".rjust(width, "-")