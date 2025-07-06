from dateutil import parser
import argparse
import json
import os
import re
import requests


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
	skip="",
	timestamp_only=False,
	organize=False,
):
	os.makedirs(input_folder, exist_ok=True)
	if not timestamp_only:
		os.makedirs(output_folder, exist_ok=True)
	if organize:
		icons_path = os.path.join(output_folder, "icons")
		avatars_path = os.path.join(output_folder, "avatars")
		emojis_path = os.path.join(output_folder, "emojis")
		channels_path = os.path.join(output_folder, "channels")
		if not timestamp_only:
			os.makedirs(icons_path, exist_ok=True)
			os.makedirs(avatars_path, exist_ok=True)
			os.makedirs(emojis_path, exist_ok=True)
			os.makedirs(channels_path, exist_ok=True)
	visited_urls = set()
	skipped_extensions = {ext.strip().lower() for ext in skip.split(",") if ext.strip()}
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
						file_ext = os.path.splitext(filename)[1].lower()
						if file_ext not in skipped_extensions:
							media_data.append(
								(url, data.get("exportedAt"), filename, "icon")
							)
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
									file_ext = os.path.splitext(filename)[1].lower()
									if file_ext not in skipped_extensions:
										media_data.append(
											(url, timestamp, filename, "avatar")
										)
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
											file_ext = os.path.splitext(filename)[
												1
											].lower()
											if file_ext not in skipped_extensions:
												media_data.append(
													(url, timestamp, filename, "avatar")
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
													file_ext = os.path.splitext(
														filename
													)[1].lower()
													if (
														file_ext
														not in skipped_extensions
													):
														media_data.append(
															(
																url,
																timestamp,
																filename,
																"avatar",
															)
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
												file_ext = os.path.splitext(filename)[
													1
												].lower()
												if file_ext not in skipped_extensions:
													media_data.append(
														(
															url,
															timestamp,
															filename,
															"emoji",
														)
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
											file_ext = os.path.splitext(filename)[
												1
											].lower()
											if file_ext not in skipped_extensions:
												media_data.append(
													(url, timestamp, filename, "emoji")
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
											file_ext = os.path.splitext(filename)[
												1
											].lower()
											if file_ext not in skipped_extensions:
												media_data.append(
													(
														url,
														timestamp,
														filename,
														"attachment",
													)
												)
				if not organize and not timestamp_only:
					os.makedirs(output_subfolder, exist_ok=True)
				for media_url, timestamp_str, file_name, media_type in media_data:
					try:
						target_folder = ""
						if organize:
							if media_type == "icon":
								target_folder = icons_path
							elif media_type == "avatar":
								target_folder = avatars_path
							elif media_type == "emoji":
								target_folder = emojis_path
							elif media_type == "attachment":
								channel_specific_path = os.path.join(
									channels_path, sanitize_filename(json_filename)
								)
								if not timestamp_only:
									os.makedirs(channel_specific_path, exist_ok=True)
								target_folder = channel_specific_path
						else:
							target_folder = output_subfolder
						base_path = os.path.join(target_folder, file_name)
						final_path = ""
						if timestamp_only:
							if os.path.exists(base_path):
								final_path = base_path
							else:
								continue
						else:
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
								dt = parser.parse(timestamp_str)
								timestamp = dt.timestamp()
								os.utime(final_path, (timestamp, timestamp))
							except (parser.ParserError, ValueError) as e:
								print(f"Timestamp error '{timestamp_str}': {e}")
						elif not timestamp_only:
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
		args.skip,
		args.timestamp_only,
		args.organize,
	)
