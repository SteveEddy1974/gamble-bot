#!/usr/bin/env python3
"""
Script to find the Exchange Baccarat channel ID by testing common values.
"""
import sys
import os
import getpass
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config
from api_client import APIClient

def find_channel():
    """Try to find the active Exchange Baccarat channel."""

    config = load_config()
    creds = config.get('credentials', {})
    username = os.getenv('BETFAIR_USERNAME') or creds.get('username')
    password = os.getenv('BETFAIR_PASSWORD') or creds.get('password')

    if not username:
        username = input('Betfair username/email: ').strip()
    if not password:
        password = getpass.getpass('Betfair password (input hidden): ').strip()

    config['credentials'] = {'username': username, 'password': password}
    
    print("Testing Betfair Games API connection...")
    print("=" * 60)
    
    # Common Exchange Baccarat channel IDs
    # These are typical channel IDs used for Exchange Baccarat tables
    common_channels = [
        "20831",  # Most common
        "20832",
        "20833",
        "12345",
        "67890",
    ]
    
    client = APIClient(config['credentials'])
    
    print(f"\nCredentials: {config['credentials']['username']}")
    print("Testing connection to Betfair Games API...\n")
    
    working_channels = []
    
    for channel_id in common_channels:
        try:
            print(f"Trying channel {channel_id}...", end=" ")
            response = client.get_snapshot(channel_id)
            
            # If we get here, the channel is valid
            print("✓ SUCCESS!")
            
            # Try to extract game info
            shoe_elem = response.find('shoe')
            if shoe_elem is not None:
                cards_remaining = shoe_elem.find('cardsRemaining')
                if cards_remaining is not None:
                    print(f"  └─ Cards remaining: {cards_remaining.text}")
                    working_channels.append(channel_id)
            else:
                print(f"  └─ Channel accessible but no shoe data")
                
        except Exception as e:
            print(f"✗ Not available ({str(e)[:50]})")
    
    print("\n" + "=" * 60)
    if working_channels:
        print(f"\n✅ Found {len(working_channels)} working channel(s):")
        for ch in working_channels:
            print(f"   • {ch}")
        print(f"\n💡 Recommended channel ID: {working_channels[0]}")
        return working_channels[0]
    else:
        print("\n❌ No working channels found.")
        print("\nPossible reasons:")
        print("1. Credentials are incorrect")
        print("2. Account doesn't have Games API access")
        print("3. Need to log in via browser first")
        print("\nTry manually visiting: https://games.betfair.com/exchange-baccarat/turbo/")
        print("Then run this script again.")
        return None

if __name__ == '__main__':
    channel = find_channel()
    if channel:
        print(f"\n✨ Ready to configure! Use channel ID: {channel}")
    else:
        print("\n⚠️  Setup incomplete - see messages above")
