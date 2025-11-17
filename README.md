# Your Personal AI Digest

An automated, AI-powered RSS feed aggregator that curates and summarizes news articles based on your interests. This project uses GitHub Actions to fetch RSS feeds, filter relevant articles using AI, and generate beautiful daily digests in both Markdown and HTML formats.

## Features

- 🤖 **AI-Powered Filtering**: Uses DeepSeek AI to evaluate article relevance and generate structured summaries
- 📰 **Multi-Source Aggregation**: Fetches articles from multiple RSS feeds simultaneously
- 🔐 **Authenticated Feeds**: Supports API keys, Basic Auth, Bearer tokens, and custom headers for paid/private feeds
- 📧 **Email Delivery**: Optional email delivery via MailerSend (HTML + text versions)
- 📅 **Automated Scheduling**: Runs daily via GitHub Actions (configurable schedule)
- 📝 **Multiple Formats**: Generates both Markdown and HTML digests
- 🎨 **Beautiful Templates**: Clean, readable HTML email template with hero article and image support

## How It Works

1. **Feed Fetching**: The workflow fetches articles from RSS feeds listed in `feed.txt`
2. **Authentication**: Supports authenticated feeds via `feed_credentials.json` (API keys, Basic Auth, Bearer tokens, custom headers)
3. **AI Filtering**: Articles are evaluated by AI for relevance to your specified topics
4. **Summarization**: Relevant articles receive structured summaries (TOPIC, EVENT, IMPACT, DATA)
5. **Digest Generation**: Creates timestamped Markdown and HTML files in the `digests/` directory
6. **Email Delivery**: Optionally sends the digest via email using MailerSend
7. **Auto-Commit**: Digests are automatically committed to the repository

## Setup

### 1. Fork or Clone This Repository

```bash
git clone https://github.com/yourusername/your-personal-ai-digest.git
cd your-personal-ai-digest
```

### 2. Configure RSS Feeds

Edit `feed.txt` and add your RSS feed URLs (one per line):

```
https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml
https://news.ycombinator.com/rss
https://www.reddit.com/r/technology/top.rss?t=day
```

### 3. Configure Feed Credentials (Optional)

If you have feeds that require authentication, copy the example file and fill in your credentials:

```bash
cp feed_credentials.json.example feed_credentials.json
```

Edit `feed_credentials.json` with your feed authentication details. Supported auth types:
- `api_key`: API key authentication
- `basic`: Basic HTTP authentication
- `bearer`: Bearer token authentication
- `custom_header`: Custom headers

Example:
```json
{
  "feeds": {
    "https://example.com/paid-feed/rss": {
      "auth_type": "api_key",
      "api_key": "YOUR_API_KEY_HERE",
      "header_name": "X-API-Key"
    }
  }
}
```

### 4. Customize Your Topics

Edit `.github/workflows/rss-ai-digest.yml` and modify the `MY_TOPICS` list (around line 133):

```python
MY_TOPICS = ['AI', 'machine learning', 'technology', 'finance']
```

### 5. Customize AI Prompts (Optional)

- `ai_system_prompt.txt`: System prompt that defines the AI's role and output format
- `ai_prompt.txt`: User prompt template for evaluating articles

### 6. Set Up GitHub Secrets

Go to your repository Settings → Secrets and variables → Actions, and add:

**Required:**
- `DEEPSEEK_API_KEY`: Your DeepSeek API key ([Get one here](https://platform.deepseek.com/))

**Optional (for email delivery):**
- `MAILERSEND_API_KEY`: Your MailerSend API key
- `EMAIL_FROM`: Sender email address
- `EMAIL_FROM_NAME`: Sender name
- `EMAIL_TO`: Recipient email address
- `EMAIL_TO_NAME`: Recipient name

### 7. Configure Schedule (Optional)

Edit `.github/workflows/rss-ai-digest.yml` to change the schedule. Default is 8 AM UTC on weekdays:

```yaml
schedule:
  - cron: '0 8 * * 1-5'  # 8 AM UTC, Monday-Friday
```

### 8. Enable Email Delivery (Optional)

To enable email delivery, ensure the email step is enabled in the workflow (line 249):

```yaml
- name: "Optional: Email digest"
  if: true  # Change to false to disable
```

## Project Structure

```
your-personal-ai-digest/
├── .github/
│   └── workflows/
│       └── rss-ai-digest.yml    # GitHub Actions workflow
├── digests/                      # Generated digest files
│   ├── YYYY-MM-DD-HH-MM.md      # Markdown digests
│   └── YYYY-MM-DD-HH-MM.html    # HTML digests
├── ai_prompt.txt                 # User prompt template
├── ai_system_prompt.txt          # System prompt for AI
├── email_template.html           # HTML email template
├── feed.txt                      # RSS feed URLs
├── feed_credentials.json.example # Example credentials file
└── README.md                     # This file
```

## Customization

### Changing Topics

Edit the `MY_TOPICS` list in `.github/workflows/rss-ai-digest.yml`:

```python
MY_TOPICS = ['AI', 'machine learning', 'technology', 'finance']
```

### Modifying Digest Format

The digest format is controlled by:
- **Markdown**: Generated in the "AI Summarize & Filter" step (lines 176-179)
- **HTML**: Uses `email_template.html` with template variables

### Using a Different AI Provider

The workflow currently uses DeepSeek. To use OpenAI or another provider:

1. Change the `base_url` in the workflow (line 137)
2. Update the API key secret name
3. Adjust the model name (line 147)

Example for OpenAI:
```python
client = OpenAI(
    api_key=os.environ['OPENAI_API_KEY'],
    base_url='https://api.openai.com/v1'
)
# ...
model='gpt-4'
```

### Customizing Email Template

Edit `email_template.html` to change the email design. Template variables:
- `{{DATE}}`: Formatted date
- `{{HERO_TITLE}}`: Hero article title
- `{{HERO_SOURCE}}`: Hero article source
- `{{HERO_TIME}}`: Hero article time
- `{{HERO_IMAGE}}`: Hero article image HTML
- `{{HERO_SUMMARY}}`: Hero article summary
- `{{HERO_URL}}`: Hero article URL
- `{{ARTICLES}}`: Remaining articles HTML

## Running Locally

You can also run the digest generation locally:

```bash
# Install dependencies
pip install feedparser openai mailersend

# Set environment variable
export DEEPSEEK_API_KEY="your-api-key"

# Run the Python scripts manually (extract from workflow)
# Or trigger the workflow manually via GitHub Actions UI
```

## Example Output

The digest includes:
- **Hero Article**: Featured story with image and detailed summary
- **Additional Articles**: Up to 9 more relevant articles with summaries
- **Structured Format**: Each article includes TOPIC, EVENT, IMPACT, and DATA fields

## Troubleshooting

### Feeds Not Fetching
- Check that feed URLs in `feed.txt` are valid and accessible
- For authenticated feeds, verify credentials in `feed_credentials.json`
- Check GitHub Actions logs for specific error messages

### AI Filtering Too Strict/Loose
- Adjust `MY_TOPICS` list to be more/less specific
- Modify `ai_system_prompt.txt` to change relevance criteria
- Check AI response format matches expectations

### Email Not Sending
- Verify all email-related secrets are set in GitHub
- Check MailerSend API key is valid
- Review workflow logs for email sending errors

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments

- Built with [feedparser](https://pypi.org/project/feedparser/) for RSS parsing
- AI powered by [DeepSeek](https://www.deepseek.com/)
- Email delivery via [MailerSend](https://www.mailersend.com/)
- Automated with [GitHub Actions](https://github.com/features/actions)

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

