from __future__ import annotations
from dateutil import parser
from typing import Any, Dict, List, Optional, Set, Tuple
import argparse
import json
import os
import re
import requests
import sys

MediaItem = Tuple[str, Optional[str], str, str]


class Config:
	"""Holds the static configuration for a Dimage run."""

	def __init__(self, args: argparse.Namespace):
		"""
		Initializes the configuration from parsed command-line arguments.

		:param args: The namespace object from argparse.ArgumentParser.parse_args().
		"""
		self.input_folder: str = args.input
		self.output_folder: str = args.output
		self.download_guild_icon: bool = args.guild_icon
		self.download_avatars: bool = args.avatars
		self.download_mentions: bool = args.mentions
		self.download_reactions: bool = args.reactions
		self.download_reactions_emojis: bool = args.reactions_emojis
		self.download_inline_emojis: bool = args.inline_emojis
		self.download_attachments: bool = args.attachments
		self.no_dupes: bool = args.no_dupes
		self.skip_extensions: Set[str] = {
			ext.strip().lower() for ext in args.skip.split(",") if ext.strip()
		}
		self.timestamp_only: bool = args.timestamp_only
		self.organize: bool = args.organize


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


def _get_media_item(
	url: str,
	default_id: str,
	default_ext: str,
	config: Config,
	visited_urls: Set[str],
	entity: Optional[Dict[str, Any]] = None,
) -> Optional[Tuple[str, str]]:
	"""
	Validates a media URL and generates a filename.
	Checks for duplicates and skipped extensions.

	:param url: The URL of the media asset.
	:param default_id: A fallback ID to use if the entity has no ID.
	:param default_ext: A fallback extension if one cannot be derived from the URL.
	:param config: The application configuration.
	:param visited_urls: The set of URLs already processed to avoid duplicates.
	:param entity: The JSON object (user, emoji, etc.) associated with the media.
	:return: A tuple of (URL, filename) or None if the item should be skipped.
	"""
	if config.no_dupes and url in visited_urls:
		return None
	_, ext = os.path.splitext(url.split("/")[-1].split("?")[0])
	if not ext:
		ext = default_ext
	if ext.lower() in config.skip_extensions:
		return None
	item_id = default_id
	if entity and "id" in entity:
		item_id = entity["id"]
	elif entity and "code" in entity:
		item_id = entity["code"]
	filename = sanitize_filename(str(item_id) + ext)
	return url, filename


def _extract_guild_icon(
	data: Dict[str, Any], config: Config, visited_urls: Set[str]
) -> List[MediaItem]:
	"""Extracts guild icon media item from the JSON data."""
	if not (
		config.download_guild_icon and "guild" in data and "iconUrl" in data["guild"]
	):
		return []
	guild = data["guild"]
	item = _get_media_item(
		guild["iconUrl"], guild.get("id", "guild"), ".png", config, visited_urls
	)
	if item:
		visited_urls.add(item[0])
		return [(item[0], data.get("exportedAt"), item[1], "icon")]
	return []


def _extract_message_media(
	message: Dict[str, Any], config: Config, visited_urls: Set[str]
) -> List[MediaItem]:
	"""Extracts all media items from a single message object."""
	media_data = []
	timestamp = message.get("timestampEdited") or message.get("timestamp")
	if (
		config.download_avatars
		and "author" in message
		and "avatarUrl" in message["author"]
	):
		author = message["author"]
		item = _get_media_item(
			author["avatarUrl"],
			author.get("id", "user"),
			".png",
			config,
			visited_urls,
			author,
		)
		if item:
			visited_urls.add(item[0])
			media_data.append((item[0], timestamp, item[1], "avatar"))
	if config.download_mentions and "mentions" in message:
		for mention in message["mentions"]:
			if "avatarUrl" in mention:
				item = _get_media_item(
					mention["avatarUrl"],
					mention.get("id", "mention"),
					".png",
					config,
					visited_urls,
					mention,
				)
				if item:
					visited_urls.add(item[0])
					media_data.append((item[0], timestamp, item[1], "avatar"))
	if "reactions" in message:
		for reaction in message["reactions"]:
			if config.download_reactions and "users" in reaction:
				for user in reaction["users"]:
					if "avatarUrl" in user:
						item = _get_media_item(
							user["avatarUrl"],
							user.get("id", "reactor"),
							".png",
							config,
							visited_urls,
							user,
						)
						if item:
							visited_urls.add(item[0])
							media_data.append((item[0], timestamp, item[1], "avatar"))
			if (
				config.download_reactions_emojis
				and "emoji" in reaction
				and "imageUrl" in reaction["emoji"]
			):
				emoji = reaction["emoji"]
				item = _get_media_item(
					emoji["imageUrl"],
					emoji.get("id", "emoji"),
					".png",
					config,
					visited_urls,
					emoji,
				)
				if item:
					visited_urls.add(item[0])
					media_data.append((item[0], timestamp, item[1], "emoji"))
	if config.download_inline_emojis and "inlineEmojis" in message:
		for emoji in message["inlineEmojis"]:
			if "imageUrl" in emoji:
				default_ext = ".gif" if emoji.get("isAnimated") else ".png"
				item = _get_media_item(
					emoji["imageUrl"],
					emoji.get("code", "emoji"),
					default_ext,
					config,
					visited_urls,
					emoji,
				)
				if item:
					visited_urls.add(item[0])
					media_data.append((item[0], timestamp, item[1], "emoji"))
	if config.download_attachments and "attachments" in message:
		for attachment in message["attachments"]:
			if "url" in attachment and "fileName" in attachment:
				url = attachment["url"]
				if config.no_dupes and url in visited_urls:
					continue
				filename = sanitize_filename(attachment["fileName"])
				if os.path.splitext(filename)[1].lower() in config.skip_extensions:
					continue
				visited_urls.add(url)
				media_data.append((url, timestamp, filename, "attachment"))
	return media_data


def extract_media_from_json(
	data: Dict[str, Any], config: Config, visited_urls: Set[str]
) -> List[MediaItem]:
	"""
	Parses the entire JSON data structure and extracts all media items.

	:param data: The loaded JSON data as a dictionary.
	:param config: The application configuration.
	:param visited_urls: The set of URLs already processed to avoid duplicates.
	:return: A list of MediaItem tuples to be processed.
	"""
	media_data = _extract_guild_icon(data, config, visited_urls)
	if "messages" not in data:
		return media_data
	for message in data["messages"]:
		media_data.extend(_extract_message_media(message, config, visited_urls))
	return media_data


def download_file(url: str, path: str) -> None:
	"""
	Downloads a file from a URL and saves it to a specified path.

	:param url: The URL of the file to download.
	:param path: The local file path to save the content to.
	"""
	try:
		response = requests.get(url, stream=True)
		response.raise_for_status()
		with open(path, "wb") as media_file:
			for chunk in response.iter_content(chunk_size=8192):
				media_file.write(chunk)
	except requests.exceptions.RequestException as e:
		print(f"Download error '{url}': {e}", file=sys.stderr)


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
		return
	final_path = base_path
	count = 1
	while os.path.exists(final_path):
		name, ext = os.path.splitext(base_path)
		final_path = f"{name}_{count:03d}{ext}"
		count += 1
	try:
		download_file(media_url, final_path)
		set_timestamp(final_path, timestamp_str)
	except OSError as e:
		print(f"File error '{file_name}': {e}", file=sys.stderr)


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
		print(f"Timestamp error for '{file_path}': {e}", file=sys.stderr)


def run(config: Config) -> None:
	"""
	Main execution logic for the script.
	Iterates through JSON files, extracts media, and processes them.

	:param config: The application configuration.
	"""
	os.makedirs(config.input_folder, exist_ok=True)
	visited_urls: Set[str] = set()
	file_use_counter: Dict[str, int] = {}
	for filename in os.listdir(config.input_folder):
		if not filename.endswith(".json"):
			continue
		filepath = os.path.join(config.input_folder, filename)
		json_filename = os.path.splitext(filename)[0]
		paths = get_paths(config, json_filename)
		create_directories(config, paths)
		try:
			with open(filepath, "r", encoding="utf-8") as f:
				data = json.load(f)
			media_to_process = extract_media_from_json(data, config, visited_urls)
			for item in media_to_process:
				process_media_item(item, config, paths, json_filename, file_use_counter)
		except (FileNotFoundError, json.JSONDecodeError) as e:
			print(f"Error processing file '{filename}': {e}", file=sys.stderr)
		except IOError as e:
			print(
				f"An I/O error occurred processing '{filename}': {e}", file=sys.stderr
			)


def main() -> None:
	"""Parses command-line arguments and starts the download process."""
	arg_parser = argparse.ArgumentParser(
		description="Downloads all media assets from JSON files generated by DiscordChatExporter"
	)
	arg_parser.add_argument(
		"-i",
		"--input",
		default="json",
		help="Path to the input directory containing `.json` files. Default: `json`.",
	)
	arg_parser.add_argument(
		"-o",
		"--output",
		default="downloads",
		help="Path to the root output directory for downloads. Default: `downloads`.",
	)
	arg_parser.add_argument(
		"--no-guild-icon",
		action="store_false",
		dest="guild_icon",
		help="Skip downloading the guild/server icon.",
	)
	arg_parser.add_argument(
		"--no-avatars",
		action="store_false",
		dest="avatars",
		help="Skip downloading message author avatars.",
	)
	arg_parser.add_argument(
		"--no-mentions",
		action="store_false",
		dest="mentions",
		help="Skip downloading avatars of mentioned users.",
	)
	arg_parser.add_argument(
		"--no-reactions",
		action="store_false",
		dest="reactions",
		help="Skip downloading avatars of users who reacted.",
	)
	arg_parser.add_argument(
		"--no-reactions-emojis",
		action="store_false",
		dest="reactions_emojis",
		help="Skip downloading custom emojis used in reactions.",
	)
	arg_parser.add_argument(
		"--no-inline-emojis",
		action="store_false",
		dest="inline_emojis",
		help="Skip downloading custom emojis used inline in messages.",
	)
	arg_parser.add_argument(
		"--no-attachments",
		action="store_false",
		dest="attachments",
		help="Skip downloading message attachments.",
	)
	arg_parser.add_argument(
		"--no-dupes",
		action="store_true",
		help="Avoid downloading duplicate files based on URL.",
	)
	arg_parser.add_argument(
		"--skip",
		type=str,
		default="",
		help="Skip files with specified comma-separated extensions.",
	)
	arg_parser.add_argument(
		"--timestamp-only",
		action="store_true",
		help="Set timestamps on existing files without downloading.",
	)
	arg_parser.add_argument(
		"--organize",
		action="store_true",
		help="Organize files into categories: `icons`, `avatars`, `emojis`, and `channels` (for attachments).",
	)
	args = arg_parser.parse_args()
	config = Config(args)
	run(config)


if __name__ == "__main__":
	main()
