# Forgotten Realms Wiki → Obsidian Vault Converter

Convert the entire Forgotten Realms Wiki into a beautifully organised [Obsidian](https://obsidian.md) vault — complete with working `[[wikilinks]]`, ITS Theme infoboxes, and notes sorted into folders by category.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Content License: CC BY-SA 3.0](https://img.shields.io/badge/Content-CC--BY--SA--3.0-blue.svg)
![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-green.svg)

---

## What Does This Script Do?

This script takes the Forgotten Realms Wiki XML data dump and converts it into **68,000+ individual Markdown notes**, one per wiki article, ready to open in Obsidian. Each note includes:

- **Rich article content** — all the lore text, fully converted to Markdown
- **Working `[[wikilinks]]`** — links between notes that Obsidian can follow and graph
- **Redirect resolution** — links like `[[Bloodhand Hold]]` automatically point to the correct note (`[[Waterdeep|Bloodhand Hold]]`)
- **ITS Theme infoboxes** — place articles (cities, towns, regions etc.) display a Wikipedia-style infobox showing type, region, population, government, and more
- **YAML frontmatter** — each note has metadata Obsidian can search and filter
- **Organised subfolders** — notes are automatically sorted into folders like `Places/Settlements`, `Characters/Wizards & Mages`, `Creatures/Dragons`, `Deities & Religion`, and more

---

## Before You Start — What You'll Need

### 1. The FR Wiki XML Dump

You need to download the wiki data file first. This is a single large XML file (~390 MB) containing all the wiki's text content.

1. Go to: **https://forgottenrealms.fandom.com/wiki/Special:Statistics**
2. Scroll down to the **"Database dumps"** section
3. Click the date link next to **"Current pages"** to download
4. The file will be named something like `forgottenrealms_pages_current.xml.7z`
5. You'll need to **extract** the `.7z` file to get the `.xml` inside it:
   - **Windows**: Download [7-Zip](https://www.7-zip.org/) (free), right-click the file → "7-Zip" → "Extract Here"
   - **Mac**: Download [The Unarchiver](https://theunarchiver.com/) (free) from the App Store, then double-click the `.7z` file
   - **Linux**: Run `7z x forgottenrealms_pages_current.xml.7z` in terminal

### 2. Python 3.8 or Later

Python is the programming language this script runs on. Check if you already have it:

- Open **Terminal** (Mac/Linux) or **Command Prompt** (Windows) and type:
  ```
  python --version
  ```
  or
  ```
  python3 --version
  ```
- If you see `Python 3.8` or higher, you're good. Skip to Step 3.
- If you get an error or see Python 2.x, you need to install Python.

**Installing Python:**

| System | Instructions |
|--------|-------------|
| **Windows** | Go to [python.org/downloads](https://www.python.org/downloads/), download the latest installer. **Important:** on the first screen of the installer, tick the box that says **"Add Python to PATH"** before clicking Install. |
| **Mac** | Go to [python.org/downloads](https://www.python.org/downloads/) and download the macOS installer. Alternatively, if you have [Homebrew](https://brew.sh/), run `brew install python3` |
| **Linux** | Run `sudo apt install python3` (Ubuntu/Debian) or `sudo dnf install python3` (Fedora) |

After installing, **close and reopen** your terminal/command prompt window.

### 3. Obsidian (with ITS Theme — optional but recommended)

- Download Obsidian free from [obsidian.md](https://obsidian.md)
- The script generates ITS Theme infoboxes for place articles. To see these render correctly, install the **ITS Theme**:
  - In Obsidian: Settings → Appearance → Themes → Browse → search "ITS" → Install
- If you don't use ITS Theme the notes still work perfectly — the infobox just appears as a standard callout block

---

## Installation

### Step 1 — Download the Script

Click the green **"Code"** button at the top of this GitHub page, then click **"Download ZIP"**. Extract the ZIP file somewhere on your computer — for example:

- **Windows**: `C:\FR-Wiki-Tool\`
- **Mac/Linux**: `~/Documents/FR-Wiki-Tool/`

You only need the file `fr_to_obsidian.py`.

### Step 2 — Install the Optional Dependency

The script works without this, but installing `tqdm` adds a progress bar so you can see how far along the conversion is.

Open Terminal (Mac/Linux) or Command Prompt (Windows) and run:

```
python -m pip install tqdm
```

or on Mac/Linux if that doesn't work:

```
python3 -m pip install tqdm
```

---

## Running the Script

Open **Terminal** (Mac/Linux) or **Command Prompt** (Windows).

### Windows

```
python fr_to_obsidian.py --input "C:\path\to\forgottenrealms_pages_current.xml" --output "C:\path\to\FR-Vault"
```

**Real example** (adjust paths to match where your files are):
```
python fr_to_obsidian.py --input "D:\Downloads\forgottenrealms_pages_current.xml" --output "D:\Obsidian\FR-Vault"
```

### Mac

```
python3 fr_to_obsidian.py --input "/path/to/forgottenrealms_pages_current.xml" --output "/path/to/FR-Vault"
```

**Real example**:
```
python3 fr_to_obsidian.py --input ~/Downloads/forgottenrealms_pages_current.xml --output ~/Documents/FR-Vault
```

### Linux

```
python3 fr_to_obsidian.py --input /path/to/forgottenrealms_pages_current.xml --output /path/to/FR-Vault
```

---

## How Long Does It Take?

The script makes **three passes** through the XML file:

| Pass | What it does | Time (approx) |
|------|-------------|---------------|
| Pass 1 | Builds a map of all 14,000+ redirects | ~1 min |
| Pass 2 | Counts articles | ~1 min |
| Pass 3 | Converts and writes all notes | ~5–8 min |

**Total: around 7–10 minutes** on a typical computer. The output is ~68,000 notes.

---

## Opening the Vault in Obsidian

1. Open Obsidian
2. Click **"Open folder as vault"**
3. Navigate to and select the output folder you specified (e.g. `FR-Vault`)
4. Obsidian will index all the notes — this takes a minute or two the first time
5. Press `Ctrl+G` (Windows/Linux) or `Cmd+G` (Mac) to open the **Graph View** — with 68,000 linked notes it's spectacular

---

## Output Structure

The vault is organised into subfolders automatically:

```
FR-Vault/
├── Places/
│   ├── Settlements/        (cities, towns, villages)
│   ├── Regions & Nations/  (kingdoms, empires, duchies)
│   ├── Geography/          (mountains, forests, rivers, seas)
│   ├── Fortresses & Ruins/ (castles, dungeons, keeps)
│   ├── Buildings/          (temples, inns, shops)
│   ├── Planes/             (Abyss, Astral Plane, etc.)
│   └── Roads & Paths/      (trade routes, trails)
├── Characters/
│   ├── Wizards & Mages/
│   ├── Warriors/
│   ├── Priests & Paladins/
│   ├── Rogues/
│   ├── Rulers & Nobles/
│   ├── Rangers & Druids/
│   ├── Bards/
│   └── Monks/
├── Creatures/
│   ├── Dragons/
│   ├── Undead/
│   ├── Elves/
│   ├── Dwarves/
│   ├── Fiends/
│   └── ... (more)
├── Deities & Religion/
├── Organizations/
├── Magic/
│   ├── Spells/
│   ├── Items & Artifacts/
│   └── Lore/
├── History/
│   ├── Battles & Wars/
│   └── Events/
├── Language & Culture/
└── Miscellaneous/
```

---

## Example Note — Waterdeep

Here's what a generated note looks like in Obsidian with the ITS Theme:

```markdown
---
title: "Waterdeep"
category: Settlements
source_url: "https://forgottenrealms.fandom.com/wiki/Waterdeep"
attribution: "Forgotten Realms Wiki (forgottenrealms.fandom.com), CC BY-SA 3.0"
location_type: "Metropolis"
region: "Northwest Faerûn, Sword Coast North"
government: "Council"
tags:
  - forgotten-realms
  - settlements
---
# Waterdeep

> [!infobox|right]+
> # Waterdeep
> ###### Details
> | | |
> |---|---|
> | **Type** | Metropolis |
> | **Region** | Northwest Faerûn, Sword Coast North |
> | **Government** | Council |
> | **Ruler** | Lords of Waterdeep |

**Waterdeep**, also known as **the City of Splendors**, was the most 
important and influential city in [[Northwest Faerûn|the North]] and 
perhaps in all [[Faerûn]]...
```

---

## Troubleshooting

**"python is not recognized" (Windows)**
→ Python wasn't added to PATH during installation. Reinstall Python and make sure to tick **"Add Python to PATH"** on the first screen.

**"No such file or directory" error**
→ Check your file paths. On Windows, make sure you're using quote marks around paths that contain spaces: `"D:\My Files\example.xml"`

**The script seems frozen / no output**
→ It's working — the first two passes have no progress bar. Wait a few minutes. If you installed `tqdm`, you'll see a progress bar during the third pass.

**"ModuleNotFoundError: No module named 'tqdm'"**
→ Run `python -m pip install tqdm` then try again. The script also works without it — just no progress bar.

**Notes are missing for some places**
→ Some wiki pages have very little content (stubs). These are skipped to avoid empty notes. The vast majority of significant locations are included.

**The infobox isn't rendering correctly**
→ Make sure you have the ITS Theme installed in Obsidian. Go to Settings → Appearance → Themes and search for "ITS".

---

## Frequently Asked Questions

**Can I run this more than once?**
Yes. If a note already exists at the output path, the script adds a number suffix (`Waterdeep_1.md`) rather than overwriting. Delete the output folder first if you want a fresh run.

**Will this work with future XML dumps?**
Yes. The FR Wiki releases updated XML dumps periodically. You can re-run the script against a newer dump to get updated notes.

**Does it download images?**
No. The XML dump doesn't contain images, and downloading them separately is a complex process. The notes reference image filenames but don't embed them. Images can be added manually if desired.

**Is this legal?**
The FR Wiki text is licensed under CC BY-SA 3.0 which permits this use provided attribution is given — the script automatically adds attribution to every note. See the Licensing section below for full details.

**Can I share the generated vault?**
Yes, provided you share it under CC BY-SA 3.0 and include attribution to the Forgotten Realms Wiki. See the Licensing section.

---

## Licensing

This project has two separate licences covering two different things.

### The Script Code
`fr_to_obsidian.py` is released under the **MIT License**. You are free to use, modify, and distribute it for any purpose. See `LICENSE-CODE` for the full terms.

### The Generated Vault Content
The notes produced by this script are derivative works of the **Forgotten Realms Wiki** (forgottenrealms.fandom.com), which is licensed under the **Creative Commons Attribution-Share Alike 3.0 (CC BY-SA 3.0)** license.

This means:
- You may use and share the generated vault freely
- You must give credit to the Forgotten Realms Wiki (the script does this automatically in each note's frontmatter)
- If you share the vault publicly, you must do so under the same CC BY-SA 3.0 license

The script automatically adds the following attribution to every generated note:
> *"Forgotten Realms Wiki (forgottenrealms.fandom.com), CC BY-SA 3.0"*

### Wizards of the Coast Fan Content Policy
The Forgotten Realms setting and all associated lore is the intellectual property of Wizards of the Coast LLC. This tool and any content it generates falls under the [Wizards of the Coast Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy).

> *This tool uses trademarks and/or copyrights owned by Wizards of the Coast LLC, used under the Wizards of the Coast Fan Content Policy. We are expressly prohibited from charging you to use or access this content. This tool is not published, endorsed, or specifically approved by Wizards of the Coast.*

**Generated vaults are for personal, non-commercial use only.**

---

## Contributing

Found a bug? Have an improvement? Pull requests are welcome. Some areas that could use work:

- Better category detection for edge cases
- Support for additional infobox types
- Image downloading support
- Support for other Fandom/MediaWiki wikis

Please open an issue first to discuss any significant changes.

---

## Acknowledgements

- **The Forgotten Realms Wiki community** — for their incredible years of work documenting the Realms
- **Paizo / Wizards of the Coast** — for the Forgotten Realms setting
- **SlRvb** — for the [ITS Theme](https://github.com/SlRvb/Obsidian--ITS-Theme) and infobox callout design
- **WikiTeam** — for their work on wiki preservation tools
