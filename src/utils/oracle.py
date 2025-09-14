from pathlib import Path
from typing import Callable, Optional
import subprocess


# shell script custom exit code to message map
EXIT_MESSAGES = {
	2: "Invalid option or bad arguments",
	3: "BaseX server not reachable",
	4: "BaseX .jar file not found",
}


def build_oracle(
	base:Path, 
	input_name:str, 
	script_name:str, 
	good_port:Optional[str]=None, 
	timeout:Optional[float]=None) -> Callable:
	
	"""
	Generate XML oracle callable for debugger.
	
	:param base: path to predicate directory.
	:param input_name: relative (to base) path to input.
	:param script_name: relative (to base) path to oracle shell script.
	:param good_port: port on which "good" BaseX server is running.
	:param timeout: subprocess timeout value.
	:returns: oracle function.
	"""

	xml_path    = base / input_name
	script_path = base / script_name

	def oracle(candidate:str) -> tuple[bool, bool]:
		"""
		Invoke oracle on candidate string.

		:param candidate: input string.
		:returns: is interesting boolean.
		"""

		# write candidate to file and atomically replace
		tmp_path = xml_path.with_suffix(xml_path.suffix + ".tmp")
		tmp_path.write_text(candidate, encoding="utf-8")
		tmp_path.replace(xml_path)
		
		try:
			cmd = ["bash", str(script_path)]
			
			# pass good port
			if good_port: cmd += ["--good-port", str(good_port)]
			
			# forward input file name
			cmd += ["--input", input_name]
			
			proc = subprocess.run(cmd,
				cwd    =base,
				stdout =subprocess.DEVNULL,
				stderr =subprocess.DEVNULL,
				timeout=timeout,
			)

		# fail on timeout
		except subprocess.TimeoutExpired: return False

		# handle breaking errors
		if proc.returncode > 1: 
			print(f"Fatal Error ({proc.returncode}): {EXIT_MESSAGES.get(proc.returncode, 'Unknown')}")

			raise SystemExit(proc.returncode)

		# "interesting" if desired error (retcode=0)
		return proc.returncode == 0

	return oracle
