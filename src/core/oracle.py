from typing import TypeVar, Generic, Sequence


T = TypeVar("T")


class Oracle(Generic[T]):
	"""Instrumented oracle base."""

	def __init__(self) -> None:
		self.calls = 0


	def _call(self, candidate:Sequence[T]) -> bool: ...


	def __call__(self, candidate:Sequence[T]) -> bool:
		"""Update instrumentation and execute."""
		
		self.calls += 1
		
		return self._call(candidate)