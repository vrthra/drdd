import unittest

from typing       import TypeVar, Callable, Sequence
from core.oracle import Oracle
from importlib    import import_module
from algos        import ALGORITHMS


T = TypeVar("T")


class UnittestOracle(Oracle[T]):
	"""Oracle wrapping a plain callable."""

	def __init__(self, fn:Callable[[Sequence[T]], bool]) -> None:
		super().__init__()

		self._fn = fn


	def _call(self, candidate:Sequence[T]) -> bool:
		"""Call function on candidate."""
		
		return self._fn(candidate)


class TestSanity(unittest.TestCase):
	"""Basic sanity checks for all DD variants."""

	def _basic_minimization(self, target, oracle, expected):
		"""Basic minimization test template."""

		for algorithm in ALGORITHMS:
			with self.subTest(variant=algorithm):
				
				# import minimizer
				minimize = getattr(import_module(f"algos.{algorithm}"), "minimize")
				
				result = minimize(
					
					target = list(target),
					oracle = UnittestOracle[str](fn=lambda s: oracle("".join(s))),
				
				)

				self.assertEqual("".join(result), expected)


	def test_reduces_to_single_required_char(self):
		self._basic_minimization(
			target   = "aaaaabaaaa", 
			oracle   = lambda s: "b" in s, 
			expected = "b"
		)


	def test_reduces_to_required_substring(self):
		self._basic_minimization(
			target   = "zzzabczzz", 
			oracle   = lambda s: "abc" in s, 
			expected = "abc"
		)


	def test_always_true_minimizes_to_empty(self):
		self._basic_minimization(
			target   = "abcdef",
			oracle   = lambda s: True,
			expected = ""
		)


	def test_single_element_removable(self):
		self._basic_minimization(
			target   = "x",
			oracle   = lambda s: True,
			expected = ""
		)


	def test_single_element_required(self):
		self._basic_minimization(
			target   = "x",
			oracle   = lambda s: "x" in s,
			expected = "x"
		)


	def test_always_false_keeps_original(self):
		self._basic_minimization(
			target   = "abcdef", 
			oracle   = lambda s: False, 
			expected = "abcdef"
		)


	def test_unicode_handling(self):
		self._basic_minimization(
			target   = "αβγdéfβγ", 
			oracle   = lambda s: "dé" in s, 
			expected = "dé"
		)


	def test_large_noise_minimizes_to_pattern(self):
		self._basic_minimization(
			target   = ("x" * 300) + "needle" + ("x" * 400), 
			oracle   = lambda s: "needle" in s, 
			expected = "needle"
		)


	def test_odd_length_partitions(self):
		self._basic_minimization(
			target   = ("a" * 17) + "Z" + ("a" * 13), 
			oracle   = lambda s: "Z" in s, 
			expected = "Z"
		)


	def test_two_required_occurrences(self):
		self._basic_minimization(
			target   = "bbbbbaaaabbbb", 
			oracle   = lambda s: s.count("a") >= 2, 
			expected = "aa"
		)


	def test_newline_sequence_required(self):
		self._basic_minimization(
			target   = "line1\nline2\n\nline4\n", 
			oracle   = lambda s: "\n\n" in s, 
			expected = "\n\n"
		)


	def test_requires_prefix_and_suffix(self):
		self._basic_minimization(
			target   = "Axxx--middle--yyyZ", 
			oracle   = lambda s: s.startswith("A") and s.endswith("Z"), 
			expected = "AZ"
		)


	def test_non_contiguous_requirements_minimal(self):
		self._basic_minimization(
			target   = "zzazbzcazz", 
			oracle   = lambda s: ("a" in s) and ("c" in s) and (s.find("a") < s.find("c")), 
			expected = "ac"
		)


if __name__ == "__main__":
	unittest.main()
