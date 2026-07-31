#!/usr/bin/env python3
"""
Create Discord channels for each Exos project under an 'EXOS PROJECTS' category.
Uses Discord HTTP API directly. Requires DISCORD_BOT_TOKEN env var.

Usage:
  DISCORD_BOT_TOKEN=... python3 setup-discord-channels.py
  python3 setup-discord-channels.py --dry-run    # Preview only
"""

import json
import os
import sys
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNELS_FILE = os.path.join(SCRIPT_DIR, 'project-channels.json')
DISCORD_API = 'https://discord.com/api/v10'
BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN', '')

def api(method, path, body=None):
    url = DISCORD_API + path
    headers = {
        'Authorization': f'Bot {BOT_TOKEN}',
        'Content-Type': 'application/json',
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else str(e)
        print(f"  API error {e.code}: {err}")
        return None

def main():
    dry_run = '--dry-run' in sys.argv

    with open(CHANNELS_FILE) as f:
        config = json.load(f)

    guild_id = config['discord_server_id']
    category_name = config['discord_category_name']

    if dry_run:
        print(f"[DRY RUN] Would create category '{category_name}' in guild {guild_id}")
        for ch in config['channels']:
            print(f"  Would create #{ch['discord_channel_name']} — {ch['project_name']}")
        print(f"  Would create #{config['default_channel']['discord_channel_name']} — General/Default")
        return

    if not BOT_TOKEN:
        print("Error: Set DISCORD_BOT_TOKEN environment variable")
        print("Get it from: Discord Developer Portal > Your Bot > Token")
        sys.exit(1)

    # Get existing channels to avoid duplicates
    existing = api('GET', f'/guilds/{guild_id}/channels') or []
    existing_names = {ch['name']: ch for ch in existing}

    # Find or create the category
    category_id = None
    for ch in existing:
        if ch['type'] == 4 and ch['name'] == category_name:
            category_id = ch['id']
            print(f"Found existing category: {category_name} ({category_id})")
            break

    if not category_id:
        result = api('POST', f'/guilds/{guild_id}/channels', {
            'name': category_name,
            'type': 4,  # GUILD_CATEGORY
        })
        if result:
            category_id = result['id']
            print(f"Created category: {category_name} ({category_id})")
        else:
            print("Failed to create category")
            sys.exit(1)

    # Create channels
    all_channels = config['channels'] + [config['default_channel']]
    updated = False

    for ch in all_channels:
        ch_name = ch['discord_channel_name']
        if ch_name in existing_names:
            ch_data = existing_names[ch_name]
            print(f"  #{ch_name} already exists ({ch_data['id']})")
            if 'discord_channel_id' in ch:
                ch['discord_channel_id'] = ch_data['id']
                updated = True
            continue

        topic = ch.get('project_name', 'General project channel')
        email_alias = ch.get('email_alias', '')
        if email_alias:
            topic += f" | Email: {email_alias}"

        result = api('POST', f'/guilds/{guild_id}/channels', {
            'name': ch_name,
            'type': 0,  # GUILD_TEXT
            'parent_id': category_id,
            'topic': topic,
        })
        if result:
            print(f"  Created #{ch_name} ({result['id']})")
            ch['discord_channel_id'] = result['id']
            updated = True

            # Send welcome message
            welcome = (
                f"**{ch.get('project_name', ch_name)}** project channel\n"
                f"Emails to `{email_alias}` will auto-update here.\n"
                f"Category: {ch.get('category', 'General')}"
            )
            api('POST', f"/channels/{result['id']}/messages", {'content': welcome})
        else:
            print(f"  Failed to create #{ch_name}")

    # Update config file with channel IDs
    if updated:
        with open(CHANNELS_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"\nUpdated {CHANNELS_FILE} with channel IDs")

    print("\nDone! Channels are ready.")


if __name__ == '__main__':
    main()
