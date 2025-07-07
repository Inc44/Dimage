from dateutil import parser
import argparse
import json
import os
import re
import requests


class Config:
	def __init__(self, args):
		self.input_folder = args.input
		self.output_folder = args.output
		self.download_guild_icon = args.guild_icon
		self.download_avatars = args.avatars
		self.download_mentions = args.mentions
		self.download_reactions = args.reactions
		self.download_reactions_emojis = args.reactions_emojis
		self.download_inline_emojis = args.inline_emojis
		self.download_attachments = args.attachments
		self.no_dupes = args.no_dupes
		self.skip_extensions = {
			ext.strip().lower() for ext in args.skip.split(",") if ext.strip()
		}
		self.timestamp_only = args.timestamp_only
		self.organize = args.organize
		self.visited_urls = set()
		self.file_use_counter = {}


def sanitize_filename(filename):
	return re.sub(r'[\/*?:"<>|]', "", filename)


def get_paths(config, json_filename=""):
	paths = {
		"icons": os.path.join(config.output_folder, "icons"),
		"avatars": os.path.join(config.output_folder, "avatars"),
		"emojis": os.path.join(config.output_folder, "emojis"),
		"channels": os.path.join(config.output_folder, "channels"),
		"subfolder": os.path.join(
			config.output_folder, sanitize_filename(json_filename)
		),
	}
	return paths


def create_directories(config, paths):
	if config.timestamp_only:
		return
	os.makedirs(config.output_folder, exist_ok=True)
	if config.organize:
		os.makedirs(paths["icons"], exist_ok=True)
		os.makedirs(paths["avatars"], exist_ok=True)
		os.makedirs(paths["emojis"], exist_ok=True)
		os.makedirs(paths["channels"], exist_ok=True)
	else:
		os.makedirs(paths["subfolder"], exist_ok=True)


def _get_media_item(url, default_id, default_ext, config, entity=None):
	if config.no_dupes and url in config.visited_urls:
		return None, None
	if config.no_dupes:
		config.visited_urls.add(url)
	name, ext = os.path.splitext(url.split("/")[-1].split("?")[0])
	if not ext:
		ext = default_ext
	if ext in config.skip_extensions:
		return None, None
	item_id = default_id
	if entity and "id" in entity:
		item_id = entity["id"]
	elif entity and "code" in entity:
		item_id = entity["code"]
	filename = sanitize_filename(str(item_id) + ext)
	return url, filename


def extract_media_from_json(data, config):
	media_data = []
	if config.download_guild_icon and "guild" in data and "iconUrl" in data["guild"]:
		url, filename = _get_media_item(
			data["guild"]["iconUrl"], data["guild"].get("id", "guild"), ".png", config
		)
		if url:
			media_data.append((url, data.get("exportedAt"), filename, "icon"))
	if "messages" not in data:
		return media_data
	for message in data["messages"]:
		timestamp = message.get("timestampEdited") or message.get("timestamp")
		if (
			config.download_avatars
			and "author" in message
			and "avatarUrl" in message["author"]
		):
			author = message["author"]
			url, filename = _get_media_item(
				author["avatarUrl"], author.get("id", "user"), ".png", config, author
			)
			if url:
				media_data.append((url, timestamp, filename, "avatar"))
		if config.download_mentions and "mentions" in message:
			for mention in message["mentions"]:
				if "avatarUrl" in mention:
					url, filename = _get_media_item(
						mention["avatarUrl"],
						mention.get("id", "mention"),
						".png",
						config,
						mention,
					)
					if url:
						media_data.append((url, timestamp, filename, "avatar"))
		if config.download_reactions and "reactions" in message:
			for reaction in message["reactions"]:
				if "users" in reaction:
					for user in reaction["users"]:
						if "avatarUrl" in user:
							url, filename = _get_media_item(
								user["avatarUrl"],
								user.get("id", "reactor"),
								".png",
								config,
								user,
							)
							if url:
								media_data.append((url, timestamp, filename, "avatar"))
		if config.download_reactions_emojis and "reactions" in message:
			for reaction in message["reactions"]:
				if "emoji" in reaction and "imageUrl" in reaction["emoji"]:
					emoji = reaction["emoji"]
					url, filename = _get_media_item(
						emoji["imageUrl"],
						emoji.get("id", "emoji"),
						".png",
						config,
						emoji,
					)
					if url:
						media_data.append((url, timestamp, filename, "emoji"))
		if config.download_inline_emojis and "inlineEmojis" in message:
			for emoji in message["inlineEmojis"]:
				if "imageUrl" in emoji:
					default_ext = (
						".svg"
						if "twemoji" in emoji["imageUrl"]
						else ".gif"
						if emoji.get("isAnimated")
						else ".png"
					)
					url, filename = _get_media_item(
						emoji["imageUrl"],
						emoji.get("code", "emoji"),
						default_ext,
						config,
						emoji,
					)
					if url:
						media_data.append((url, timestamp, filename, "emoji"))
		if config.download_attachments and "attachments" in message:
			for attachment in message["attachments"]:
				if "url" in attachment and "fileName" in attachment:
					url = attachment["url"]
					if config.no_dupes and url in config.visited_urls:
						continue
					if config.no_dupes:
						config.visited_urls.add(url)
					filename = sanitize_filename(attachment["fileName"])
					if os.path.splitext(filename)[1].lower() in config.skip_extensions:
						continue
					media_data.append((url, timestamp, filename, "attachment"))
	return media_data


def process_media_item(media_item, config, paths, json_filename):
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
		use_index = config.file_use_counter.get(base_path, 0)
		path_to_check = (
			f"{os.path.splitext(base_path)[0]}_{use_index:03d}{os.path.splitext(base_path)[1]}"
			if use_index > 0
			else base_path
		)
		config.file_use_counter[base_path] = use_index + 1
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
		response = requests.get(media_url, stream=True)
		response.raise_for_status()
		with open(final_path, "wb") as media_file:
			for chunk in response.iter_content(chunk_size=8192):
				media_file.write(chunk)
		set_timestamp(final_path, timestamp_str)
	except requests.exceptions.RequestException as e:
		print(f"Download error '{media_url}': {e}")
	except OSError as e:
		print(f"File error '{file_name}': {e}")


def set_timestamp(file_path, timestamp_str):
	if not timestamp_str:
		return
	try:
		dt = parser.parse(timestamp_str)
		timestamp = dt.timestamp()
		os.utime(file_path, (timestamp, timestamp))
	except (parser.ParserError, ValueError) as e:
		print(f"Timestamp error for '{file_path}': {e}")


def run(config):
	os.makedirs(config.input_folder, exist_ok=True)
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
			media_to_process = extract_media_from_json(data, config)
			for item in media_to_process:
				process_media_item(item, config, paths, json_filename)
		except (FileNotFoundError, json.JSONDecodeError) as e:
			print(f"Error processing file '{filename}': {e}")
		except Exception as e:
			print(f"An unexpected error occurred processing '{filename}': {e}")


if __name__ == "__main__":
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
		help="Avoid downloading duplicate files.",
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
