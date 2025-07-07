from __future__ import annotations
import logging

import requests

log = logging.getLogger(__name__)


def download_file(url: str, path: str) -> bool:
	"""
	Downloads a file from a URL and saves it to a specified path.

	:param url: The URL of the file to download.
	:param path: The local file path to save the content to.
	:return: True on success, False on failure.
	"""
	try:
		response = requests.get(url, stream=True)
		response.raise_for_status()
		with open(path, "wb") as media_file:
			for chunk in response.iter_content(chunk_size=8192):
				media_file.write(chunk)
		return True
	except requests.exceptions.HTTPError as e:
		log.error(f"HTTP {e.response.status_code} {e.response.reason} for URL: {url}")
	except requests.exceptions.RequestException as e:
		log.error(f"Could not download '{url}': {e}")
	except IOError as e:
		log.error(f"Could not write to file '{path}': {e}")
	return False
