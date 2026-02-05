#!/usr/bin/env python3
"""List available Betfair Baccarat channels.

This script connects to the Betfair API and lists all available Baccarat channels
so you can choose which one to monitor.

Usage: python scripts/list_channels.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import getpass
import xml.etree.ElementTree as ET

from main import load_config
from api_client import APIClient
import requests


def list_channels():
    """Fetch and display available Baccarat channels."""
    config = load_config()

    creds = config.get('credentials', {}) if isinstance(config, dict) else {}
    username = os.getenv('BETFAIR_USERNAME') or (creds.get('username') if isinstance(creds, dict) else None)
    password = os.getenv('BETFAIR_PASSWORD') or (creds.get('password') if isinstance(creds, dict) else None)

    if not username:
        username = input('Betfair username/email: ').strip()
    if not password:
        password = getpass.getpass('Betfair password (input hidden): ').strip()

    config['credentials'] = {'username': username, 'password': password}
    
    print("=== Fetching Available Channels ===")
    print()
    
    try:
        # Initialize API client
        api_client = APIClient(config['credentials'])
        
        # Try to get channel list (endpoint may vary)
        # Common endpoint: /rest/v1/channels?username=USERNAME
        url = f"{APIClient.BASE_URL}/channels?username={username}"
        resp = api_client.session.get(url)
        resp.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(resp.text)
        
        # Define XML namespace
        ns = {'bf': 'urn:betfair:games:api:v1'}
        
        # Find all channel elements
        channels = root.findall('.//bf:channel', ns)
        
        if channels:
            print(f"Found {len(channels)} channels:\n")
            
            baccarat_channels = []
            
            for channel in channels:
                channel_id = channel.get('id')
                name = channel.get('name')
                game_type = channel.get('gameType')
                
                print(f"  Channel ID: {channel_id}")
                print(f"  Name: {name}")
                print(f"  Game Type: {game_type}")
                print()
                
                # Track Baccarat channels
                if 'BACCARAT' in game_type.upper() or 'BACCARAT' in name.upper():
                    baccarat_channels.append((channel_id, name))
            
            # Highlight Baccarat channels
            if baccarat_channels:
                print("\n" + "="*50)
                print("🎯 BACCARAT CHANNELS FOUND:")
                print("="*50)
                for ch_id, ch_name in baccarat_channels:
                    print(f"  Channel ID: {ch_id}")
                    print(f"  Name: {ch_name}")
                    print()
                print("Use one of these channel IDs in your bot configuration!")
            else:
                print("\n⚠️  No Baccarat channels found in the list above.")
                print("You may need to use DevTools method to find the channel ID.")
                
        else:
            print("No channels found in response.")
            print(f"Raw XML:\n{resp.text[:1000]}")
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response: {e.response.text[:500] if e.response else 'No response'}")
        print()
        print("Note: You may need to adjust the endpoint or authentication.")
        print("Check the Betfair Games API documentation for the correct channel listing endpoint.")
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("If you see authentication errors, verify BETFAIR_USERNAME/BETFAIR_PASSWORD (or config.yaml)")


if __name__ == '__main__':
    list_channels()
