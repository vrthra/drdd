"""BaseX server management and native Server Protocol client."""

import hashlib
import socket
import subprocess
import time

from pathlib import Path
from typing  import BinaryIO


_HOST       = "127.0.0.1"
_PASS       = "password"
_PORT_START = 1984
_PORT_MAX   = 65535

BASEX_EXIT_MSGS = {
	2: "Invalid option or bad arguments",
	3: "BaseX server not reachable",
	4: "BaseX .jar file not found",
}


class BaseXError(Exception):
	"""Protocol-level or query-execution error from a BaseX server."""


def _recv_until_null(f) -> bytes:
	"""Read from buffered file until unescaped \\x00, decoding \\xFF escapes."""

	buf = bytearray()

	while True:
		b = f.read(1)

		if not b: raise BaseXError("Connection closed unexpectedly")

		if b == b"\x00": return bytes(buf)

		if b == b"\xff":
			nb = f.read(1)

			if not nb: raise BaseXError("Connection closed during escape sequence")

			buf.append(nb[0])

		else: buf.append(b[0])


def _send_str(sock:socket.socket, s:str) -> None:
	"""Escape and send a null-terminated UTF-8 string."""

	data = s.encode("utf-8")
	data = data.replace(b"\xff", b"\xff\xff").replace(b"\x00", b"\xff\x00")
	
	sock.sendall(data + b"\x00")


class BaseXSession:
	"""Persistent TCP session to a running BaseX server."""

	def __init__(self,
		host    :str = _HOST,
		port    :int = _PORT_START,
		user    :str = "admin",
		password:str = _PASS) -> None:

		self._host               = host
		self._port               = port
		self._user               = user
		self._password           = password
		self._sock:socket.socket = None      # type: ignore[assignment]
		self._file:BinaryIO      = None      # type: ignore[assignment]


	def _authenticate(self) -> None:
		"""Handshake: auto-detect digest vs CRAM-MD5 auth."""

		greeting = _recv_until_null(self._file).decode("utf-8")

		if ":" in greeting:
			# digest auth — realm:nonce
			realm, nonce = greeting.rsplit(":", 1)
			inner = hashlib.md5(f"{self._user}:{realm}:{self._password}".encode()).hexdigest()
		else:
			# CRAM-MD5 — nonce only
			nonce = greeting
			inner = hashlib.md5(self._password.encode()).hexdigest()

		auth_hash = hashlib.md5((inner + nonce).encode()).hexdigest()

		self._sock.sendall(self._user.encode() + b"\x00")
		self._sock.sendall(auth_hash.encode() + b"\x00")

		status = self._file.read(1)

		if status != b"\x00":
			raise BaseXError(f"Authentication failed on {self._host}:{self._port}")


	def _command(self, cmd:str) -> str:
		"""Execute a command via the command protocol.

		Response format: {result}\\x00 {info}\\x00 {status_byte}
		"""

		self._sock.sendall(cmd.encode("utf-8") + b"\x00")

		result = _recv_until_null(self._file)
		info   = _recv_until_null(self._file)
		status = self._file.read(1)

		if status != b"\x00":
			raise BaseXError(info.decode("utf-8", errors="replace"))

		return result.decode("utf-8")


	def __enter__(self) -> "BaseXSession":
		self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		self._sock.settimeout(30.0)
		self._sock.connect((self._host, self._port))
		self._file = self._sock.makefile('rb')
		self._authenticate()
		self._command("SET MAINMEM true")

		return self


	def query(self, xquery:str, context:str) -> str:
		"""Execute an XQuery with an XML document as the context item."""

		# create in-memory db from XML (\x08 + name\x00 + content\x00)
		self._sock.sendall(b"\x08")

		_send_str(self._sock, "_dd")
		_send_str(self._sock, context)

		info   = _recv_until_null(self._file)
		status = self._file.read(1)

		if status != b"\x00": raise BaseXError(f"CREATE DB failed: {info.decode('utf-8', errors='replace')}")

		# run XQuery against the open database (command protocol)
		try: return self._command("XQUERY " + xquery)

		# drop the temp database
		finally:
			try: self._command("DROP DB _dd")
			except (BaseXError, OSError): pass


	def __exit__(self, *_) -> None:
		if self._sock is None: return

		try:
			self._sock.sendall(b"exit\x00")
		except OSError: pass

		try:
			if self._file is not None: self._file.close()
		except OSError: pass

		try:
			self._sock.close()
		except OSError: pass

		self._sock = None  # type: ignore [assignment]
		self._file = None  # type: ignore [assignment]


def _port_free(port:int) -> bool:
	"""Check if a port is free."""

	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.settimeout(0.1)
		
		return s.connect_ex((_HOST, port)) != 0


def _find_free_pair(start:int=_PORT_START) -> tuple[int, int]:
	"""Find a pair of free ports with gap for BaseX event ports.

	BaseX claims port+1 as its event port, so each server needs two
	consecutive ports. We allocate p and p+2 to avoid collision.
	"""

	p = start

	while p + 3 < _PORT_MAX:
		if all(_port_free(p + i) for i in range(4)): return p, p + 2

		p += 1

	raise RuntimeError("No free port group found")


def _wait_for_port(port: int, timeout: float = 25.0) -> None:
	"""Wait until server spins up."""

	deadline = time.monotonic() + timeout

	while time.monotonic() < deadline:
		if not _port_free(port): return
		
		time.sleep(0.1)

	raise TimeoutError(f"Timed out waiting for {_HOST}:{port}")


def _start_server(
	jar_path:Path,
	port    :int,
	host    :str = _HOST,
	password:str = _PASS) -> subprocess.Popen:

	"""Start a BaseX server."""

	return subprocess.Popen(
		args = [
			
			"java",
			"-cp", str(jar_path), "org.basex.BaseXServer",
			"-n",  host,
			"-p",  str(port),
			"-c",  f"PASSWORD {password}"
		
		],

		stdout = subprocess.DEVNULL,
		stderr = subprocess.DEVNULL
	)


class BaseXServerPair:
	"""Context manager that starts a good/bad pair of BaseX servers and stops them on exit."""

	def __init__(self, good_jar:Path, bad_jar:Path) -> None:
		for j in (good_jar, bad_jar):
			if not j.exists(): raise FileNotFoundError(f"Missing jar: {j}")

		self._good_jar  = good_jar
		self._bad_jar   = bad_jar
		self._good_port = None
		self._bad_port  = None
		self._good_proc = None
		self._bad_proc  = None


	@property
	def good_port(self) -> int:
		if self._good_port is None: raise RuntimeError("BaseXServerPair not started")
		
		return self._good_port


	@property
	def bad_port(self) -> int:
		if self._bad_port is None: raise RuntimeError("BaseXServerPair not started")
		
		return self._bad_port


	def __enter__(self) -> "BaseXServerPair":
		start = _PORT_START

		for attempt in range(3):
			self._good_port, self._bad_port = _find_free_pair(start)

			self._bad_proc  = _start_server(self._bad_jar, self.bad_port)
			self._good_proc = _start_server(self._good_jar, self.good_port)

			try:
				_wait_for_port(self._bad_port)
				_wait_for_port(self._good_port)
				
				return self

			# port likely grabbed between availability check and server start
			except TimeoutError:
				for proc in (self._good_proc, self._bad_proc):
					if proc is None: continue

					try: proc.kill()
					except OSError: pass

					try: proc.wait(timeout=2)
					except subprocess.TimeoutExpired: pass

				self._good_proc = None
				self._bad_proc  = None
				start           = self._bad_port + 2

				if attempt == 2: raise

		return self  # unreachable


	def __exit__(self, *_) -> None:
		for proc in (self._good_proc, self._bad_proc):
			if proc is None: continue

			try: proc.terminate()
			except OSError:	pass

			try: proc.wait(timeout=5)
			
			except subprocess.TimeoutExpired:
				try: proc.kill()
				except OSError: pass

				try: proc.wait(timeout=2)
				except subprocess.TimeoutExpired: pass
