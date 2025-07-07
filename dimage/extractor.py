from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple
import os

from .config import Config

MediaItem = Tuple[str, Optional[str], str, str]


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
	filename = str(item_id) + ext
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
				filename = attachment["fileName"]
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
