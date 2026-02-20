---
name: brand-monitor
description: Monitor brand mentions across all social platforms with sentiment analysis, intelligent alerting, and engagement tracking. Use when Claude needs to: (1) Track brand mentions across platforms, (2) Analyze sentiment and categorize mentions, (3) Generate alerts for urgent mentions, (4) Create weekly engagement summaries, (5) Update dashboard with mention metrics
license: Complete terms in LICENSE.txt
---

# Brand Monitor

This skill provides comprehensive brand mention monitoring across X/Twitter, Facebook, Instagram, and LinkedIn with sentiment analysis, intelligent alerting, and automated reporting.

## Prerequisites

### Environment Configuration
Required `.env` variables:
```bash
BRAND_KEYWORDS=YourBrand,@YourHandle,#YourHashtag
MENTION_CHECK_INTERVAL=1800  # 30 minutes in seconds

# Platform-specific credentials (from other skills)
X_BEARER_TOKEN=your_bearer_token
FACEBOOK_ACCESS_TOKEN=your_token
INSTAGRAM_ACCESS_TOKEN=your_token
LINKEDIN_ACCESS_TOKEN=your_token
```

### Dependencies
- `x-twitter-automation` skill for X monitoring
- `facebook-automation` skill for Facebook monitoring
- `instagram-automation` skill for Instagram monitoring
- LinkedIn API access (if available)

## Quick Start

Start monitoring:
```bash
/brand-monitor-start

Check mentions now:
```bash
/brand-monitor-check

Generate weekly summary:
```bash
/brand-monitor-summary --week 2024-W03

Update keywords:
```bash
/brand-monitor-keywords --add "NewProduct" --remove "OldBrand"
```

## Core Features

### 1. Multi-Platform Monitoring

**Supported Platforms:**
- **X/Twitter**: Mentions, hashtags, keyword searches
- **Facebook**: Page comments, post mentions, tagged posts
- **Instagram**: Comments, tagged photos, story mentions
- **LinkedIn**: Post comments, article mentions, company mentions

**Monitoring Schedule:**
- **Frequency**: Every 30 minutes (configurable)
- **Real-time**: Priority for verified accounts
- **Batch processing**: Group mentions by platform

### 2. Keyword & Brand Tracking

**Keyword Configuration:**
```yaml
brand_keywords:
  primary:
    - "YourBrand"
    - "@YourHandle"
    - "#YourHashtag"
  products:
    - "ProductA"
    - "ServiceB"
  competitors:
    - "CompetitorX"
  campaigns:
    - "#Launch2024"
    - "SpecialOffer"
```

**Search Strategy:**
- Exact match for brand name
- Broad match for variations
- Hashtag tracking
- Misspellings and typos
- Industry terms

### 3. Sentiment Analysis

**Sentiment Classification:**
```python
def analyze_sentiment(text, platform, author_influence):
    """Analyze mention sentiment and urgency"""

    # Base sentiment analysis
    sentiment = claude_sentiment_analysis(text)

    # Context modifiers
    if contains_question(text):
        sentiment['urgency'] = 'high'
        sentiment['category'] = 'query'

    if contains_complaint_words(text):
        sentiment['urgency'] = 'critical'
        sentiment['category'] = 'complaint'

    if author_influence > 10000:  # Verified/influencer
        sentiment['urgency'] = max(sentiment['urgency'], 'high')

    return sentiment
```

**Sentiment Categories:**
- **Positive**: Praise, recommendations, success stories
- **Negative**: Complaints, issues, criticism
- **Neutral**: Mentions, questions, news
- **Mixed**: Both positive and negative elements

### 4. Priority Alert System

**Alert Priority Matrix:**

| Sentiment | Author Type | Action Required |
|-----------|-------------|-----------------|
| Negative | Verified | Immediate alert |
| Negative | Regular | 1-hour alert |
| Question | Verified | Immediate alert |
| Question | Regular | 1-hour alert |
| Positive | Any | Log only |
| Neutral | Any | Log only |

**Alert Generation Logic:**
```python
def should_create_alert(mention):
    """Determine if mention needs alert"""

    # Always alert for negative sentiment
    if mention['sentiment'] == 'negative':
        return True, "Negative sentiment requires attention"

    # Always alert for questions
    if mention['category'] == 'query':
        return True, "Question requires response"

    # Always alert for verified accounts
    if mention['author']['verified']:
        return True, "Verified account mention"

    # Log positive mentions without alert
    if mention['sentiment'] == 'positive':
        return False, "Positive mention logged only"

    return False, "No action needed"
```

### 5. Alert File Generation

**Alert File Format (`/Needs_Action/MENTION_<platform>_<YYYY-MM-DD>.md`):**
```markdown
---
type: mention_alert
platform: twitter
mention_id: 1234567890
author: @techjournalist
author_followers: 50000
verified: true
sentiment: negative
urgency: critical
keyword: YourBrand
content: "Is YourBrand having issues? Their service has been down for 2 hours..."
url: https://twitter.com/techjournalist/status/1234567890
detected_at: 2024-01-21T14:30:00Z
requires_response: true
category: complaint
---

# Brand Mention Alert - Twitter - 2024-01-21

## Mention Details
- **Platform:** Twitter
- **Author:** @techjournalist (Tech Journalist)
- **Followers:** 50,000
- **Verified:** ✅
- **Detected:** 2024-01-21 14:30
- **Urgency:** Critical

## Content
> "Is YourBrand having issues? Their service has been down for 2 hours. #YourBrand"

## Analysis
- **Sentiment:** Negative
- **Category:** Service complaint
- **Keywords:** YourBrand, #YourHashtag
- **Reach Estimate:** 50,000+ impressions

## Suggested Response
**Option 1 (Direct):**
"We're aware of the issue and working on it. Expected resolution in 30 minutes. Thank you for your patience!"

**Option 2 (Transparent):**
"You're right, we're experiencing some difficulties. Our team is actively working on a fix. Updates here: [status page]"

## Action Required
- [ ] Craft and post response
- [ ] Monitor for replies
- [ ] Escalate to support team
- [ ] Update status page

**Move to `/Pending_Approval/` after response**
---
*Auto-generated at 2024-01-21 14:31*
```

## Implementation Details

### Monitoring Engine

```python
class BrandMonitorEngine:
    def __init__(self):
        self.platforms = {
            'twitter': TwitterMonitor(),
            'facebook': FacebookMonitor(),
            'instagram': InstagramMonitor(),
            'linkedin': LinkedInMonitor()
        }
        self.last_check = {}
        self.keywords = load_keywords_from_env()

    def run_monitoring_cycle(self):
        """Run complete monitoring cycle"""

        all_mentions = []

        for platform_name, monitor in self.platforms.items():
            try:
                mentions = monitor.search_mentions(
                    keywords=self.keywords,
                    since=self.last_check.get(platform_name)
                )
                all_mentions.extend(mentions)
                self.last_check[platform_name] = datetime.now()

            except Exception as e:
                log_error(f"{platform_name}_monitor_failed", str(e))

        # Process all mentions
        self.process_mentions(all_mentions)
```

### Platform-Specific Monitors

**Twitter Monitor:**
```python
def search_twitter_mentions(keywords, since):
    """Search Twitter for brand mentions"""

    queries = []
    for keyword in keywords:
        queries.append(f"{keyword} -filter:retweets")

    all_tweets = []
    for query in queries:
        tweets = client.search_recent_tweets(
            query=query,
            tweet_fields=['created_at', 'author_id', 'public_metrics'],
            user_fields=['verified', 'public_metrics'],
            expansions=['author_id']
        )
        all_tweets.extend(tweets.data or [])

    return all_tweets
```

**Facebook Monitor:**
```python
def search_facebook_mentions(keywords, since):
    """Search Facebook for brand mentions"""

    mentions = []

    # Search page posts
    posts = graph.get_connections(
        page_id,
        'posts',
        since=since.strftime('%Y-%m-%d'),
        fields='message,created_time,comments'
    )

    for post in posts['data']:
        if contains_keywords(post.get('message', ''), keywords):
            mentions.append(format_facebook_post(post))

        # Check comments
        for comment in post.get('comments', {}).get('data', []):
            if contains_keywords(comment.get('message', ''), keywords):
                mentions.append(format_facebook_comment(comment))

    return mentions
```

### Sentiment Analysis Integration

```python
def claude_sentiment_analysis(text):
    """Use Claude for sentiment analysis"""

    prompt = f"""
    Analyze the sentiment of this social media post:
    "{text}"

    Return JSON format:
    {{
        "sentiment": "positive|negative|neutral",
        "confidence": 0.95,
        "urgency": "low|medium|high|critical",
        "category": "praise|complaint|query|neutral",
        "emotions": ["frustration", "disappointment"],
        "key_phrases": ["customer service", "down time"]
    }}
    """

    response = claude_api.complete(prompt)
    return json.loads(response)
```

## Commands Reference

### Monitoring Commands
```bash
# Start continuous monitoring
/brand-monitor-start

# Stop monitoring
/brand-monitor-stop

# Check current status
/brand-monitor-status

# Run manual check
/brand-monitor-check

# Check specific platform
/brand-monitor-check --platform twitter
```

### Configuration Commands
```bash
# Add keywords
/brand-monitor-keywords --add "NewProduct" --category products

# Remove keywords
/brand-monitor-keywords --remove "OldBrand"

# List all keywords
/brand-monitor-keywords --list

# Set check interval
/brand-monitor-interval --minutes 30

# Test keyword matching
/brand-monitor-test --text "YourBrand is great!" --keywords "YourBrand"
```

### Alert Commands
```bash
# List pending alerts
/brand-monitor-alerts --status pending

# List alerts by sentiment
/brand-monitor-alerts --sentiment negative

# Mark alert as resolved
/brand-monitor-resolve --alert MENTION_twitter_2024-01-21_001

# Generate alert summary
/brand-monitor-summary --period 24h
```

### Analytics Commands
```bash
# Weekly engagement summary
/brand-monitor-summary --week 2024-W03

# Platform comparison
/brand-monitor-compare --platforms twitter,facebook --period 7d

# Keyword performance
/brand-monitor-keywords-stats --period 30d

# Sentiment trends
/brand-monitor-sentiment-trend --period 90d
```

## Dashboard Integration

### Dashboard.md Updates
```markdown
## Brand Mentions - Real-time

### Current Status
- **Last Check:** 2 minutes ago
- **Active Alerts:** 3
- **Today's Mentions:** 47
- **Sentiment Breakdown:** 65% positive, 25% neutral, 10% negative

### Platform Breakdown
| Platform | Mentions | Positive | Negative | Questions |
|----------|----------|----------|----------|-----------|
| Twitter | 23 | 15 | 3 | 5 |
| Facebook | 12 | 8 | 2 | 2 |
| Instagram | 8 | 6 | 1 | 1 |
| LinkedIn | 4 | 4 | 0 | 0 |

### Trending Topics
- #ProductLaunch (23 mentions)
- Customer Support (12 mentions)
- New Feature (8 mentions)

### Recent Alerts
- [ ] Negative mention from @techjournalist - 5 min ago
- [ ] Question about pricing - 15 min ago
- [ ] Service complaint - 1 hour ago
```

## Weekly Summary Generation

**Summary Format (`/Briefings/MENTION_SUMMARY_YYYY-MM-DD.md`):**
```markdown
---
week: 2024-W03
period: 2024-01-15 to 2024-01-21
total_mentions: 289
generated_by: brand-monitor
---

# Weekly Brand Mention Summary - Week 2024-W03

## Overview
- **Total Mentions:** 289 (↑12% from last week)
- **Platforms:** 4 active
- **Sentiment:** 71% positive, 24% neutral, 5% negative
- **Response Rate:** 94% (within 1 hour)
- **Top Keywords:** #ProductLaunch (89 mentions)

## Platform Performance

### Twitter
- **Mentions:** 142 (49%)
- **Engagement:** 2,345 interactions
- **Top Tweet:** Product announcement - 892 retweets
- **Sentiment:** 68% positive

### Facebook
- **Mentions:** 87 (30%)
- **Reach:** 12,450 users
- **Top Post:** Customer story - 234 shares
- **Sentiment:** 75% positive

### Instagram
- **Mentions:** 45 (16%)
- **Tags:** 23 brand tags
- **Top Story:** Behind the scenes - 567 views
- **Sentiment:** 82% positive

### LinkedIn
- **Mentions:** 15 (5%)
- **Views:** 3,450 professionals
- **Top Article:** Industry insights - 89 comments
- **Sentiment:** 93% positive

## Sentiment Analysis

### Positive Highlights
- "Best customer service ever!" - @happy_customer
- "YourBrand changed my business" - @entrepreneur
- "Innovative product, highly recommend" - @techreviewer

### Negative Issues
- Service downtime complaint (3 mentions)
- Pricing concerns (2 mentions)
- Feature request delays (1 mention)

### Neutral Observations
- Industry comparison articles (12 mentions)
- Product inquiries (8 mentions)
- Partnership discussions (5 mentions)

## Response Performance

### Response Times
- **Average:** 23 minutes
- **Target:** <60 minutes
- **Achievement:** 96% within target

### Resolution Status
- **Resolved:** 47 issues
- **In Progress:** 8 issues
- **Escalated:** 2 issues

## Recommendations

### Action Items
1. Address service reliability concerns (3 negative mentions)
2. Create FAQ for common pricing questions
3. Engage with positive mentions for advocacy
4. Monitor competitor mention trends

### Opportunities
- Leverage positive sentiment for testimonials
- Engage with industry influencers
- Expand content on popular topics
- Optimize posting times based on engagement

---
*Next summary: 2024-01-28*
```

## Error Handling

### Platform API Errors
```python
def handle_platform_error(platform, error):
    """Handle platform-specific errors"""

    if platform == 'twitter':
        if 'rate limit' in str(error).lower():
            wait_time = extract_reset_time(error.headers)
            schedule_retry(platform, wait_time)

    elif platform == 'facebook':
        if 'token expired' in str(error).lower():
            refresh_facebook_token()

    log_error(f"{platform}_error", {
        'error': str(error),
        'timestamp': datetime.now().isoformat()
    })
```

### Data Validation
```python
def validate_mention_data(mention):
    """Ensure mention data is complete"""

    required_fields = ['id', 'content', 'author', 'platform', 'timestamp']

    for field in required_fields:
        if field not in mention:
            raise ValidationError(f"Missing required field: {field}")

    # Validate timestamp
    try:
        datetime.fromisoformat(mention['timestamp'])
    except ValueError:
        raise ValidationError("Invalid timestamp format")

    return True
```

## Performance Optimization

### Efficient Search Strategies
```python
def optimize_keyword_search(keywords):
    """Optimize keywords for platform APIs"""

    # Group by platform
    optimized = {
        'twitter': [],
        'facebook': [],
        'instagram': [],
        'linkedin': []
    }

    for keyword in keywords:
        # Twitter-specific optimization
        if keyword.startswith('@'):
            optimized['twitter'].append(f"to:{keyword}")

        # Facebook-specific optimization
        elif keyword.startswith('#'):
            optimized['facebook'].append(f"#{keyword}")

        # Add to all platforms
        else:
            for platform in optimized:
                optimized[platform].append(keyword)

    return optimized
```

### Caching Strategy
- Cache mention data for 5 minutes
- Cache sentiment analysis results
- Cache author information
- Cache keyword search results

## Best Practices

1. **Response Time**: Respond to negative mentions within 1 hour
2. **Tone Matching**: Match brand voice in responses
3. **Escalation**: Escalate critical issues immediately
4. **Documentation**: Log all interactions for analysis
5. **Proactive**: Monitor trends and adjust strategy
6. **Compliance**: Follow platform terms of service

## Troubleshooting

### Common Issues
1. **"No mentions found"**
   - Check keyword configuration
   - Verify API credentials
   - Review rate limit status

2. **"False positives"**
   - Refine keyword matching
   - Add negative keywords
   - Improve context analysis

3. **"Missing alerts"**
   - Check sentiment analysis
   - Verify priority rules
   - Review alert generation logic

4. **"Platform sync issues"**
   - Check API tokens
   - Verify platform permissions
   - Review rate limits

## Security & Privacy

1. **Data Protection**: Secure mention data storage
2. **Privacy Compliance**: Respect user privacy
3. **Access Control**: Limit sensitive mention access
4. **Data Retention**: Define retention policies
5. **API Security**: Secure all API credentials