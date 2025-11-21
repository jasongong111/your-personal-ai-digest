import feedparser
import json
import os
import base64
import re
import time
import requests
from datetime import datetime
from urllib.request import Request, urlopen

# Helper to make feedparser entries JSON serializable
def make_serializable(entry):
    new_entry = {}
    for key, value in entry.items():
        if key.endswith('_parsed'):
            continue # Skip struct_time fields
        if isinstance(value, (str, int, float, bool, type(None))):
            new_entry[key] = value
        elif isinstance(value, list):
             # Recursive simplistic check for lists (assuming list of dicts or primitives)
             new_entry[key] = value # trusting it's simple enough or json.dump will fail and we catch it? 
             # deep sanitization might be needed but let's try to keep it simple like the original script
             # The original script seemingly worked with dict(entry), which is odd if it had struct_time.
             # We'll skip keys with _parsed to be safe.
        elif isinstance(value, dict):
             new_entry[key] = value
    return new_entry

def main():
    # Load feed credentials if file exists
    feed_creds = {}
    if os.path.exists('feed_credentials.json'):
        try:
            with open('feed_credentials.json', 'r') as f:
                creds_data = json.load(f)
                feed_creds = creds_data.get('feeds', {})
        except Exception as e:
            print(f"Warning: Could not parse feed_credentials.json: {e}")

    # Load config if file exists
    config = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not parse config.json: {e}")

    articles_per_feed = config.get('limits', {}).get('articles_per_feed', 10)

    if not os.path.exists('feed.txt'):
        print("Error: feed.txt not found")
        return

    urls = [line.strip() for line in open('feed.txt').readlines() if line.strip()]
    articles = []
    
    print(f"Fetching {len(urls)} feeds...")

    for url in urls:
        try:
            # Check if this feed has credentials
            feed_config = feed_creds.get(url, {})
            auth_type = feed_config.get('auth_type')
            
            # Prepare headers for authenticated feeds
            headers = {}
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
            
            # Add default User-Agent to avoid blocking by some sites (like Reddit)
            if 'User-Agent' not in headers:
                headers['User-Agent'] = 'python:my-news-digest-bot:v1.0 (by /u/my-news-digest)'
            
            # Fetch feed with headers
            # Use requests for all feeds for consistency and better control
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
            except requests.RequestException as e:
                print(f'Error fetching feed {url}: {e}')
                continue
            
            if feed.bozo:
                print(f"Warning parsing feed {url}: {feed.bozo_exception}")
            
            feed_title = feed.feed.get('title', '')
            if not feed_title:
                # Fallback to domain
                match = re.search(r'https?://([^/]+)', url)
                feed_title = match.group(1).replace('www.', '') if match else 'Unknown Source'

            # Process entries
            print(f"  - {feed_title}: Found {len(feed.entries)} entries")
            
            for entry in feed.entries[:articles_per_feed]:  # Top N per feed
                # Extract image from various RSS formats
                image_url = None
                
                # Try media:content (common in RSS)
                if hasattr(entry, 'media_content') and entry.media_content:
                    image_url = entry.media_content[0].get('url')
                
                # Try media:thumbnail
                elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get('url')
                
                # Try enclosure (podcasts/media)
                elif hasattr(entry, 'enclosures') and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get('type', '').startswith('image/'):
                            image_url = enc.get('href')
                            break
                
                # Try looking in content/description for img tags
                if not image_url:
                    content = entry.get('content', [{}])[0].get('value', '') if hasattr(entry, 'content') else entry.get('description', '')
                    img_match = re.search(r'<img[^>]+src=[\"\']([^\"\'>]+)[\"\']', content)
                    if img_match:
                        image_url = img_match.group(1)
                
                # Create article dict with image and source info
                # We manually copy fields to avoid serialization issues with struct_time
                article = {
                    'title': entry.get('title', 'No title'),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'content': entry.get('content', [{'value': ''}])[0]['value'] if 'content' in entry else '',
                    'published': entry.get('published', ''),
                    'updated': entry.get('updated', ''),
                    'id': entry.get('id', ''),
                    'image_url': image_url,
                    'source_title': feed_title,
                    'source_url': feed.feed.get('link', url)
                }
                
                # If published is missing, try updated
                if not article['published'] and article['updated']:
                    article['published'] = article['updated']

                articles.append(article)
        except Exception as e:
            print(f'Error fetching feed {url}: {e}')
            continue
    
    # Save to file
    print(f"Saved {len(articles)} articles to articles.json")
    with open('articles.json', 'w') as f:
        json.dump(articles, f, indent=2)

if __name__ == "__main__":
    main()
