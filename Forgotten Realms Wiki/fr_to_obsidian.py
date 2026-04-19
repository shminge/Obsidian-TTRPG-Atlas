#!/usr/bin/env python3
"""
Forgotten Realms Wiki XML -> Obsidian Vault Converter
=====================================================
Converts the FR Wiki XML dump into individual Obsidian .md notes with:
  - YAML frontmatter (including infobox fields for places)
  - [[wikilinks]] preserved and redirects resolved
  - Subfolders by category
  - Place infobox data extracted so no content is lost

Usage:
    python fr_to_obsidian.py --input forgottenrealms_pages_current.xml --output FR-Vault

Requirements:
    python -m pip install tqdm   (optional, for progress bar)
"""

import re
import json
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# ---------------------------------------------------------------------------
# Skip lists
# ---------------------------------------------------------------------------
SKIP_PREFIXES = (
    'Talk:', 'User:', 'User talk:', 'Forgotten Realms Wiki:',
    'Forgotten Realms Wiki talk:', 'File:', 'File talk:', 'MediaWiki:',
    'MediaWiki talk:', 'Template:', 'Template talk:', 'Help:', 'Help talk:',
    'Category talk:', 'Portal:', 'Portal talk:', 'Module:', 'Module talk:',
    'Draft:', 'Map:',
)

# ---------------------------------------------------------------------------
# Place infobox templates (used for data extraction + categorisation)
# ---------------------------------------------------------------------------
PLACE_INFOBOX_NAMES = {
    'location', 'building', 'road', 'settlement', 'region',
    'nation', 'body of water', 'forest', 'mountain', 'dungeon',
    'plane', 'island', 'sea', 'cave', 'ruins',
}

# ALL infobox types to strip from wikitext before markdown conversion
# (prevents raw infobox markup leaking into note body)
ALL_INFOBOX_NAMES = PLACE_INFOBOX_NAMES | {
    'person', 'creature', 'item', 'spell', 'organization', 'deity',
    'class', 'race', 'book', 'bookiu', 'computer game', 'video game',
    'boardgame', 'sourcebook', 'adventure', 'novel', 'comic',
    'magic item', 'weapon', 'armor', 'vehicle', 'ship', 'deity',
    'disease', 'poison', 'trap', 'event', 'war', 'battle',
    'language', 'calendar', 'currency', 'food', 'drink',
    'roll of years', 'members', 'member', 'archivebox',
    'ga', 'stub', 'cleanup', 'delete', 'merge', 'disambig',
    'otheruses4', 'otheruses', 'for', 'redirect', 'main',
    'see also', 'tl', 'signature', 'cite book', 'cite web',
    'cite dragon', 'cite organized play', 'cite game',
    'information', 'category jump', 'religion category jump',
    'creature category jump', 'forum post', 'refonly',
}

# Infobox fields to pull into frontmatter
PLACE_FIELDS = {
    'type':        'location_type',
    'region':      'region',
    'size':        'size',
    'races':       'races',
    'religion':    'religion',
    'government':  'government',
    'ruler':       'ruler',
    'imports':     'imports',
    'exports':     'exports',
    'population':  'population',
    'population1': 'population',
    'aliases':     'aliases',
    'demonym':     'demonym',
    'languages':   'languages',
    'alignment':   'alignment',
}

# ---------------------------------------------------------------------------
# Category detection rules
# ---------------------------------------------------------------------------
CATEGORY_RULES = [
    (r'\bcity\b|\btown\b|\bvillage\b|\bsettlement\b|\bport\b|\bharbou?r\b|\bmetropolis\b|\bhamlet\b|\bborough\b', 'Places/Settlements'),
    (r'\bfortress\b|\bcastle\b|\bcitadel\b|\btower\b|\bdungeon\b|\bruins?\b|\bkeep\b|\bhold\b|\bstronghold\b|\bbastion\b', 'Places/Fortresses & Ruins'),
    (r'\bforest\b|\bwood\b|\bmountain\b|\brange\b|\briver\b|\blake\b|\bsea\b|\bocean\b|\bdesert\b|\bplain\b|\bswamp\b|\bmarsh\b|\bjungle\b|\btundra\b|\bvalley\b|\bisle\b|\bisland\b', 'Places/Geography'),
    (r'\bregion\b|\bkingdom\b|\bempire\b|\bnation\b|\bcountry\b|\brealm\b|\bprovince\b|\bterritory\b|\blands?\b|\bduchy\b|\bfief\b|\bbarony\b', 'Places/Regions & Nations'),
    (r'\bplane\b|\bdimension\b|\babyss\b|\bhell\b|\bheaven\b|\boutlands\b|\betheral\b|\bastral\b|\blimbo\b|\bmechanus\b', 'Places/Planes'),
    (r'\binn\b|\btavern\b|\bshop\b|\bguild ?hall\b|\btemple\b|\bsanctuary\b|\bshrine\b|\bpalace\b|\bmanor\b|\bcathedral\b|\bacademy\b|\blibrary\b|\bmarket\b', 'Places/Buildings'),
    (r'\broad\b|\bpath\b|\bhighway\b|\btrail\b|\bpass\b|\bbridge\b|\bgate\b|\bway\b', 'Places/Roads & Paths'),
    (r'\bwizard\b|\bsorcerer\b|\barchmage\b|\bmage\b|\bwarlock\b|\bspellcaster\b', 'Characters/Wizards & Mages'),
    (r'\bpaladin\b|\bcleric\b|\bpriest(?:ess)?\b|\bhigh priest\b|\bchaplain\b', 'Characters/Priests & Paladins'),
    (r'\bfighter\b|\bwarrior\b|\bbarbarian\b|\bknight\b|\bsoldier\b|\bmercenary\b|\bberserker\b', 'Characters/Warriors'),
    (r'\bthief\b|\brogue\b|\bassassin\b|\bspy\b|\bshadow\b|\bpickpocket\b', 'Characters/Rogues'),
    (r'\bking\b|\bqueen\b|\bprince\b|\bprincess\b|\bruler\b|\bmonarch\b|\bemperor\b|\blord\b|\blady\b|\bsultan\b|\bpharaoh\b|\bduke\b|\bduchess\b', 'Characters/Rulers & Nobles'),
    (r'\bdruid\b|\branger\b|\bhunter\b|\bscout\b|\btracker\b', 'Characters/Rangers & Druids'),
    (r'\bbard\b|\bskald\b|\bpoet\b|\bminstrel\b', 'Characters/Bards'),
    (r'\bmonk\b|\bascetic\b', 'Characters/Monks'),
    (r'\bdragon\b|\bdracolich\b|\bwyrm\b|\bdrake\b|\bwyvern\b', 'Creatures/Dragons'),
    (r'\bundead\b|\bvampire\b|\blich\b|\bzombie\b|\bskeleton\b|\bwight\b|\bghoul\b|\bspectre\b|\bwraith\b|\bbanshee\b|\brevenant\b', 'Creatures/Undead'),
    (r'\bdemon\b|\bdevil\b|\bfiend\b|\btanar.ri\b|\bbaatezu\b|\bbalor\b|\bsuccubus\b', 'Creatures/Fiends'),
    (r'\bangel\b|\bceles?tial\b|\barchon\b|\bplanatar\b|\bdeva\b|\bsolars?\b', 'Creatures/Celestials'),
    (r'\bdrow\b|\bsun elf\b|\bmoon elf\b|\bwood elf\b|\bwild elf\b|\bsea elf\b|\bstar elf\b', 'Creatures/Elves'),
    (r'\belf\b|\belves\b', 'Creatures/Elves'),
    (r'\bshield dwarf\b|\bgold dwarf\b|\bdeep dwarf\b|\bduergar\b', 'Creatures/Dwarves'),
    (r'\bdwarf\b|\bdwarves\b', 'Creatures/Dwarves'),
    (r'\bhalfling\b|\bhalf-?ling\b|\blightfoot\b|\bstrongfoot\b', 'Creatures/Halflings'),
    (r'\bgnome\b|\brock gnome\b|\bdeep gnome\b|\bsvirfneblin\b', 'Creatures/Gnomes'),
    (r'\bhalf-?orc\b|\borc\b|\borcs\b|\bgruumsh\b', 'Creatures/Orcs'),
    (r'\bgoblin\b|\bhobgoblin\b|\bbugbear\b', 'Creatures/Goblinoids'),
    (r'\bgiant\b|\btroll\b|\bogre\b|\bminotaur\b|\bgnoll\b|\byuan-ti\b|\bkobold\b|\blizardfolk\b|\btroglodyte\b', 'Creatures/Monsters'),
    (r'\bhuman\b|\bhumans\b', 'Creatures/Humans'),
    (r'\btiefling\b|\baasimar\b|\bgensai\b|\bhalf-?elf\b|\bhalf-?dragon\b', 'Creatures/Planetouched'),
    (r'\bgod\b|\bgoddess\b|\bdeity\b|\bdivine\b|\bpantheon\b|\bportfolio\b|\bworship\b|\bfaith\b|\bchurch of\b|\bavatar\b|\baspect\b', 'Deities & Religion'),
    (r'\bguild\b|\border\b|\bcult\b|\bbrotherhood\b|\bsisterhood\b|\bsociety\b|\borganization\b|\bfaction\b|\bcabal\b|\bcouncil\b|\bleague\b|\balliance\b|\bclan\b|\btribe\b', 'Organizations'),
    (r'\bspell\b|\bincantation\b|\bcantrip\b|\bconjuration\b|\bevocation\b|\billusion\b|\bnecromancy\b|\bdivination\b|\btransmutation\b|\benchantment\b|\babjuration\b', 'Magic/Spells'),
    (r'\bartifact\b|\bmagic item\b|\bmagical item\b|\bwondrous\b|\benchanted\b|\bsword of\b|\bstaff of\b|\bring of\b|\bamulet of\b|\bwand of\b|\bscroll of\b', 'Magic/Items & Artifacts'),
    (r'\bweave\b|\bspellplague\b|\bshadowweave\b|\bmystra\b', 'Magic/Lore'),
    (r'\bbattle of\b|\bsiege of\b|\bwar of\b|\bcrusade\b|\binvasion\b|\bconquest\b', 'History/Battles & Wars'),
    (r'\bevent\b|\bcatastroph\b|\bcalamity\b|\bearthfall\b|\bspellplague\b|\bsundering\b|\btime of troubles\b', 'History/Events'),
    (r'\blanguage\b|\btongue\b|\bscript\b|\balphabet\b|\bdialect\b', 'Language & Culture'),
]

FALLBACK_FOLDER = 'Miscellaneous'
BASE_URL = 'https://forgottenrealms.fandom.com/wiki/'


# ---------------------------------------------------------------------------
# Infobox extraction
# ---------------------------------------------------------------------------

def clean_field_value(val: str) -> str:
    """Strip refs, nested templates, HTML from an infobox value."""
    val = re.sub(r'<ref[^>]*/>', '', val)
    val = re.sub(r'<ref[^>]*>.*?</ref>', '', val, flags=re.DOTALL)
    val = re.sub(r'<br\s*/?>', ', ', val, flags=re.IGNORECASE)
    val = re.sub(r'<[^>]+>', '', val)
    for _ in range(4):
        val = re.sub(r'\{\{[^{}]*\}\}', '', val)
    val = val.strip(' |,;')
    return val.strip()


# Templates that are navigation/meta and should be skipped when
# looking for the real content infobox
META_TEMPLATES = {
    'otheruses4', 'otheruses', 'for', 'main', 'see also', 'redirect',
    'ga', 'stub', 'cleanup', 'delete', 'merge', 'disambig',
    'tl', 'signature', 'archivebox', 'refonly', 'forum post',
    'cite book', 'cite web', 'cite dragon', 'cite organized play', 'cite game',
    'information', 'category jump', 'religion category jump',
    'creature category jump', 'roll of years', 'members', 'member',
}

# Content infobox types (place + character + other content)
CONTENT_INFOBOX_NAMES = ALL_INFOBOX_NAMES - META_TEMPLATES


def extract_infobox(wikitext: str) -> tuple:
    """
    Extract the first recognised content infobox, skipping meta/navigation templates.
    Returns (infobox_type_str, dict_of_fields) or (None, {}).
    Uses depth-counting to handle nested braces correctly.
    """
    pattern = r'\{\{(' + '|'.join(re.escape(n) for n in CONTENT_INFOBOX_NAMES) + r')\s*[\n\r|]'
    m = re.search(pattern, wikitext, re.IGNORECASE)
    if not m:
        return None, {}

    infobox_type = m.group(1).strip().lower()
    # For non-place infoboxes, just return the type — no field extraction needed
    if infobox_type not in PLACE_INFOBOX_NAMES:
        return infobox_type, {}

    start = m.end()

    # Walk to find the matching }}
    depth = 1
    i = start
    while i < len(wikitext) and depth > 0:
        if wikitext[i:i+2] == '{{':
            depth += 1
            i += 2
        elif wikitext[i:i+2] == '}}':
            depth -= 1
            if depth == 0:
                break
            i += 2
        else:
            i += 1

    infobox_body = wikitext[start:i]

    # Parse | key = value pairs
    fields = {}
    field_pattern = re.compile(r'^\|\s*([^=|\n]+?)\s*=[ \t]*(.*)$', re.MULTILINE)
    for fm in field_pattern.finditer(infobox_body):
        key = fm.group(1).strip().lower().replace(' ', '_')
        val = clean_field_value(fm.group(2))
        if val and val not in ('-', 'N/A', 'n/a', ''):
            if key not in fields:  # first value wins
                fields[key] = val

    return infobox_type, fields


def strip_place_infoboxes(wikitext: str) -> str:
    """Remove place infobox blocks from wikitext (we already extracted the data)."""
    pattern = r'\{\{(' + '|'.join(re.escape(n) for n in ALL_INFOBOX_NAMES) + r')\s*[\n\r|]'
    result = wikitext
    while True:
        m = re.search(pattern, result, re.IGNORECASE)
        if not m:
            break
        start = m.start()
        i = m.end()
        depth = 1
        while i < len(result) and depth > 0:
            if result[i:i+2] == '{{':
                depth += 1
                i += 2
            elif result[i:i+2] == '}}':
                depth -= 1
                if depth == 0:
                    i += 2
                    break
                i += 2
            else:
                i += 1
        result = result[:start] + result[i:]
    return result


# ---------------------------------------------------------------------------
# Wikitext -> Markdown conversion
# ---------------------------------------------------------------------------

def normalise_title(title: str) -> str:
    """Normalise for redirect lookup."""
    title = unquote(title)
    title = title.replace('_', ' ')
    title = title.split('#')[0]
    return title.strip().lower()


def convert_wikitext_to_markdown(wikitext: str) -> str:
    """Convert wikitext markup to Markdown, preserving [[wikilinks]]."""

    # Remove <ref> tags
    wikitext = re.sub(r'<ref[^>]*>.*?</ref>', '', wikitext, flags=re.DOTALL)
    wikitext = re.sub(r'<ref[^/]*/>', '', wikitext)

    # Remove HTML comments
    wikitext = re.sub(r'<!--.*?-->', '', wikitext, flags=re.DOTALL)

    # Save [[wikilinks]] so template removal doesn't eat them
    links = []

    def save_link(m):
        links.append(m.group(0))
        return f'\x00LINK{len(links)-1}\x00'

    wikitext = re.sub(r'\[\[[^\]]+\]\]', save_link, wikitext)

    # Remove templates (multiple passes for nesting)
    for _ in range(6):
        wikitext = re.sub(r'\{\{[^{}]*\}\}', '', wikitext)
    wikitext = re.sub(r'\{\{|\}\}', '', wikitext)

    # Restore wikilinks
    for i, link in enumerate(links):
        wikitext = wikitext.replace(f'\x00LINK{i}\x00', link)

    # Remove File/Image/Category/language links
    wikitext = re.sub(r'\[\[(?:File|Image|Media):[^\]]*\]\]', '', wikitext, flags=re.IGNORECASE)
    wikitext = re.sub(r'\[\[Category:[^\]]*\]\]', '', wikitext, flags=re.IGNORECASE)
    wikitext = re.sub(r'\[\[[a-z]{2,3}:[^\]]*\]\]', '', wikitext)

    # External links: keep display text
    wikitext = re.sub(r'\[https?://[^\s\]]+\s+([^\]]+)\]', r'\1', wikitext)
    wikitext = re.sub(r'\[https?://[^\]]+\]', '', wikitext)

    # Remove trailing sections
    wikitext = re.sub(
        r'^(==+)\s*(References|See also|External links|Gallery|Appendix|Notes|Further reading|Appearances)\s*\1.*',
        '', wikitext, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE
    )

    # Headings
    for lvl in range(6, 1, -1):
        eq = '=' * lvl
        md_hashes = '#' * (lvl - 1)
        wikitext = re.sub(
            rf'^{eq}\s*(.+?)\s*{eq}\s*$',
            rf'{md_hashes} \1',
            wikitext,
            flags=re.MULTILINE
        )

    # Bold and italic (using character repetition to avoid quote issues)
    wikitext = re.sub(r"'{3}(.+?)'{3}", r'**\1**', wikitext)
    wikitext = re.sub(r"'{2}(.+?)'{2}", r'*\1*',   wikitext)

    # Lists
    wikitext = re.sub(r'^\*\*\*\s*', '      - ', wikitext, flags=re.MULTILINE)
    wikitext = re.sub(r'^\*\*\s*',   '   - ',    wikitext, flags=re.MULTILINE)
    wikitext = re.sub(r'^\*\s*',     '- ',       wikitext, flags=re.MULTILINE)
    wikitext = re.sub(r'^###\s*',    '      1. ', wikitext, flags=re.MULTILINE)
    wikitext = re.sub(r'^##\s*',     '   1. ',   wikitext, flags=re.MULTILINE)
    wikitext = re.sub(r'^#\s*',      '1. ',      wikitext, flags=re.MULTILINE)

    # Definition lists
    wikitext = re.sub(r'^;\s*(.+)', r'**\1**', wikitext, flags=re.MULTILINE)
    wikitext = re.sub(r'^:\s*',     '> ',      wikitext, flags=re.MULTILINE)

    # Gallery blocks and remaining HTML
    wikitext = re.sub(r'<gallery[^>]*>.*?</gallery>', '', wikitext, flags=re.DOTALL | re.IGNORECASE)
    wikitext = re.sub(r'<[^>]+>', '', wikitext)

    # Clean up blank lines
    wikitext = re.sub(r'\n{3,}', '\n\n', wikitext)

    return wikitext.strip()


def sanitize_link_target(page: str) -> str:
    """
    Sanitize a page name to match the filename on disk.
    Replaces characters invalid in filenames (/ : * ? etc) with hyphens,
    matching sanitize_filename() used when writing notes.
    Critical for links like [[Waterdeep/Dock Ward]] which must become
    [[Waterdeep-Dock Ward]] to match the file Waterdeep-Dock Ward.md.
    """
    safe = re.sub(r'[\\/:*?"<>|]', '-', page)
    safe = re.sub(r'-+', '-', safe).strip(' -.')
    return safe[:200]


def resolve_wikilinks(text: str, redirect_map: dict) -> str:
    """Resolve redirect links and normalise wikilinks."""

    def replace_link(m):
        inner = m.group(1).strip()

        if '|' in inner:
            page_part, display = inner.split('|', 1)
            display = display.strip()
        else:
            page_part = inner
            display = None

        norm = normalise_title(page_part)
        # Clean underscores/anchors for display text
        clean_page = page_part.replace('_', ' ').split('#')[0].strip()
        # Sanitize to match actual filename (/ -> -, etc.)
        safe_page = sanitize_link_target(clean_page)
        target = redirect_map.get(norm)

        if target:
            # Redirect resolved — sanitize the target to match its filename
            safe_target = sanitize_link_target(target)
            if display:
                return f'[[{safe_target}|{display}]]'
            elif clean_page.lower() != target.lower():
                return f'[[{safe_target}|{clean_page}]]'
            else:
                return f'[[{safe_target}]]'
        else:
            # No redirect — use sanitized page name so link matches file on disk
            if display:
                return f'[[{safe_page}|{display}]]'
            elif safe_page != page_part:
                return f'[[{safe_page}]]'
            else:
                return m.group(0)

    return re.sub(r'\[\[([^\]]+)\]\]', replace_link, text)


# ---------------------------------------------------------------------------
# Category & filename helpers
# ---------------------------------------------------------------------------

def detect_category(title: str, content: str,
                    infobox_type: str = None, infobox_fields: dict = None) -> tuple:
    """Return (subfolder_path, category_label)."""

    if infobox_type:
        itype = infobox_type.lower()
        loc_type = (infobox_fields or {}).get('type', '').lower()

        # Non-place infoboxes — route to appropriate category by infobox type
        if itype == 'person':
            # Person infobox — use keyword matching on content for sub-category
            search_text = (title + ' ' + content[:800]).lower()
            for pattern, folder in CATEGORY_RULES:
                if re.search(pattern, search_text, re.IGNORECASE):
                    label = folder.split('/')[-1]
                    if folder.startswith('Characters/'):
                        return folder, label
            return 'Characters/Rulers & Nobles', 'Rulers & Nobles'
        if itype == 'creature':
            search_text = (title + ' ' + content[:800]).lower()
            for pattern, folder in CATEGORY_RULES:
                if re.search(pattern, search_text, re.IGNORECASE):
                    label = folder.split('/')[-1]
                    if folder.startswith('Creatures/'):
                        return folder, label
            return 'Creatures/Monsters', 'Monsters'
        if itype == 'deity':
            return 'Deities & Religion', 'Deities & Religion'
        if itype == 'organization':
            return 'Organizations', 'Organizations'
        if itype in ('spell',):
            return 'Magic/Spells', 'Spells'
        if itype in ('item', 'magic item', 'weapon', 'armor'):
            return 'Magic/Items & Artifacts', 'Items & Artifacts'

        # Place infoboxes
        if itype == 'road':
            return 'Places/Roads & Paths', 'Roads & Paths'
        if itype == 'building':
            return 'Places/Buildings', 'Buildings'

        if itype in ('location', 'settlement', 'region', 'nation',
                     'body of water', 'forest', 'mountain', 'dungeon',
                     'plane', 'island', 'sea', 'cave', 'ruins'):

            if any(t in loc_type for t in ('city', 'town', 'village', 'settlement', 'hamlet', 'metropolis', 'borough')):
                return 'Places/Settlements', 'Settlements'
            if any(t in loc_type for t in ('fortress', 'castle', 'keep', 'tower', 'dungeon', 'ruins', 'stronghold', 'citadel')):
                return 'Places/Fortresses & Ruins', 'Fortresses & Ruins'
            if any(t in loc_type for t in ('forest', 'mountain', 'river', 'lake', 'sea', 'ocean', 'desert', 'plain', 'valley', 'island', 'isle', 'swamp', 'marsh')):
                return 'Places/Geography', 'Geography'
            if any(t in loc_type for t in ('region', 'kingdom', 'empire', 'nation', 'duchy', 'barony', 'country')):
                return 'Places/Regions & Nations', 'Regions & Nations'
            if any(t in loc_type for t in ('plane', 'realm', 'dimension')):
                return 'Places/Planes', 'Planes'

            # Fallback by infobox type name
            if itype == 'plane':
                return 'Places/Planes', 'Planes'
            if itype in ('forest', 'mountain', 'body of water', 'island', 'sea'):
                return 'Places/Geography', 'Geography'
            if itype in ('region', 'nation'):
                return 'Places/Regions & Nations', 'Regions & Nations'
            if itype in ('dungeon', 'cave', 'ruins'):
                return 'Places/Fortresses & Ruins', 'Fortresses & Ruins'
            # Default location -> Settlements
            return 'Places/Settlements', 'Settlements'

    # Keyword matching fallback
    search_text = (title + ' ' + content[:800]).lower()
    for pattern, folder in CATEGORY_RULES:
        if re.search(pattern, search_text, re.IGNORECASE):
            label = folder.split('/')[-1]
            return folder, label

    return FALLBACK_FOLDER, 'Miscellaneous'


def sanitize_filename(title: str) -> str:
    safe = re.sub(r'[\\/:*?"<>|]', '-', title)
    safe = re.sub(r'-+', '-', safe).strip(' -.')
    return safe[:200] or 'Untitled'


def slugify_url(title: str) -> str:
    return title.replace(' ', '_')


def strip_wikilinks_for_frontmatter(val: str) -> str:
    """Convert [[Page|Display]] -> Display and [[Page]] -> Page."""
    val = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', val)
    val = re.sub(r'\[\[([^\]]+)\]\]', r'\1', val)
    return val.strip()


def build_frontmatter(title: str, category_label: str, url: str,
                      infobox_type: str = None, infobox_fields: dict = None) -> str:
    """Build YAML frontmatter block."""
    safe_title = title.replace('"', '\\"')
    fm_lines = [
        '---',
        f'title: "{safe_title}"',
        f'category: {category_label}',
        f'source_url: "{url}"',
        'attribution: "Forgotten Realms Wiki (forgottenrealms.fandom.com), CC BY-SA 3.0"',
        'tags:',
        '  - forgotten-realms',
        f'  - {category_label.lower().replace(" ", "-").replace("&", "and")}',
        '---',
        '',
    ]
    return '\n'.join(fm_lines)


# Human-readable labels for infobox rows
INFOBOX_ROW_LABELS = [
    ('type',        'Type'),
    ('region',      'Region'),
    ('size',        'Size'),
    ('government',  'Government'),
    ('ruler',       'Ruler'),
    ('population1', 'Population'),
    ('population',  'Population'),
    ('races',       'Races'),
    ('religion',    'Religion'),
    ('languages',   'Languages'),
    ('alignment',   'Alignment'),
    ('demonym',     'Demonym'),
    ('imports',     'Imports'),
    ('exports',     'Exports'),
    ('aliases',     'Also known as'),
]


def build_its_infobox(title: str, infobox_fields: dict) -> str:
    """
    Build an ITS Theme-compatible infobox callout from extracted infobox fields.
    Format:
        > [!infobox|right]+
        > # Title
        > ###### Details
        > | | |
        > |---|---|
        > | **Type** | Settlement |
        > | **Region** | [[Delimbiyr Vale]], [[Sword Coast]] |
        ...
    """
    if not infobox_fields:
        return ''

    rows = []
    seen_keys = set()
    for wiki_key, label in INFOBOX_ROW_LABELS:
        if wiki_key in infobox_fields and label not in seen_keys:
            val = infobox_fields[wiki_key].strip()
            if val:
                rows.append(f'> | **{label}** | {val} |')
                seen_keys.add(label)

    if not rows:
        return ''

    callout_lines = [
        '> [!infobox|right]+',
        f'> # {title}',
        '> ###### Details',
        '> | | |',
        '> |---|---|',
    ] + rows

    return '\n'.join(callout_lines) + '\n\n'

def detect_xml_namespace(xml_path: Path) -> str:
    with open(xml_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.search(r'xmlns="([^"]+)"', line)
            if m:
                return '{' + m.group(1) + '}'
    return ''


def build_redirect_map(xml_path: Path) -> dict:
    """First pass: build and resolve redirect map."""
    print("Building redirect map (pass 1)...")
    ns = detect_xml_namespace(xml_path)

    raw_redirects = {}
    canonical = {}

    context = ET.iterparse(xml_path, events=('end',))
    redir_count = 0

    for event, elem in context:
        if elem.tag == f'{ns}page':
            title_el = elem.find(f'{ns}title')
            text_el  = elem.find(f'.//{ns}text')
            if title_el is not None and text_el is not None:
                title = (title_el.text or '').strip()
                text  = (text_el.text  or '').strip()
                norm  = normalise_title(title)

                if text.lower().startswith('#redirect'):
                    m = re.search(r'#redirect[^\[]*\[\[([^\]#|]+)', text, re.IGNORECASE)
                    if m:
                        target_raw  = m.group(1).strip()
                        target_norm = normalise_title(target_raw)
                        raw_redirects[norm] = target_norm
                        if target_norm not in canonical:
                            canonical[target_norm] = target_raw.replace('_', ' ').split('#')[0].strip()
                        redir_count += 1
                else:
                    canonical[norm] = title
            elem.clear()

    print(f"  Found {redir_count:,} redirects. Resolving chains...")

    def follow_chain(start):
        visited = {start}
        current = start
        for _ in range(10):
            nxt = raw_redirects.get(current)
            if nxt is None or nxt in visited:
                break
            visited.add(nxt)
            current = nxt
        return current

    redirect_map = {}
    for source, target_norm in raw_redirects.items():
        resolved_norm = follow_chain(target_norm)
        display_title = canonical.get(resolved_norm, resolved_norm.title())
        redirect_map[source] = display_title

    print(f"  Redirect map ready ({len(redirect_map):,} entries).\n")
    return redirect_map


def iter_articles(xml_path: Path):
    """Yield (title, wikitext) for real lore articles only."""
    ns = detect_xml_namespace(xml_path)
    context = ET.iterparse(xml_path, events=('end',))
    for event, elem in context:
        if elem.tag == f'{ns}page':
            title_el = elem.find(f'{ns}title')
            text_el  = elem.find(f'.//{ns}text')
            if title_el is not None and text_el is not None:
                title = (title_el.text or '').strip()
                text  = (text_el.text  or '').strip()
                if (not any(title.startswith(p) for p in SKIP_PREFIXES)
                        and not text.lower().startswith('#redirect')
                        and text.strip()):
                    yield title, text
            elem.clear()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_map_seeds(json_path: Path) -> set:
    """Extract pin link names from an Obsidian map markers JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    seeds = set()
    for marker in data.get('markers', []):
        if marker.get('type') == 'pin' and marker.get('link'):
            seeds.add(marker['link'].strip())
    print(f"  Loaded {len(seeds)} map pins from {json_path.name}")
    return seeds


def build_article_allowlist(xml_path: Path, seeds: set,
                             redirect_map: dict) -> set:
    """
    Build the set of article titles to include using graph traversal.

    Strategy:
    - Start with the map pin names as seeds
    - Follow ALL wikilinks from place articles (Location/Building/Road infoboxes)
    - From non-place articles, do NOT follow further links (they act as leaf nodes)
    - This keeps the vault geographically focused while including directly
      referenced characters, deities, organisations etc.
    """
    print("Building article allowlist from map pins...")

    ns = detect_xml_namespace(xml_path)

    # Build full index: normalised_title -> (canonical_title, wikitext, is_place)
    print("  Indexing all articles...")
    index = {}       # norm -> (canonical, wikitext, is_place)
    redir = {}       # norm -> norm target

    PLACE_IBOX_SET = PLACE_INFOBOX_NAMES  # reuse existing set

    context = ET.iterparse(xml_path, events=('end',))
    for event, elem in context:
        if elem.tag == f'{ns}page':
            title_el = elem.find(f'{ns}title')
            text_el  = elem.find(f'.//{ns}text')
            if title_el is not None and text_el is not None:
                title = (title_el.text or '').strip()
                text  = (text_el.text  or '').strip()
                norm  = normalise_title(title)

                # Skip meta namespaces
                if any(title.startswith(p) for p in SKIP_PREFIXES):
                    elem.clear()
                    continue

                if text.lower().startswith('#redirect'):
                    m = re.search(r'#redirect[^\[]*\[\[([^\]#|]+)', text, re.IGNORECASE)
                    if m:
                        redir[norm] = normalise_title(m.group(1))
                elif text:
                    # Detect if this is a place article
                    ibox_pat = r'\{\{(' + '|'.join(
                        re.escape(n) for n in PLACE_IBOX_SET
                    ) + r')\s*[\n\r|]'
                    is_place = bool(re.search(ibox_pat, text, re.IGNORECASE))
                    index[norm] = (title, text, is_place)
            elem.clear()

    print(f"  Indexed {len(index):,} articles, {len(redir):,} redirects")

    def resolve_norm(name: str) -> str:
        norm = normalise_title(name)
        visited = {norm}
        for _ in range(10):
            if norm in redir:
                nxt = redir[norm]
                if nxt in visited:
                    break
                visited.add(nxt)
                norm = nxt
            else:
                break
        return norm

    def get_links(text: str) -> set:
        links = set()
        for m in re.finditer(r'\[\[([^\]|#]+)', text):
            links.add(m.group(1).strip())
        return links

    # Seed the queue with map pins
    queue = []
    for seed in seeds:
        norm = resolve_norm(seed)
        if norm in index:
            queue.append(norm)

    print(f"  {len(queue)} of {len(seeds)} pins matched articles in XML")

    # BFS: follow links from place articles only
    allowlist = set()
    to_visit = list(queue)

    while to_visit:
        norm = to_visit.pop()
        if norm in allowlist:
            continue
        if norm not in index:
            continue
        allowlist.add(norm)
        canonical, text, is_place = index[norm]

        # Only follow outgoing links from place articles
        if is_place:
            for link in get_links(text):
                target = resolve_norm(link)
                if target not in allowlist and target in index:
                    to_visit.append(target)

    print(f"  Allowlist: {len(allowlist):,} articles to extract\n")
    return allowlist, index


def process(xml_path: Path, output_dir: Path, json_path: Path = None):
    print(f"Input:  {xml_path}")
    print(f"Output: {output_dir}\n")

    redirect_map = build_redirect_map(xml_path)

    # If a JSON map file was provided, build the allowlist
    allowlist = None
    article_index = None
    if json_path:
        seeds = load_map_seeds(json_path)
        allowlist, article_index = build_article_allowlist(xml_path, seeds, redirect_map)

    if allowlist is None:
        print("Counting articles (pass 2)...")
        total = sum(1 for _ in iter_articles(xml_path))
        print(f"Found {total:,} articles.\n")
    else:
        total = len(allowlist)
        print(f"Processing {total:,} articles from allowlist.\n")

    output_dir.mkdir(parents=True, exist_ok=True)
    stats = {'written': 0, 'skipped': 0, 'links_resolved': 0}

    # Use allowlist-based iterator or full iterator
    if allowlist is not None and article_index is not None:
        def iter_allowed():
            for norm, (canonical, wikitext, _) in article_index.items():
                if norm in allowlist:
                    yield canonical, wikitext
        base_iterator = iter_allowed()
    else:
        base_iterator = iter_articles(xml_path)

    iterator = base_iterator
    if HAS_TQDM:
        iterator = tqdm(iterator, total=total, unit='articles')

    for title, wikitext in iterator:
        try:
            # Extract place infobox BEFORE template removal
            infobox_type, infobox_fields = extract_infobox(wikitext)

            # Strip infobox from wikitext (data already extracted above)
            wikitext_clean = strip_place_infoboxes(wikitext)
            # Convert wikitext -> markdown
            body = convert_wikitext_to_markdown(wikitext_clean)

            # Resolve redirect links
            before = body
            body = resolve_wikilinks(body, redirect_map)
            if body != before:
                stats['links_resolved'] += 1

            # If body empty but infobox data exists, synthesise a summary
            if not body.strip() and infobox_fields:
                parts = []
                for fkey, label in [('type', 'Type'), ('region', 'Region'), ('size', 'Size'),
                                     ('government', 'Government'), ('races', 'Races'),
                                     ('religion', 'Religion'), ('ruler', 'Ruler')]:
                    if fkey in infobox_fields:
                        val = strip_wikilinks_for_frontmatter(infobox_fields[fkey])
                        if val:
                            parts.append(f'**{label}:** {val}')
                body = '\n\n'.join(parts)

            if not body.strip():
                stats['skipped'] += 1
                continue

            # Detect category
            subfolder, category_label = detect_category(
                title, body, infobox_type, infobox_fields
            )

            # Build note
            url = BASE_URL + slugify_url(title)
            frontmatter = build_frontmatter(
                title, category_label, url, infobox_type, infobox_fields
            )
            # Build ITS infobox callout if we have place data
            its_infobox = build_its_infobox(title, infobox_fields) if infobox_fields else ''
            note = frontmatter + f'# {title}\n\n' + its_infobox + body + '\n'

            # Write file
            note_dir = output_dir / subfolder
            note_dir.mkdir(parents=True, exist_ok=True)
            filename = sanitize_filename(title) + '.md'
            out_path = note_dir / filename

            if out_path.exists():
                counter = 1
                stem = sanitize_filename(title)
                while out_path.exists():
                    out_path = note_dir / f'{stem}_{counter}.md'
                    counter += 1

            out_path.write_text(note, encoding='utf-8')
            stats['written'] += 1

        except Exception as e:
            stats['skipped'] += 1
            msg = f"WARNING: Skipped '{title}': {e}"
            if HAS_TQDM:
                tqdm.write(msg)
            else:
                print(msg)

    # Post-process: convert broken links to plain text
    fix_broken_links(output_dir)

    return stats


def fix_broken_links(output_dir: Path) -> dict:
    """
    Post-processing pass: scan all notes for [[wikilinks]] that point to
    notes that don't exist in the vault, and convert them to plain text.

    [[Missing Page]]          -> Missing Page
    [[Missing Page|Display]]  -> Display
    [[Existing Page]]         -> [[Existing Page]]  (unchanged)
    """
    print("\nFixing broken links...")

    # Single pass: collect all files, build index, then fix
    all_files = list(output_dir.rglob('*.md'))
    existing = {md.stem.lower() for md in all_files}
    print(f"  Scanning {len(all_files):,} notes...")

    link_pattern = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')
    stats = {'notes_fixed': 0, 'links_fixed': 0}

    for md in all_files:
        original = md.read_text(encoding='utf-8')
        fixed = original
        changed = False

        def replace_link(m):
            page    = m.group(1).strip()
            display = m.group(2).strip() if m.group(2) else None
            # Use sanitize_link_target so [[Waterdeep/Dock Ward]] -> 'waterdeep-dock ward'
            safe = sanitize_link_target(page)
            if safe.lower() in existing:
                return m.group(0)  # link is valid — leave it alone
            # Broken link — return plain text
            return display if display else page

        new_content = link_pattern.sub(replace_link, fixed)
        if new_content != original:
            md.write_text(new_content, encoding='utf-8')
            stats['notes_fixed'] += 1
            # Count how many links were fixed in this note
            stats['links_fixed'] += len(link_pattern.findall(original)) - len(link_pattern.findall(new_content))

    print(f"  Fixed {stats['links_fixed']:,} broken links across {stats['notes_fixed']:,} notes")

    return stats


def print_summary(output_dir: Path, stats: dict):
    print(f"\n{'='*52}")
    print(f"  Notes written  : {stats['written']:,}")
    print(f"  Links resolved : {stats['links_resolved']:,}")
    print(f"  Skipped        : {stats['skipped']:,}")
    print(f"{'='*52}")
    print("\nSubfolder breakdown:")
    total = 0
    for folder in sorted(output_dir.rglob('*')):
        if folder.is_dir():
            count = len(list(folder.glob('*.md')))
            if count > 0:
                rel = folder.relative_to(output_dir)
                print(f"  {rel}/ — {count:,} notes")
                total += count
    print(f"\n  Total: {total:,} notes")
    print(f"\nVault ready at: {output_dir.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert FR Wiki XML dump to Obsidian vault.'
    )
    parser.add_argument('--input',  '-i', required=True,
                        help='Path to forgottenrealms_pages_current.xml')
    parser.add_argument('--output', '-o', default='./FR-Vault',
                        help='Output directory (default: ./FR-Vault)')
    parser.add_argument('--json', '-j', default=None,
                        help='Path to Obsidian map markers JSON file. '
                             'If provided, only extracts articles linked '
                             'from map pins and the places they link to.')
    args = parser.parse_args()

    xml_path   = Path(args.input)
    output_dir = Path(args.output)

    if not xml_path.exists():
        print(f"ERROR: Input file not found: {xml_path}")
        return

    json_path = Path(args.json) if args.json else None
    if json_path and not json_path.exists():
        print(f"ERROR: JSON file not found: {json_path}")
        return

    stats = process(xml_path, output_dir, json_path)
    print_summary(output_dir, stats)


if __name__ == '__main__':
    main()
