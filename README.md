# Dimage

Downloads all media assets from JSON files generated by [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter).

## ⚙️ Functionality

-   Parses `.json` export files from DiscordChatExporter.
-   Downloads guild icons, user avatars, mention avatars, reaction avatars, custom emojis (reaction and inline), and message attachments.
-   Organizes downloaded media into subdirectories named after the source channel or DM.
-   Sets the local file modification timestamp to match the original Discord message timestamp.
-   Allows skipping duplicate URLs to prevent redundant downloads and reduce execution time.
-   Provides granular control over which asset types are downloaded via command-line flags.
-   Allows skipping downloads based on file extension.
-   Provides a mode to set timestamps on existing files without downloading.

## 🚀 Installation Steps

1. **Set up a Conda environment**:
	```bash
	conda create --name Dimage python=3.10 -y
	conda activate Dimage
	```

2. **Clone the repository**:
	```bash
	git clone https://github.com/Inc44/Dimage.git
	```

3. **Navigate into the project directory**:
	```bash
	cd Dimage
	```

4. **Install dependencies**:
	```bash
	pip install requests pytz
	```

5. **Launch the application**:
	```bash
	python -OO main.py --no-guild-icon --no-avatars --no-mentions --no-reactions --no-reactions-emojis --no-inline-emojis --no-attachments --no-dupes --skip svg --timestamp-only
	```

## 🛠️ Usage

After launching, the toolbar at the top displays icons for various tools. Hover over an icon to see its description. Click to activate the respective tool.

## 🎨 Arguments

| Argument                | Description                                                              |
| ----------------------- | ------------------------------------------------------------------------ |
| `-i, --input <path>`    | Specifies the input directory containing `.json` files. Default: `json`. |
| `-o, --output <path>`   | Specifies the root output directory for downloads. Default: `downloads`. |
| `--no-guild-icon`       | Disables downloading the guild/server icon.                              |
| `--no-avatars`          | Disables downloading message author avatars.                             |
| `--no-mentions`         | Disables downloading avatars of mentioned users.                         |
| `--no-reactions`        | Disables downloading avatars of users who added a reaction.              |
| `--no-reactions-emojis` | Disables downloading custom emojis used in reactions.                    |
| `--no-inline-emojis`    | Disables downloading custom emojis used inline in messages.              |
| `--no-attachments`      | Disables downloading message attachments.                                |
| `--no-dupes`            | Disables downloading duplicate files.                                    |
| `--skip <exts>`         | Skips downloading files with specified comma-separated extensions.       |
| `--timestamp-only`      | Sets timestamps on existing files.                                       |

## 📜 License

[![MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](https://opensource.org/licenses/MIT)

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🤝 Support

[![BuyMeACoffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/xamituchido)
[![Ko-Fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/inc44)
[![Patreon](https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/Inc44)