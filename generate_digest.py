import json
import os
import re
import html
from datetime import datetime
import dateutil.parser
from openai import OpenAI

def format_date(date_str):
    if not date_str:
        return ""
    try:
        # Try to parse date string using dateutil (handles most formats)
        dt = dateutil.parser.parse(date_str)
        return dt.strftime('%b %d, %H:%M')
    except:
        return date_str

def normalize_title(t):
    t = t.lower()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    words = set(t.split())
    return words

def are_similar(title1, title2):
    words1 = normalize_title(title1)
    words2 = normalize_title(title2)
    
    if not words1 or not words2:
        return False
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    similarity = intersection / union if union > 0 else 0
    
    return similarity > 0.6 and intersection >= 3

def get_source_name(item):
    if item.get('source_title') and item.get('source_title') != 'Unknown Source':
            return item['source_title']
    # Fallback to domain extraction
    url = item.get('url', '')
    match = re.search(r'https?://([^/]+)', url)
    return match.group(1).replace('www.', '') if match else 'Unknown'

def summarize_group(client, group, system_prompt, prompt_template, topics_str):
    if len(group) == 1:
        a = group[0]
        articles_text = f"Article title: {a['title']}\nArticle URL: {a['link']}\nContent/Snippet: {a.get('summary', '')[:500]}"
    else:
        articles_list = []
        for a in group:
            articles_list.append(f"Article title: {a['title']}\nArticle URL: {a['link']}\nContent/Snippet: {a.get('summary', '')[:500]}")
        articles_text = "\n\n".join(articles_list)
    
    user_message = prompt_template.format(articles=articles_text, topics=topics_str)
    
    try:
        resp = client.chat.completions.create(
            model='deepseek-reasoner',
            messages=[
                {'role':'system','content':system_prompt},
                {'role':'user','content':user_message}
            ],
            max_tokens=4000
        )
        ai_response = resp.choices[0].message.content.strip()
        
        if ai_response.upper().startswith('IRRELEVANT'):
            return None

        score = 0
        summary_text = ai_response
        
        lines = ai_response.split('\n')
        if lines and lines[0].upper().startswith('SCORE:'):
            try:
                score_str = lines[0].split(':')[1].strip()
                score = int(score_str)
                summary_text = '\n'.join(lines[1:]).strip()
            except:
                pass

        if len(group) > 1 and 'Sources:' in summary_text:
            summary_parts = summary_text.split('Sources:')
            summary_only = summary_parts[0].strip()
        else:
            summary_only = summary_text
        
        urls = [a['link'] for a in group]
        
        return {
            'title': group[0]['title'],
            'url': urls[0],
            'urls': urls,
            'summary': summary_only,
            'image_url': group[0].get('image_url'),
            'score': score,
            'source_title': group[0].get('source_title', 'Unknown Source'),
            'source_url': group[0].get('source_url', urls[0]),
            'published': group[0].get('published', '')
        }
    except Exception as e:
        print(f"Error summarizing group: {e}")
        return None

def render_article_html(item, show_image=True):
    safe_summary = html.escape(item['summary'])
    safe_title = html.escape(item['title'])
    
    source_name = get_source_name(item)
    source_url = item.get('source_url', item.get('url', '#'))
    published_date = format_date(item.get('published', ''))
    
    img_html = ''
    if show_image and item.get('image_url'):
        safe_alt = html.escape(item['title'])
        img_html = f'<img src="{item["image_url"]}" alt="{safe_alt}">'
    
    title_html = f'<a href="{item["url"]}">{safe_title}</a>'
    
    meta_html = f'<a href="{source_url}" style="color: #666; text-decoration: none;">{source_name}</a>'
    if published_date:
        meta_html += f' • {published_date}'

    article_template = '<div class="article">{{IMAGE}}<h4>{{TITLE}}</h4><p class="meta">{{META}}</p><p>{{SUMMARY}}</p></div>'
    
    article_html = article_template.replace('{{IMAGE}}', img_html)
    article_html = article_html.replace('{{TITLE}}', title_html)
    article_html = article_html.replace('{{SUMMARY}}', safe_summary)
    article_html = article_html.replace('{{META}}', meta_html)
    return article_html

def main():
    # Load config
    config = {}
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            config = json.load(f)

    if not os.path.exists('articles.json'):
        print("Error: articles.json not found. Run fetch_feeds.py first.")
        return

    with open('articles.json') as f:
        articles = json.load(f)
    
    MY_TOPICS = config.get('topics', ['AI', 'Technology', 'Startup'])
    final_digest_count = config.get('limits', {}).get('final_digest_count', 10)
    topics_str = ', '.join(MY_TOPICS)
    
    # Load prompts
    if os.path.exists('ai_system_prompt.txt'):
        with open('ai_system_prompt.txt', 'r') as f:
            # We format only once here, but we might need different topics for GitHub. 
            # Actually, let's keep the placeholder in the text and format inside the loop if possible.
            # But the original code formatted it immediately. 
            # Let's re-read the file content raw.
            pass
    
    with open('ai_system_prompt.txt', 'r') as f:
        raw_system_prompt = f.read().strip()
    
    with open('ai_prompt.txt', 'r') as f:
        prompt_template = f.read().strip()
    
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        return

    client = OpenAI(api_key=api_key, base_url='https://api.deepseek.com')
    
    # Split articles
    github_articles = []
    regular_articles = []
    
    for a in articles:
        # Check if it's from GitHub Trending feed
        src = a.get('source_url', '').lower()
        title = a.get('source_title', '').lower()
        if 'githubtrendingrss' in src or 'github trending' in title:
            github_articles.append(a)
        else:
            regular_articles.append(a)
            
    print(f"Separated {len(github_articles)} GitHub articles and {len(regular_articles)} regular articles.")

    # --- Process Regular Articles ---
    processed_indices = set()
    article_groups = []
    
    for i, a in enumerate(regular_articles):
        if i in processed_indices: continue
        
        # Pre-filter removed to let AI determine relevance
        
        group = [a]
        processed_indices.add(i)
        
        for j, other in enumerate(regular_articles[i+1:], start=i+1):
            if j in processed_indices: continue
            # Check similarity for grouping
            if are_similar(a['title'], other['title']):
                group.append(other)
                processed_indices.add(j)
        
        article_groups.append(group)
    
    print(f"Summarizing {len(article_groups)} regular story groups...")
    
    system_prompt_regular = raw_system_prompt.format(topics=topics_str)
    filtered_regular = []
    
    for group in article_groups:
        res = summarize_group(client, group, system_prompt_regular, prompt_template, topics_str)
        if res:
            filtered_regular.append(res)
            
    filtered_regular.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # --- Process GitHub Articles ---
    # We assume no duplicates in GitHub Trending feed usually
    print(f"Summarizing {len(github_articles)} GitHub articles...")
    
    # Use a broader topic set for GitHub to ensure they aren't filtered as Irrelevant
    github_topics = "Software Engineering, Open Source, GitHub Trending, Technology, Programming, AI"
    
    # Load specialized GitHub prompt if available, otherwise fallback
    if os.path.exists('ai_github_system_prompt.txt'):
        with open('ai_github_system_prompt.txt', 'r') as f:
             system_prompt_github = f.read().strip()
    else:
         system_prompt_github = raw_system_prompt.format(topics=github_topics)
    
    filtered_github = []
    for a in github_articles:
        # Treat each as a group of 1
        res = summarize_group(client, [a], system_prompt_github, prompt_template, github_topics)
        if res:
            filtered_github.append(res)
            
    # Sort GitHub by score (or keep feed order if score is similar)
    filtered_github.sort(key=lambda x: x.get('score', 0), reverse=True)

    # --- Generate Output ---
    
    # Create digests directory
    os.makedirs('digests', exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d-%H-%M')
    md_filename = f'digests/{timestamp}.md'
    html_filename = f'digests/{timestamp}.html'
    
    # Markdown
    with open(md_filename, 'w') as f:
        f.write('# Your Daily Digest\n\n')
        
        if filtered_regular:
            f.write('## Top Stories\n\n')
            for item in filtered_regular[:final_digest_count]:
                f.write(f'### {item["title"]}\n{item["summary"]}\n{item["url"]}\n\n')
        
        if filtered_github:
            f.write('## Trending GitHub Repos\n\n')
            for item in filtered_github:
                f.write(f'### {item["title"]}\n{item["summary"]}\n{item["url"]}\n\n')

    # HTML
    if os.path.exists('email_template.html'):
        with open('email_template.html', 'r') as f:
            html_template = f.read()
    else:
        print("Error: email_template.html not found")
        return
        
    # Hero (from regular articles)
    hero = filtered_regular[0] if filtered_regular else {'title':'No news today','url':'#','summary':'','image_url':None, 'source_title': 'System'}
    
    # Build Hero HTML
    hero_source_html = f'<a href="{hero.get("source_url","#")}" style="text-decoration: none; color: inherit;">{get_source_name(hero)}</a>'
    if hero.get('published'):
        hero_source_html += f' • {format_date(hero["published"])}'
    
    hero_image_html = ''
    if hero.get('image_url'):
        safe_hero_alt = html.escape(hero['title'])
        hero_image_html = f'<img src="{hero["image_url"]}" alt="{safe_hero_alt}">'

    # Build Regular Articles HTML
    articles_html = ''
    for item in filtered_regular[1:final_digest_count]:
        articles_html += render_article_html(item, show_image=True)
        
    # Build GitHub HTML
    github_html = ''
    if filtered_github:
        github_html = '<div class="more"><h3>Trending GitHub Repositories</h3>'
        for item in filtered_github:
             github_html += render_article_html(item, show_image=False)
        github_html += '</div><div class="divider"></div>'
    
    # Replace in template
    date_str = datetime.utcnow().strftime('%A, %B %d, %Y')
    html_content = html_template.replace('{{DATE}}', date_str)
    html_content = html_content.replace('{{HERO_TITLE}}', html.escape(hero['title']))
    html_content = html_content.replace('{{HERO_SOURCE}}', hero_source_html)
    html_content = html_content.replace('{{HERO_IMAGE}}', hero_image_html)
    html_content = html_content.replace('{{HERO_SUMMARY}}', html.escape(hero['summary']))
    html_content = html_content.replace('{{HERO_URL}}', hero['url'])
    
    # Inject GitHub Section
    html_content = html_content.replace('{{GITHUB_SECTION}}', github_html)
    
    # Inject Regular Articles
    html_content = re.sub(r'\{\{#ARTICLES\}\}.*?\{\{/ARTICLES\}\}', articles_html, html_content, flags=re.DOTALL)
    
    with open(html_filename, 'w') as f:
        f.write(html_content)
        
    print(f"Digest generated: {html_filename}")

    # Write filenames for GitHub Actions to use
    with open('digest_filename.txt', 'w') as f:
        f.write(md_filename)
    
    with open('digest_html_filename.txt', 'w') as f:
        f.write(html_filename)

if __name__ == "__main__":
    main()
