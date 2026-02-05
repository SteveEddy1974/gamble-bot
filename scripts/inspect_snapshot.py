#!/usr/bin/env python3
"""Inspect the raw XML structure from a channel snapshot."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config
from api_client import APIClient


def inspect_snapshot(channel_id):
    """Fetch and display raw snapshot XML."""
    config = load_config()
    api_client = APIClient(config['credentials'])
    
    print(f"Fetching snapshot for channel {channel_id}...")
    print("=" * 80)
    
    try:
        xml_root = api_client.get_snapshot(channel_id)
        
        # Import xml.etree.ElementTree for pretty printing
        import xml.etree.ElementTree as ET
        xml_str = ET.tostring(xml_root, encoding='unicode')
        
        print(xml_str[:5000])  # First 5000 characters
        print("\n" + "=" * 80)
        print(f"Total length: {len(xml_str)} characters")
        
        # List all top-level elements
        print("\nTop-level elements found:")
        for child in xml_root:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            print(f"  - {tag}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    channel_id = sys.argv[1] if len(sys.argv) > 1 else '1444086'
    inspect_snapshot(channel_id)
