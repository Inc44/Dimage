from __future__ import annotations
from typing import Set
import argparse


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
