import json
import os
import requests
from datetime import datetime
import pytz
import argparse
import re


def sanitize_filename(filename):
	return re.sub(r'[\/*?:"<>|]', "", filename)


def download_media_from_json(
	input_folder="json",
	output_folder="downloads",
	download_guild_icon=True,
	download_avatars=True,
	download_mentions=True,
	download_reactions=True,
	download_reactions_emojis=True,
	download_inline_emojis=True,
	download_attachments=True,
	no_dupes=False,
):
	if not os.path.exists(input_folder):
		os.makedirs(input_folder)
	if not os.path.exists(output_folder):
		os.makedirs(output_folder)
	visited_urls = set()
	for filename in os.listdir(input_folder):
		if filename.endswith(".json"):
			filepath = os.path.join(input_folder, filename)
			json_filename = os.path.splitext(filename)[0]
			output_subfolder = os.path.join(
				output_folder, sanitize_filename(json_filename)
			)
			try:
				with open(filepath, "r", encoding="utf-8") as f:
					data = json.load(f)
				media_data = []
				if (
					download_guild_icon
					and "guild" in data
					and "iconUrl" in data["guild"]
				):
					url = data["guild"]["iconUrl"]
					if not no_dupes or url not in visited_urls:
						if no_dupes:
							visited_urls.add(url)
						name, ext = os.path.splitext(url.split("/")[-1].split("?")[0])
						if not ext:
							ext = ".png"
						filename = sanitize_filename(
							data["guild"].get("id", "guild") + ext
						)
						media_data.append((url, data.get("exportedAt"), filename))
				if "messages" in data:
					for message in data["messages"]:
						timestamp = message.get("timestamp")
						if message.get("timestampEdited") is not None:
							timestamp = message.get("timestampEdited")
						if download_avatars:
							author = message.get("author")
							if author and "avatarUrl" in author:
								url = author["avatarUrl"]
								if not no_dupes or url not in visited_urls:
									if no_dupes:
										visited_urls.add(url)
									name, ext = os.path.splitext(
										url.split("/")[-1].split("?")[0]
									)
									if not ext:
										ext = ".png"
									filename = sanitize_filename(
										author.get("id", "user") + ext
									)
									media_data.append((url, timestamp, filename))
						if download_mentions:
							if "mentions" in message:
								for mention in message["mentions"]:
									if "avatarUrl" in mention:
										url = mention["avatarUrl"]
										if not no_dupes or url not in visited_urls:
											if no_dupes:
												visited_urls.add(url)
											name, ext = os.path.splitext(
												url.split("/")[-1].split("?")[0]
											)
											if not ext:
												ext = ".png"
											filename = sanitize_filename(
												mention.get("id", "mention") + ext
											)
											media_data.append(
												(url, timestamp, filename)
											)
						if download_reactions:
							if "reactions" in message:
								for reaction in message["reactions"]:
									if "users" in reaction:
										for user in reaction["users"]:
											if "avatarUrl" in user:
												url = user["avatarUrl"]
												if (
													not no_dupes
													or url not in visited_urls
												):
													if no_dupes:
														visited_urls.add(url)
													name, ext = os.path.splitext(
														url.split("/")[-1].split("?")[0]
													)
													if not ext:
														ext = ".png"
													filename = sanitize_filename(
														user.get("id", "reactor") + ext
													)
													media_data.append(
														(url, timestamp, filename)
													)
						if download_reactions_emojis:
							if "reactions" in message:
								for reaction in message["reactions"]:
									if "emoji" in reaction:
										emoji = reaction["emoji"]
										if "imageUrl" in emoji:
											url = emoji["imageUrl"]
											if not no_dupes or url not in visited_urls:
												if no_dupes:
													visited_urls.add(url)
												base_name = url.split("/")[-1].split(
													"?"
												)[0]
												name, ext = os.path.splitext(base_name)
												if not ext:
													ext = ".png"
												filename = sanitize_filename(
													emoji.get("id", "emoji") + ext
												)  # Use "emoji"
												media_data.append(
													(url, timestamp, filename)
												)
						if download_inline_emojis:
							if "inlineEmojis" in message:
								for emoji in message["inlineEmojis"]:
									if "imageUrl" in emoji:
										url = emoji["imageUrl"]
										if not no_dupes or url not in visited_urls:
											if no_dupes:
												visited_urls.add(url)
											name, ext = os.path.splitext(
												url.split("/")[-1].split("?")[0]
											)
											if not ext:
												if "twemoji" in url:
													ext = ".svg"
												elif emoji.get("isAnimated"):
													ext = ".gif"
												else:
													ext = ".png"
											filename = sanitize_filename(
												emoji.get("code", "emoji") + ext
											)
											media_data.append(
												(url, timestamp, filename)
											)
						if download_attachments:
							if "attachments" in message:
								for attachment in message["attachments"]:
									if "url" in attachment and "fileName" in attachment:
										url = attachment["url"]
										if not no_dupes or url not in visited_urls:
											if no_dupes:
												visited_urls.add(url)
											name, ext = os.path.splitext(
												attachment["fileName"]
											)
											url_name, url_ext = os.path.splitext(
												url.split("/")[-1].split("?")[0]
											)
											if not ext:
												ext = url_ext
											if not ext:
												ext = ".png"
											filename = sanitize_filename(name + ext)
											media_data.append(
												(url, timestamp, filename)
											)
				if not os.path.exists(output_subfolder):
					os.makedirs(output_subfolder)
				for media_url, timestamp_str, file_name in media_data:
					try:
						base_path = os.path.join(output_subfolder, file_name)
						final_path = base_path
						count = 1
						while os.path.exists(final_path):
							name, ext = os.path.splitext(base_path)
							final_path = f"{name}_{count:03d}{ext}"
							count += 1
						response = requests.get(media_url, stream=True)
						response.raise_for_status()
						with open(final_path, "wb") as media_file:
							for chunk in response.iter_content(chunk_size=8192):
								media_file.write(chunk)
						if timestamp_str:
							try:
								timestamp_str = timestamp_str.replace("Z", "+00:00")
								try:
									dt = datetime.fromisoformat(timestamp_str)
								except ValueError:
									dt = datetime.strptime(
										timestamp_str, "%Y-%m-%dT%H:%M:%S.%f%z"
									)
								if dt.tzinfo is None:
									dt = dt.replace(tzinfo=pytz.utc)
								timestamp = dt.timestamp()
								os.utime(final_path, (timestamp, timestamp))
							except ValueError as e:
								print(f"Timestamp error '{timestamp_str}': {e}")
						else:
							print(
								f"Downloaded '{os.path.basename(final_path)}' (no timestamp)."
							)
					except requests.exceptions.RequestException as e:
						print(f"Download error '{media_url}': {e}")
					except OSError as e:
						print(f"File error '{file_name}': {e}")
			except (FileNotFoundError, json.JSONDecodeError) as e:
				print(f"Error processing file '{filename}': {e}")
			except Exception as e:
				print(f"An unexpected error occurred processing '{filename}': {e}")


if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		description="Download media from Discord JSON exports."
	)
	parser.add_argument(
		"-i",
		"--input",
		default="json",
		help="Path to the folder containing JSON files.",
	)
	parser.add_argument(
		"-o",
		"--output",
		default="downloads",
		help="Output folder (default: downloaded_media).",
	)
	parser.add_argument(
		"--no-guild-icon",
		action="store_false",
		dest="guild_icon",
		help="Disable downloading guild icon.",
	)
	parser.add_argument(
		"--no-avatars",
		action="store_false",
		dest="avatars",
		help="Disable downloading user avatars.",
	)
	parser.add_argument(
		"--no-mentions",
		action="store_false",
		dest="mentions",
		help="Disable downloading avatars from mentions.",
	)
	parser.add_argument(
		"--no-reactions",
		action="store_false",
		dest="reactions",
		help="Disable downloading avatars from reaction users.",
	)
	parser.add_argument(
		"--no-reactions-emojis",
		action="store_false",
		dest="reactions_emojis",
		help="Disable downloading emojis from reaction users.",
	)
	parser.add_argument(
		"--no-inline-emojis",
		action="store_false",
		dest="inline_emojis",
		help="Disable downloading inline emojis.",
	)
	parser.add_argument(
		"--no-attachments",
		action="store_false",
		dest="attachments",
		help="Disable downloading attachments.",
	)
	parser.add_argument(
		"--no-dupes",
		action="store_true",
		help="Disable downloading duplicates.",
	)
	args = parser.parse_args()
	download_media_from_json(
		args.input,
		args.output,
		args.guild_icon,
		args.avatars,
		args.mentions,
		args.reactions,
		args.reactions_emojis,
		args.inline_emojis,
		args.attachments,
		args.no_dupes,
	)
