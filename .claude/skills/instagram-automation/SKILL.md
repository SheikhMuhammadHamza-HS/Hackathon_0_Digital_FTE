---
name: instagram-automation
description: Automate Instagram content management including scheduling posts, auto-adding hashtags, monitoring engagement metrics, and generating content summaries. Use when Claude needs to: (1) Schedule and post Instagram content with images and captions, (2) Automatically add relevant hashtags, (3) Track engagement performance, (4) Generate weekly content analytics
license: Complete terms in LICENSE.txt
---

# Instagram Automation

This skill provides comprehensive Instagram automation for content scheduling, hashtag optimization, engagement tracking, and performance analytics.

## Quick Start

Post to Instagram:
```bash
/instagram-post "Caption here" --image /path/to/image [--hashtags "tag1,tag2,tag3"]
```

Schedule a post:
```bash
/instagram-schedule "2024-01-20 18:00" "Caption" --image ./photo.jpg
```

Get weekly summary:
```bash
/instagram-summary --week 2024-W03
```

## Core Features

### 1. Content Scheduling & Posting

**Image Requirements:**
- Aspect ratio: 1:1 (square), 4:5 (portrait), or 1.91:1 (landscape)
- Max file size: 30MB
- Supported formats: JPG, PNG
- Recommended resolution: 1080x1080px

**Caption Guidelines:**
- First line crucial for engagement
- Max 2,200 characters
- Include call-to-action
- Break into readable paragraphs

**Post Structure:**
```markdown
---
type: instagram_post
media_type: image|video|carousel
scheduled: 2024-01-20 18:00
status: draft|scheduled|posted
filters: "Clarendon"
---

[Caption text]

#hashtags
```

### 2. Automatic Hashtag Generation

**Hashtag Strategy:**
- 20-30 hashtags per post (Instagram limit)
- Mix of popularity levels:
  - Super popular (1M+ posts): 3-5 tags
  - Popular (100k-1M): 5-8 tags
  - Niche (10k-100k): 8-12 tags
  - Micro-niche (<10k): 4-6 tags

**Smart Hashtag Selection:**
- Analyze image content
- Extract keywords from caption
- Industry-specific tags
- Location-based tags
- Trending hashtags

**Hashtag Groups:**
```yaml
photography:
  - #photography
  - #photooftheday
  - #instagood

business:
  - #entrepreneur
  - #business
  - #startup

local:
  - #newyork
  - #nyc
  - #brooklyn
```

### 3. Engagement Monitoring

**Metrics Tracked:**
- Likes count
- Comments count
- Saves/bookmarks
- Shares
- Reach
- Impressions
- Engagement rate
- Story views (for stories)
- Follower growth

**Real-time Alerts:**
- Engagement spikes
- Negative comments detected
- Unusual activity patterns
- Milestone achievements

**Performance Indicators:**
- Best posting times
- Top performing hashtags
- Most engaging content types
- Audience demographics

### 4. Weekly Content Summary

**Summary Components:**
- Posts published this week
- Total engagement metrics
- Top performing posts
- Hashtag performance
- Follower growth
- Engagement trends
- Content recommendations

**Report Format:**
```markdown
# Instagram Weekly Summary
**Week:** 2024-W03 (Jan 15-21)
**Account:** @yourusername

## Performance Overview
- Posts: 7
- Total Likes: 1,234
- Total Comments: 89
- Engagement Rate: 4.2%
- New Followers: 52

## Top Posts
1. 📸 Photo of [subject] - 234 likes, 12 comments
2. 🎬 Video about [topic] - 189 likes, 8 comments

## Hashtag Performance
- #yourbrand: 45 uses, 3.2% engagement
- #industry: 23 uses, 2.8% engagement

## Insights & Recommendations
- Best posting time: 6-7 PM
- Video content outperforms photos by 23%
- Audience most active on weekdays
```

## Implementation Details

### Instagram Basic Display API

**Authentication:**
- OAuth 2.0 flow required
- Permissions needed:
  - `instagram_basic`
  - `instagram_content_publish`
  - `instagram_manage_comments`
- Token refresh handling

**API Limitations:**
- 200 posts per hour per user
- 60 days media data retention
- No direct hashtag analytics
- Limited engagement data

### Content Storage Structure

```
/Vault/Social Media/Instagram/
├── posts/
│   ├── 2024-01/
│   │   ├── post-001.md
│   │   └── post-002.md
├── media/
│   ├── original/
│   └── processed/
├── analytics/
│   ├── daily-2024-01-21.md
│   └── weekly-2024-W03.md
├── hashtags/
│   ├── groups.yaml
│   └── performance.json
└── schedules/
    └── queue.json
```

### Image Processing

**Auto-optimization:**
- Resize to optimal dimensions
- Compress while maintaining quality
- Add watermark if configured
- Generate multiple formats

**Filter Options:**
- Instagram-native filters
- Custom filter presets
- Brand color schemes
- Consistent aesthetic rules

### Hashtag Management

**Dynamic Hashtag Pools:**
- Trending hashtags (updated daily)
- Seasonal hashtags
- Industry-specific pools
- Location-based tags
- Branded hashtags

**Performance Tracking:**
- Track reach per hashtag
- Monitor hashtag saturation
- Identify declining tags
- Discover new opportunities

## Commands Reference

### Posting Commands
```bash
# Immediate post
/instagram-post "Amazing sunset!" --image ./sunset.jpg

# Post with auto hashtags
/instagram-post "New product launch" --image ./product.jpg --auto-hashtags

# Post with custom hashtags
/instagram-post "Check this out" --image ./photo.jpg --hashtags "tech,innovation,startup"

# Carousel post
/instagram-post "Multiple views" --images ./img1.jpg,./img2.jpg,./img3.jpg
```

### Scheduling Commands
```bash
# Schedule specific time
/instagram-schedule "2024-01-20 18:00" "Caption" --image ./photo.jpg

# Schedule optimal time
/instagram-schedule "optimal" "Caption" --image ./photo.jpg --auto-time

# Schedule series
/instagram-series "daily 09:00" "Good morning!" --template morning

# Schedule from content calendar
/instagram-schedule-from-calendar --file content-plan.csv
```

### Hashtag Commands
```bash
# Generate hashtags
/instagram-hashtags "Photography nature landscape" --count 20

# Analyze hashtag performance
/instagram-hashtag-stats #travel

# Create hashtag group
/instagram-hashtag-group "photography" "#photo,#nature,#landscape"

# Test hashtag combinations
/instagram-test-hashtags "brand,product,launch" --preview
```

### Analytics Commands
```bash
# Get current stats
/instagram-stats --live

# Post performance
/instagram-post-stats post-id-123

# Weekly summary
/instagram-summary --week 2024-W03

# Export data
/instagram-export --format csv --period 30d
```

## Content Strategy Templates

### Post Types
1. **Behind the Scenes** - 20% of content
2. **Educational** - 25% of content
3. **Entertaining** - 30% of content
4. **Promotional** - 15% of content
5. **User-Generated** - 10% of content

### Caption Templates
**Question Format:**
```
Hook line 🎯

Main content with value proposition

Question to engage audience? 👇

#hashtag1 #hashtag2 #hashtag3
```

**Storytelling Format:**
```
Opening hook that grabs attention 📖

[Story arc with beginning, middle, end]

Key takeaway or moral of the story

Call-to-action or question

#relevant #hashtags #here
```

## Best Practices

### Posting Strategy
1. **Consistency**: Post 1-2 times daily
2. **Timing**: Post when audience is most active
3. **Quality over quantity**: Maintain high standards
4. **Variety**: Mix content types regularly
5. **Engagement**: Respond within first hour

### Hashtag Strategy
1. Research relevant hashtags
2. Mix popularity levels
3. Create branded hashtags
4. Avoid banned/restricted tags
5. Update hashtag pools regularly

### Engagement Growth
1. Post Instagram Stories daily
2. Use interactive stickers
3. Go live weekly
4. Collaborate with others
5. Engage with similar accounts

## Error Handling

### Common Issues
- **Image format rejected**: Auto-convert to supported format
- **Caption too long**: Truncate with ellipsis
- **Hashtag limit exceeded**: Remove lowest performing tags
- **API rate limit**: Queue posts and retry
- **Upload failure**: Retry with different compression

### Recovery Procedures
- Maintain local backup of all content
- Queue failed posts for retry
- Log all errors with context
- Provide manual override options

## Security & Compliance

1. Secure credential storage
2. Respect Instagram ToS
3. Disclose sponsored content
4. Copyright compliance
5. Privacy considerations
6. Age-appropriate content
7. Community guidelines adherence