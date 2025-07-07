from __future__ import annotations
from typing import Dict, Optional
import logging
import os
import re

from dateutil import parser

from .config import Config
from .downloader import download_file
from .extractor import MediaItem

log = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
	"""
	Removes characters invalid for file names from a string.

	:param filename: The initial filename string.
	:return: A sanitized string suitable for use as a filename.
	"""
	return re.sub(r'[\/*?:"<>|]', "", filename)


def get_paths(config: Config, json_filename: str = "") -> Dict[str, str]:
	"""
	Constructs a dictionary of required directory paths.

	:param config: The application configuration.
	:param json_filename: The base name of the JSON file being processed.
	:return: A dictionary mapping path keys to absolute paths.
	"""
	return {
		"icons": os.path.join(config.output_folder, "icons"),
		"avatars": os.path.join(config.output_folder, "avatars"),
		"emojis": os.path.join(config.output_folder, "emojis"),
		"channels": os.path.join(config.output_folder, "channels"),
		"subfolder": os.path.join(
			config.output_folder, sanitize_filename(json_filename)
		),
	}


def create_directories(config: Config, paths: Dict[str, str]) -> None:
	"""
	Creates the necessary output directories based on configuration.

	:param config: The application configuration.
	:param paths: A dictionary of required paths from get_paths().
	"""
	if config.timestamp_only:
		return
	os.makedirs(config.output_folder, exist_ok=True)
	if config.organize:
		for key in ["icons", "avatars", "emojis", "channels"]:
			os.makedirs(paths[key], exist_ok=True)
	else:
		os.makedirs(paths["subfolder"], exist_ok=True)


def set_timestamp(file_path: str, timestamp_str: Optional[str]) -> None:
	"""
	Sets the modification and access time of a file.

	:param file_path: The path to the file.
	:param timestamp_str: An ISO 8601 formatted date-time string.
	"""
	if not timestamp_str:
		return
	try:
		dt = parser.parse(timestamp_str)
		timestamp = dt.timestamp()
		os.utime(file_path, (timestamp, timestamp))
	except (parser.ParserError, ValueError) as e:
		log.warning(f"Could not parse timestamp for '{file_path}': {e}")
	except OSError as e:
		log.warning(f"Could not set timestamp for '{file_path}': {e}")


def process_media_item(
	media_item: MediaItem,
	config: Config,
	paths: Dict[str, str],
	json_filename: str,
	file_use_counter: Dict[str, int],
) -> None:
	"""
	Processes a single media item: determines its path, downloads it, and sets its timestamp.

	:param media_item: The MediaItem tuple to process.
	:param config: The application configuration.
	:param paths: A dictionary of required paths.
	:param json_filename: The base name of the source JSON file.
	:param file_use_counter: A counter for filename collisions in timestamp-only mode.
	"""
	media_url, timestamp_str, file_name, media_type = media_item
	file_name = sanitize_filename(file_name)
	target_folder = ""
	if config.organize:
		if media_type == "icon":
			target_folder = paths["icons"]
		elif media_type == "avatar":
			target_folder = paths["avatars"]
		elif media_type == "emoji":
			target_folder = paths["emojis"]
		elif media_type == "attachment":
			channel_specific_path = os.path.join(
				paths["channels"], sanitize_filename(json_filename)
			)
			if not config.timestamp_only:
				os.makedirs(channel_specific_path, exist_ok=True)
			target_folder = channel_specific_path
	else:
		target_folder = paths["subfolder"]
	base_path = os.path.join(target_folder, file_name)
	if config.timestamp_only:
		use_index = file_use_counter.get(base_path, 0)
		path_to_check = (
			f"{os.path.splitext(base_path)[0]}_{use_index:03d}{os.path.splitext(base_path)[1]}"
			if use_index > 0
			else base_path
		)
		file_use_counter[base_path] = use_index + 1
		if os.path.exists(path_to_check):
			set_timestamp(path_to_check, timestamp_str)
		else:
			log.warning(f"Skipping timestamp for non-existent file: {path_to_check}")
		return
	final_path = base_path
	count = 1
	while os.path.exists(final_path):
		name, ext = os.path.splitext(base_path)
		final_path = f"{name}_{count:03d}{ext}"
		count += 1
	if download_file(media_url, final_path):
		set_timestamp(final_path, timestamp_str)
