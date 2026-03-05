# [UC-SOC-001] Social Media Content Calendar

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SOC-001 |
| **Domain** | social_media |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P2-Medium |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Enables social media teams to plan, schedule, and manage content across multiple platforms (Twitter, LinkedIn, Facebook, Instagram). The calendar provides visual timeline, content approval workflow, and automated posting with optimal timing recommendations.

### Data Models

- **Model**: SocialPost (repo: platform-backend, path: `backend/src/domain/models/SocialPost.js`)
  - Fields: `content: string`, `platform: enum[twitter|linkedin|facebook|instagram]`, `scheduled_at: Date`, `status: enum[draft|scheduled|published|failed]`, `media: array`, `hashtags: array`
- **Model**: ContentCalendar (repo: platform-backend, path: `backend/src/domain/models/ContentCalendar.js`)
  - Fields: `name: string`, `company_id: ObjectId`, `posts: array`, `month: string`, `year: number`

### Services

- **Service**: socialPostService (repo: platform-backend, path: `backend/src/application/services/socialPostService.js`)
  - Methods: `create()`, `schedule()`, `publish()`, `getCalendar()`
- **Service**: platformIntegrationService (repo: platform-backend, path: `backend/src/application/services/platformIntegrationService.js`)
  - Methods: `postToTwitter()`, `postToLinkedIn()`, `postToFacebook()`, `postToInstagram()`

### Routes/Endpoints

- `POST /api/social/posts` -> `socialPostService.create()`
- `GET /api/social/calendar` -> `socialPostService.getCalendar()`
- `PUT /api/social/posts/:id/schedule` -> `socialPostService.schedule()`
- `POST /api/social/posts/:id/publish` -> `socialPostService.publish()`

### Frontend Components

- **Page**: SocialCalendarPage (repo: engage-ai-flow, path: `client/src/pages/SocialCalendarPage.tsx`)
- **Component**: CalendarGrid (repo: engage-ai-flow, path: `client/src/components/CalendarGrid.tsx`)
- **Component**: PostEditor (repo: engage-ai-flow, path: `client/src/components/PostEditor.tsx`)

## Acceptance Criteria

1. GIVEN a social media manager
   WHEN they create a post via POST /api/social/posts with platform and scheduled_at
   THEN post is saved with status 'scheduled' and appears in calendar view

2. GIVEN a scheduled post with scheduled_at in the past
   WHEN the scheduler runs
   THEN post is published to the specified platform and status updated to 'published'

3. GIVEN invalid platform credentials
   WHEN attempting to publish via POST /api/social/posts/:id/publish
   THEN returns 400 with message indicating authentication required for platform

## Required Skills

1. **content_calendar** - new
   - Spec: docs/specs/skills/content_calendar.md
   - Plan and organize content across time periods

2. **social_posting** - new
   - Spec: docs/specs/skills/social_posting.md
   - Publish and manage content on social media platforms

## Required Agent Capabilities

- **Primary**: `social_media_agent` - capabilities: [social_posting, content_calendar]
- **Secondary**: `marketing_agent` - capabilities: [copywriting, content_creation]

## RAG Chunk References

- `category: social_media` + `source_file CONTAINS 'services/socialPostService'`
- `category: social_media` + `domain: social`
- `category: usecase` + `domain: social_media`

## Related Use Cases

- **Depends on**: none (entry point)
- **Enables**: UC-SOC-002 (Engagement Analysis - generates data)
- **Conflicts with**: none

## Implementation Notes

- Scheduler runs every 5 minutes checking for posts to publish
- Platform APIs use OAuth 2.0 for authentication
- Media files stored in S3 with CDN
- Kafka event `social.post.published` emitted after successful publish
- Frontend uses FullCalendar library for calendar view
