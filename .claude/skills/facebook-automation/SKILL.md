---
name: facebook-automation
description: Automate Facebook Page management including posting content, monitoring engagement, scheduling posts, and generating reports. Use when Claude needs to: (1) Post text or image content to Facebook Pages, (2) Track post performance metrics, (3) Schedule future posts, (4) Generate engagement analytics reports
license: Complete terms in LICENSE.txt
---

# Facebook Automation

This skill provides comprehensive Facebook Page automation capabilities for content posting, engagement monitoring, and performance analytics.

## Quick Start

Post content to Facebook:
```bash
/facebook-post "Your message here" [--image /path/to/image] [--page "Page Name"]
```

Schedule a post:
```bash
/facebook-schedule "2024-01-20 14:00" "Message" [--image /path/to/image]
```

Get engagement report:
```bash
/facebook-report [--period 7d] [--page "Page Name"]
```

## Core Features

### 1. Content Posting

**Text Posts:**
- Post plain text updates to Facebook Pages
- Support for emojis and formatting
- Character limit checking (Facebook limit: 63,206)

**Image Posts:**
- Upload single or multiple images
- Auto-resize if needed (max 10MB per image)
- Supported formats: JPG, PNG, GIF, BMP

**Post Structure:**
```markdown
---
type: facebook_post
page: "Your Page Name"
post_type: text|image|video
scheduled: false
status: draft|posted|scheduled
---

[Post content here]
```

### 2. Engagement Monitoring

**Metrics Tracked:**
- Likes count
- Comments count
- Shares count
- Reach (total/organic)
- Engagement rate
- Click-through rate

**Real-time Updates:**
- Monitor for new comments
- Track comment sentiment
- Identify trending posts
- Alert for unusual activity

### 3. Post Scheduling

**Scheduling Options:**
- Specific date/time
- Recurring posts (daily, weekly, monthly)
- Optimal time suggestions based on audience
- Bulk scheduling from content calendar

**Time Zone Support:**
- Automatic timezone detection
- Manual timezone override
- Local time display

### 4. Analytics & Reporting

**Daily Summary:**
- Posts published
- Total engagement
- Top performing content
- Audience growth

**Weekly/Monthly Reports:**
- Engagement trends
- Best posting times
- Content performance analysis
- Audience demographics
- Growth metrics

**Report Format (Markdown):**
```markdown
# Facebook Performance Report
**Period:** 2024-01-15 to 2024-01-21
**Page:** Your Page Name

## Key Metrics
- Total Posts: 15
- Total Reach: 5,432
- Engagement Rate: 3.2%
- New Followers: 47

## Top Posts
1. [Post title] - 234 likes, 45 comments
2. [Post title] - 189 likes, 32 comments

## Engagement Trends
[Chart or data visualization]
```

## Implementation Details

### Authentication

1. Facebook Page Access Token required
2. Permissions needed:
   - `pages_read_engagement`
   - `pages_manage_posts`
   - `pages_manage_engagement`
3. Token renewal handling
4. Secure credential storage

### API Integration

**Facebook Graph API v18.0+**
- Endpoint: `/{page-id}/posts`
- Rate limiting: 200 calls per hour
- Error handling for API limits
- Retry logic with exponential backoff

### Data Storage

**Local Storage Structure:**
```
/Vault/Social Media/Facebook/
├── posts/
│   ├── 2024-01/
│   │   ├── post-001.md
│   │   └── post-002.md
├── analytics/
│   ├── daily-2024-01-21.md
│   └── weekly-2024-W03.md
├── schedules/
│   └── pending-posts.json
└── config/
    └── pages.json
```

### Content Templates

**Post Templates:**
- Announcement template
- Question template
- Behind-the-scenes template
- Product showcase template

**Caption Guidelines:**
- First 125 characters crucial
- Include call-to-action
- Use relevant hashtags (3-5 max)
- Tag relevant pages/people

## Commands Reference

### Posting Commands
```bash
# Post text
/facebook-post "Hello world!" --page "My Page"

# Post with image
/facebook-post "Check this out!" --image ./photo.jpg --page "My Page"

# Post to multiple pages
/facebook-post "Big news!" --pages "Page1,Page2,Page3"
```

### Scheduling Commands
```bash
# Schedule specific time
/facebook-schedule "2024-01-20 14:00" "Content here"

# Schedule optimal time
/facebook-schedule "auto" "Content here" --optimize

# Schedule recurring
/facebook-schedule "daily 09:00" "Good morning!" --recurring
```

### Monitoring Commands
```bash
# Get real-time stats
/facebook-stats --live

# Check specific post
/facebook-post-details post-id-123

# Monitor comments
/facebook-comments --unreplied
```

### Reporting Commands
```bash
# Daily report
/facebook-report --period 1d

# Custom range
/facebook-report --start 2024-01-01 --end 2024-01-31

# Export data
/facebook-export --format csv --file facebook-data.csv
```

## Best Practices

1. **Posting Times:**
   - Peak hours: 9-11 AM, 2-4 PM
   - Test different times for your audience
   - Use scheduling for consistency

2. **Content Mix:**
   - 80% value, 20% promotional
   - Mix of text, images, and videos
   - User-generated content when possible

3. **Engagement:**
   - Respond to comments within 2 hours
   - Like comments to acknowledge
   - Ask questions to boost engagement

4. **Hashtags:**
   - Use 2-5 relevant hashtags
   - Mix popular and niche tags
   - Create branded hashtags

5. **Analytics:**
   - Review metrics weekly
   - A/B test content types
   - Adjust strategy based on data

## Error Handling

### Common Issues
- **Token expired**: Auto-renew or prompt for re-auth
- **Image too large**: Auto-resize or compress
- **Rate limit hit**: Queue requests and retry
- **Page not found**: Verify page ID and permissions

### Recovery Strategies
- Maintain post queue for failed uploads
- Backup scheduled posts locally
- Log all errors for debugging
- Fallback to manual posting if needed

## Security Considerations

1. Store access tokens securely
2. Use environment variables for credentials
3. Implement token rotation
4. Log all API activities
5. Regular security audits

## Compliance Notes

- Follow Facebook Community Standards
- Respect copyright and trademarks
- Disclose sponsored content
- Comply with GDPR for EU users
- Maintain transparency with audience