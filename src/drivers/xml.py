"""XML oracle and minimizer driver using native BaseX protocol + saxonche."""

import os
import re

from importlib       import import_module
from pathlib         import Path
from saxonche        import PySaxonProcessor
from algos           import ALGORITHMS
from core.oracle     import Oracle
from drivers.basex   import BaseXSession, BaseXServerPair, BaseXError
from drivers.logging import MinimizerLog


_ID_RE  = re.compile(r'id="([^"]*)"')
_XML_P0 = 0.25


def _extract_ids(text:str) -> list[str]:
	"""Extract id attribute values from XML output, filtering blanks."""

	return [m for m in _ID_RE.findall(text) if m.strip()]


class BaseXOracle(Oracle[int]):
	"""Three-way oracle: Saxon (reference) vs. bad-BaseX vs. good-BaseX."""

	def __init__(self, query_text:str, good_jar:Path, bad_jar:Path) -> None:
		super().__init__()

		self._query_text                = query_text
		self._good_jar                  = good_jar
		self._bad_jar                   = bad_jar
		self._servers:BaseXServerPair   = None         # type: ignore[assignment]
		self._saxon:PySaxonProcessor    = None         # type: ignore[assignment]
		self._bad_session:BaseXSession  = None         # type: ignore[assignment]
		self._good_session:BaseXSession = None         # type: ignore[assignment]
		self._saved_stderr              = -1


	def __enter__(self) -> "BaseXOracle":
		"""Start BaseX servers, initialize saxonche, open TCP sessions."""

		try:
			self._servers      = BaseXServerPair(self._good_jar, self._bad_jar).__enter__()
			self._bad_session  = BaseXSession(port=self._servers.bad_port).__enter__()
			self._good_session = BaseXSession(port=self._servers.good_port).__enter__()

		except Exception:
			self.__exit__(None, None, None)
			raise

		# saxon setup
		self._saxon = PySaxonProcessor(license=False)
		self._xq    = self._saxon.new_xquery_processor()

		self._xq.set_query_content(self._query_text)

		# redirect fd 2 once to suppress saxonche XML parse noise
		devnull            = os.open(os.devnull, os.O_WRONLY)
		self._saved_stderr = os.dup(2)
		
		os.dup2(devnull, 2)
		os.close(devnull)

		return self


	def _call(self, candidate) -> bool:
		xml_str = bytes(candidate).decode("utf-8", errors="replace")

		# saxon reference
		try:
			node = self._saxon.parse_xml(xml_text=xml_str)

			self._xq.set_context(xdm_item=node)

			saxon_result = self._xq.run_query_to_string()

		except Exception: return False

		if saxon_result is None: return False

		saxon_ids = _extract_ids(saxon_result)

		# BaseX queries
		try:
			bad_result  = self._bad_session.query(self._query_text, xml_str)
			good_result = self._good_session.query(self._query_text, xml_str)
		
		except (BaseXError, ConnectionError, OSError): return False

		bad_ids  = _extract_ids(bad_result)
		good_ids = _extract_ids(good_result)

		# three-way predicate
		return bad_ids != saxon_ids and good_ids == saxon_ids


	def __exit__(self, *_) -> None:
		"""Clean up context managers."""

		if self._saved_stderr != -1:
			
			# restore stderr before cleaning up so any shutdown errors are visible
			os.dup2(self._saved_stderr, 2)
			os.close(self._saved_stderr)
			
			self._saved_stderr = -1

		for resource in (self._bad_session, self._good_session, self._servers):
			if resource is None: continue
			try: resource.__exit__(None, None, None)
			except Exception: pass


def xml_minimizer(
	input_path :Path,
	algorithm  :str,
	query_path :Path,
	good_jar   :Path,
	bad_jar    :Path,
	output_path:Path | None         = None,
	log        :MinimizerLog | None = None) -> dict:

	"""Run a DD minimization over an XML oracle."""

	if algorithm not in ALGORITHMS: raise ValueError(f"Unknown algorithm '{algorithm}'. Available: {', '.join(ALGORITHMS)}")

	original = input_path.read_bytes()
	minimize = getattr(import_module(f"algos.{algorithm}"), "minimize")

	oracle = BaseXOracle(
		
		query_text = query_path.read_text(),
		good_jar   = good_jar,
		bad_jar    = bad_jar,
	
	)

	if log: log.bind(len(original), oracle)

	# initialize probabilistic models
	kwargs = {"p_0": _XML_P0} if algorithm in ("cdd", "probdd") else {}

	with oracle:
		minimized = minimize(
			
			target = original,
			oracle = oracle,
			log    = log,
			
			**kwargs,
		)

	if output_path: output_path.write_bytes(bytes(minimized))

	return {
		"minimized_length"  : len(minimized),
		"oracle_invocations": oracle.calls,
	}
