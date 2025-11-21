#!/usr/bin/env python3
"""
Test script to verify all RSS feeds in feed.txt are working.
Checks feed accessibility, validity, and authentication if needed.
"""

import feedparser
import json
import os
import base64
import sys
import requests
from urllib.parse import urlparse


def load_feed_credentials():
    """Load feed credentials if the file exists."""
    feed_creds = {}
    if os.path.exists('feed_credentials.json'):
        try:
            with open('feed_credentials.json', 'r') as f:
                creds_data = json.load(f)
                feed_creds = creds_data.get('feeds', {})
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse feed_credentials.json: {e}")
    return feed_creds


def get_auth_headers(feed_config):
    """Generate authentication headers based on feed configuration."""
    headers = {}
    auth_type = feed_config.get('auth_type')
    
    if auth_type == 'api_key':
        headers[feed_config.get('header_name', 'X-API-Key')] = feed_config.get('api_key', '')
    elif auth_type == 'basic':
        username = feed_config.get('username', '')
        password = feed_config.get('password', '')
        auth_string = base64.b64encode(f'{username}:{password}'.encode()).decode()
        headers['Authorization'] = f'Basic {auth_string}'
    elif auth_type == 'bearer':
        headers['Authorization'] = f'Bearer {feed_config.get("token", "")}'
    elif auth_type == 'custom_header':
        headers.update(feed_config.get('headers', {}))
    
    return headers


def test_feed(url, feed_creds):
    """Test a single RSS feed and return status information."""
    result = {
        'url': url,
        'status': 'unknown',
        'error': None,
        'title': None,
        'entry_count': 0,
        'has_auth': False
    }
    
    try:
        # Check if this feed has credentials
        feed_config = feed_creds.get(url, {})
        headers = get_auth_headers(feed_config)
        result['has_auth'] = bool(headers)
        
        # Add default User-Agent to avoid blocking by some sites (like Reddit)
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'python:my-news-digest-bot:v1.0 (by /u/my-news-digest)'
        
        # Fetch feed with authentication/headers
        # Use requests for all feeds for consistency and better control
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except requests.RequestException as e:
            result['status'] = 'error'
            result['error'] = f'Request failed: {e}'
            return result
        
        # Get feed title if available
        if hasattr(feed.feed, 'title'):
            result['title'] = feed.feed.title
        elif hasattr(feed.feed, 'link'):
            result['title'] = feed.feed.link
        
        # Check feed status - prioritize entries over bozo exceptions
        if not feed.entries:
            result['status'] = 'warning'
            result['error'] = 'Feed has no entries'
            if feed.bozo and feed.bozo_exception:
                result['error'] += f' (parsing issue: {feed.bozo_exception})'
        elif feed.bozo and feed.bozo_exception:
            # If we have entries but there's a bozo exception, it's likely
            # a non-fatal issue like encoding mismatch
            error_msg = str(feed.bozo_exception)
            # Check if it's a common non-fatal encoding issue
            if 'encoding' in error_msg.lower() or 'us-ascii' in error_msg.lower():
                result['status'] = 'warning'
                result['error'] = f'Encoding warning: {error_msg}'
            else:
                # Other parsing issues might be more serious
                result['status'] = 'warning'
                result['error'] = f'Parsing issue: {error_msg}'
            result['entry_count'] = len(feed.entries)
        else:
            result['status'] = 'success'
            result['entry_count'] = len(feed.entries)
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


def main():
    """Main function to test all feeds."""
    print("=" * 70)
    print("RSS Feed Test Script")
    print("=" * 70)
    print()
    
    # Load feed URLs
    if not os.path.exists('feed.txt'):
        print("Error: feed.txt not found!")
        sys.exit(1)
    
    with open('feed.txt', 'r') as f:
        urls = [line.strip() for line in f.readlines() if line.strip()]
    
    if not urls:
        print("Error: No feeds found in feed.txt!")
        sys.exit(1)
    
    print(f"Found {len(urls)} feed(s) to test\n")
    
    # Load credentials
    feed_creds = load_feed_credentials()
    if feed_creds:
        print(f"Loaded credentials for {len(feed_creds)} feed(s)\n")
    
    # Test each feed
    results = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Testing: {url}")
        result = test_feed(url, feed_creds)
        results.append(result)
        
        if result['status'] == 'success':
            auth_info = " (with auth)" if result['has_auth'] else ""
            print(f"  ✓ SUCCESS{auth_info}: {result['title'] or 'Untitled'} ({result['entry_count']} entries)")
        elif result['status'] == 'warning':
            print(f"  ⚠ WARNING: {result['error']}")
        else:
            print(f"  ✗ ERROR: {result['error']}")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    successful = [r for r in results if r['status'] == 'success']
    warnings = [r for r in results if r['status'] == 'warning']
    errors = [r for r in results if r['status'] == 'error']
    
    print(f"Total feeds: {len(results)}")
    print(f"✓ Successful: {len(successful)}")
    print(f"⚠ Warnings: {len(warnings)}")
    print(f"✗ Errors: {len(errors)}")
    print()
    
    if errors:
        print("Failed feeds:")
        for result in errors:
            print(f"  - {result['url']}")
            print(f"    Error: {result['error']}")
        print()
    
    if warnings:
        print("Feeds with warnings:")
        for result in warnings:
            print(f"  - {result['url']}")
            print(f"    Warning: {result['error']}")
        print()
    
    # Exit with error code if any feeds failed
    if errors:
        sys.exit(1)
    elif warnings:
        print("All feeds accessible, but some have warnings.")
        sys.exit(0)
    else:
        print("All feeds are working correctly! ✓")
        sys.exit(0)


if __name__ == '__main__':
    main()

