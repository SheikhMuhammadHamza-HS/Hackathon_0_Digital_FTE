---
name: x-twitter-automation
description: Post tweets and monitor mentions on X (Twitter) with API v2 integration, engagement automation, and approval workflows. Use when Claude needs to: (1) Post scheduled content, (2) Monitor and respond to mentions, (3) Track analytics and engagement, (4) Manage social media presence, (5) Generate mention alerts for review
license: Complete terms in LICENSE.txt
---

# X (Twitter) Automation

This skill provides comprehensive X (Twitter) automation including posting, monitoring, engagement tracking, and analytics with strict HITL approval workflows.

## Prerequisites

### Environment Configuration
Required `.env` variables:
```bash
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_SECRET=your_access_secret
X_BEARER_TOKEN=your_bearer_token
```

### API Requirements
- X API v2 access
- Elevated access for posting
- Read/write permissions
- Webhook setup for real-time mentions (optional)

## Quick Start

Post a tweet:
```bash
/x-post "Hello world! #automation"

Schedule a tweet:
```bash
/x-schedule "2024-01-20 14:00" "Big news coming soon!"

Check mentions:
```bash
/x-monitor-mentions

Get analytics:
```bash
/x-analytics --period 7d
```

## Core Features

### 1. Tweet Posting

**Single Tweet Posting:**
```python
def post_tweet(text, media_ids=None, reply_to=None):
    """Post a tweet via X API v2"""

    endpoint = "https://api.twitter.com/2/tweets"

    data = {
        "text": text
    }

    if media_ids:
        data["media"] = {"media_ids": media_ids}

    if reply_to:
        data["reply"] = {"in_reply_to_tweet_id": reply_to}

    response = make_request("POST", endpoint, json=data)
    return response["data"]["id"]
```

**Tweet Validation:**
- Character limit: 280 characters
- No prohibited content
- Respect rate limits (300 tweets/3hrs)
- Check for duplicate content

### 2. Scheduling System

**Scheduled Content Structure:**
```markdown
---
scheduled_time: 2024-01-20T14:00:00Z
status: scheduled
tweet_id: null
type: original
---

# Scheduled Tweet - 2024-01-20 14:00

**Content:** Big news coming soon! 🚀
**Hashtags:** #innovation #tech
**Media:** [optional image/video]
**Approval:** Auto-approved (scheduled content)
```

**Auto-Post Rules:**
- ✅ Pre-scheduled content → Auto-post allowed
- ❌ Replies to mentions → Requires approval
- ❌ Direct mentions → Requires approval
- ❌ Sensitive topics → Requires approval

### 3. Mention Monitoring

**Monitoring Cycle:** Every 30 minutes

**Mention Processing:**
```python
def monitor_mentions():
    """Check for new mentions and create alerts"""

    mentions = get_mentions(since_last_check)

    for mention in mentions:
        alert_data = {
            'mention_id': mention['id'],
            'author': mention['author']['username'],
            'text': mention['text'],
            'created_at': mention['created_at'],
            'type': classify_mention(mention),
            'priority': assess_priority(mention)
        }

        create_mention_alert(alert_data)
```

**Mention Classification:**
- **Question**: Needs response
- **Complaint**: High priority
- **Praise**: Can like/retweet
- **Spam**: Ignore/report
- **Media**: Check for brand mentions

### 4. Engagement Automation

**Allowed Auto-Actions:**
- Like positive mentions
- Retweet brand mentions
- Follow back verified accounts
- Like scheduled post interactions

**Approval Required:**
- Reply to any mention
- Quote tweets
- Direct messages
- Sensitive content interactions

### 5. Analytics Tracking

**Metrics Collected:**
- Impressions per tweet
- Engagement rate
- Follower growth
- Top performing content
- Best posting times
- Hashtag performance

**Analytics Dashboard Update:**
```markdown
## X (Twitter) Performance - Week 2024-W03

### Summary
- **Tweets Posted:** 7
- **Total Impressions:** 12,450
- **Engagement Rate:** 4.2%
- **New Followers:** 89
- **Top Tweet:** [link] - 2,340 impressions

### Engagement Breakdown
| Metric | Count | Rate |
|--------|-------|------|
| Likes | 523 | 4.2% |
| Retweets | 89 | 0.7% |
| Replies | 45 | 0.4% |
| Profile Clicks | 123 | 1.0% |
```

## Implementation Details

### API Client Setup

```python
import tweepy
import os
from datetime import datetime, timedelta

class XTwitterClient:
    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=os.getenv('X_BEARER_TOKEN'),
            consumer_key=os.getenv('X_API_KEY'),
            consumer_secret=os.getenv('X_API_SECRET'),
            access_token=os.getenv('X_ACCESS_TOKEN'),
            access_token_secret=os.getenv('X_ACCESS_SECRET')
        )
        self.last_mention_check = datetime.now() - timedelta(minutes=30)

    def post_tweet(self, text, **kwargs):
        """Post tweet with error handling"""
        try:
            response = self.client.create_tweet(text=text, **kwargs)
            log_tweet_post(response.data['id'], text)
            return response.data['id']
        except tweepy.TweepyException as e:
            log_error('tweet_post_failed', str(e))
            raise
```

### Mention Alert System

**Alert File Format (`/Needs_Action/TWITTER_mention_YYYY-MM-DD.md`):**
```markdown
---
type: twitter_mention_alert
mention_id: 1234567890
author: @username
priority: high
created_at: 2024-01-21T14:30:00Z
classification: question
status: pending
---

# Twitter Mention Alert - 2024-01-21

## Mention Details
- **Author:** @username (John Doe)
- **Tweet ID:** 1234567890
- **Posted:** 2024-01-21 14:30
- **Text:** "Hey @yourhandle, when is the new feature launching?"
- **Classification:** Question
- **Priority:** High

## Suggested Actions
1. **Reply**: "Thanks for asking! The feature launches next week. Stay tuned! 🚀"
2. **Like**: Yes
3. **Retweet**: No
4. **Follow**: Maybe (check profile)

## Quick Reply Options
- [ ] "Coming soon! We'll announce the exact date this week."
- [ ] "Great question! Sign up for our newsletter for updates."
- [ ] Custom reply: _________________________

## Approval Required
**Move to `/Pending_Approval/` to authorize response**

---
*Auto-generated at 2024-01-21 14:35*
```

### Dashboard Integration

**Dashboard.md Section:**
```markdown
## X (Twitter) Status

### Recent Activity
- **Last Post:** 2 hours ago - "New feature announcement!"
- **Mentions Pending:** 3
- **Engagement Rate:** 4.2% (↑0.3%)
- **Followers:** 5,234 (↑89 this week)

### Pending Actions
- [ ] Reply to @user123 about feature launch
- [ ] Review mention from @techblog
- [ ] Approve scheduled posts for tomorrow

### Performance
- **Best Time:** 2-4 PM EST
- **Top Hashtag:** #automation
- **Top Tweet:** "Our biggest update yet..." - 2.3k impressions
```

## Commands Reference

### Posting Commands
```bash
# Post immediate tweet
/x-post "Hello world! #automation"

# Post with image
/x-post "Check this out!" --image ./image.jpg

# Post thread
/x-post-thread "Thread part 1/3" --thread ./thread_content.md

# Schedule tweet
/x-schedule "2024-01-20 14:00" "Big news coming!"
```

### Monitoring Commands
```bash
# Check mentions now
/x-monitor-mentions

# Start continuous monitoring
/x-monitor-start

# Stop monitoring
/x-monitor-stop

# Check monitoring status
/x-monitor-status
```

### Engagement Commands
```bash
# Like a tweet
/x-like --tweet 1234567890

# Retweet
/x-retweet --tweet 1234567890

# Reply (requires approval)
/x-reply --tweet 1234567890 --text "Thanks for sharing!"

# Follow user
/x-follow --user @username
```

### Analytics Commands
```bash
# Get week analytics
/x-analytics --period 7d

# Get tweet performance
/x-tweet-stats --tweet 1234567890

# Export analytics
/x-export --format csv --period 30d

# Best posting times
/x-optimal-times --period 30d
```

## HITL Approval Workflow

### Approval Matrix

| Action | Auto-Allowed | Requires Approval |
|--------|--------------|-------------------|
| Scheduled posts | ✅ | ❌ |
| Replies to mentions | ❌ | ✅ |
| Direct messages | ❌ | ✅ |
| Quote tweets | ❌ | ✅ |
| Following users | ✅ (verified only) | ✅ (unverified) |
| Liking mentions | ✅ | ❌ |
| Retweeting mentions | ✅ (positive) | ✅ (all) |

### Approval File Creation

**For Sensitive Actions:**
```markdown
---
type: twitter_approval
action: reply
tweet_id: 1234567890
author: @username
proposed_reply: "Thanks for your feedback! We'll look into this."
risk_level: low
timestamp: 2024-01-21T14:30:00Z
---

# Twitter Action Approval

## Action Details
- **Type:** Reply to tweet
- **Tweet:** 1234567890 by @username
- **Proposed Reply:** "Thanks for your feedback! We'll look into this."
- **Risk Assessment:** Low

## Approval Checklist
- [ ] Reply is professional and on-brand
- [ ] No confidential information shared
- [ ] Tone is appropriate
- [ ] No legal or compliance issues

## Action Required
**Move to `/Approved/` to authorize this action**

---
*Generated: 2024-01-21 14:30*
```

## Error Handling

### Rate Limit Management
```python
def handle_rate_limits(response):
    """Handle Twitter API rate limits"""

    if response.status == 429:
        reset_time = int(response.headers['x-rate-limit-reset'])
        wait_time = reset_time - int(time.time())

        log_error('rate_limit_hit', f"Waiting {wait_time} seconds")
        time.sleep(wait_time + 1)
        return True

    return False
```

### Common Errors
- **Authentication failed**: Check .env credentials
- **Duplicate tweet**: Modify content slightly
- **Media upload failed**: Check file size/format
- **Character limit exceeded**: Truncate or edit
- **Sensitive content flagged**: Review and revise

## Logging System

### Log Entry Format
**Location:** `/Logs/YYYY-MM-DD.json`

```json
{
  "timestamp": "2024-01-21T14:30:00Z",
  "operation": "tweet_posted",
  "tweet_id": "1234567890",
  "content": "Hello world! #automation",
  "type": "scheduled",
  "auto_posted": true,
  "impressions": null,
  "operator": "claude"
}
```

### Log Categories
- `tweet_posted` - Tweet successfully posted
- `tweet_scheduled` - Tweet scheduled for future
- `mention_detected` - New mention found
- `engagement_action` - Like/retweet/follow
- `approval_required` - Action awaiting approval
- `error` - Any error encountered

## Performance Optimization

### Batch Processing
```python
def process_mentions_batch(mentions):
    """Process multiple mentions efficiently"""

    # Group by priority
    high_priority = [m for m in mentions if m['priority'] == 'high']
    normal_priority = [m for m in mentions if m['priority'] == 'normal']

    # Process high priority first
    for mention in high_priority:
        create_mention_alert(mention)

    # Batch process normal priority
    batch_create_alerts(normal_priority)
```

### Caching Strategy
- Cache tweet performance data
- Cache user information
- Cache analytics calculations
- Cache mention classifications

## Security & Compliance

### Content Moderation
```python
def moderate_content(text):
    """Check content before posting"""

    # Check for prohibited content
    prohibited = ['spam', 'hate', 'illegal']
    for word in prohibited:
        if word.lower() in text.lower():
            raise ContentModerationError(f"Prohibited content detected: {word}")

    # Check for confidential information
    if contains_confidential_info(text):
        raise SecurityError("Confidential information detected")

    return True
```

### Brand Safety
- Maintain consistent brand voice
- Avoid controversial topics
- Review hashtag relevance
- Fact-check claims

## Best Practices

1. **Timing**: Post during peak engagement hours
2. **Frequency**: Maintain consistent posting schedule
3. **Engagement**: Respond promptly to mentions
4. **Content**: Mix promotional and value content
5. **Hashtags**: Use 2-3 relevant hashtags
6. **Analytics**: Review performance weekly
7. **Approval**: Never skip approval for sensitive actions

## Troubleshooting

### Common Issues
1. **"Authentication failed"**
   - Verify .env credentials
   - Check API key permissions
   - Regenerate tokens if needed

2. **"Rate limit exceeded"**
   - Check rate limit status
   - Wait for reset time
   - Implement backoff strategy

3. **"Mentions not detected"**
   - Verify webhook setup
   - Check API permissions
   - Review last check time

4. **"Scheduled post failed"**
   - Check scheduled time
   - Verify content validation
   - Review error logs

## Integration Points

### With CEO Briefing
```python
def update_ceo_briefing():
    """Update CEO briefing with Twitter metrics"""

    metrics = get_weekly_analytics()

    briefing_update = {
        'twitter_followers': metrics['followers'],
        'twitter_engagement': metrics['engagement_rate'],
        'top_performing_tweet': metrics['top_tweet']
    }

    update_ceo_briefing_section('social_media', briefing_update)
```

### With Dashboard
```python
def update_dashboard():
    """Update main dashboard with Twitter status"""

    status = {
        'last_post': get_last_post_time(),
        'pending_mentions': count_pending_mentions(),
        'engagement_rate': get_current_engagement_rate(),
        'follower_growth': get_weekly_follower_growth()
    }

    update_dashboard_section('twitter', status)
```

## Compliance Notes

- Follow X Terms of Service
- Disclose automated content where required
- Respect copyright and trademarks
- Comply with advertising guidelines
- Maintain data privacy standards
- Regular compliance reviews