# [UC-SOC-002] Social Media Engagement Analysis

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SOC-002 |
| **Domain** | social_media |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P2-Medium |
| **Complexity** | H |
| **Status** | Spec |

## Domain Context

Analyzes social media engagement metrics across platforms including likes, shares, comments, reach, and sentiment. Provides insights on best-performing content, optimal posting times, and audience demographics. Generates actionable recommendations for improving engagement.

### Data Models

- **Model**: EngagementMetrics (repo: platform-backend, path: `backend/src/domain/models/EngagementMetrics.js`)
  - Fields: `post_id: ObjectId`, `platform: string`, `likes: number`, `shares: number`, `comments: number`, `reach: number`, `sentiment: number`, `timestamp: Date`
- **Model**: EngagementReport (repo: platform-backend, path: `backend/src/domain/models/EngagementReport.js`)
  - Fields: `period: string`, `total_engagement: number`, `top_posts: array`, `recommendations: array`

### Services

- **Service**: engagementService (repo: platform-backend, path: `backend/src/application/services/engagementService.js`)
  - Methods: `analyze()`, `getTopPosts()`, `getRecommendations()`, `trackMetrics()`
- **Service**: sentimentService (repo: platform-backend, path: `backend/src/application/services/sentimentService.js`)
  - Methods: `analyzeComments()`, `calculateSentiment()`

### Routes/Endpoints

- `GET /api/social/engagement/analyze` -> `engagementService.analyze()`
- `GET /api/social/engagement/top-posts` -> `engagementService.getTopPosts()`
- `GET /api/social/engagement/recommendations` -> `engagementService.getRecommendations()`
- `POST /api/social/engagement/track` -> `engagementService.trackMetrics()`

### Frontend Components

- **Page**: EngagementDashboard (repo: engage-ai-flow, path: `client/src/pages/EngagementDashboard.tsx`)
- **Component**: EngagementChart (repo: engage-ai-flow, path: `client/src/components/EngagementChart.tsx`)
- **Component**: SentimentAnalysis (repo: engage-ai-flow, path: `client/src/components/SentimentAnalysis.tsx`)

## Acceptance Criteria

1. GIVEN published social posts with engagement data
   WHEN GET /api/social/engagement/analyze is called with date range
   THEN returns aggregated metrics with platform breakdown and trend analysis

2. GIVEN engagement data for multiple posts
   WHEN GET /api/social/engagement/top-posts is requested
   THEN returns top 10 posts ranked by engagement score (weighted: likes*1 + shares*3 + comments*2)

3. GIVEN insufficient data (< 10 posts)
   WHEN requesting recommendations via GET /api/social/engagement/recommendations
   THEN returns 200 with message indicating more data needed for reliable recommendations

## Required Skills

1. **engagement_analysis** - new
   - Spec: docs/specs/skills/engagement_analysis.md
   - Analyze social media engagement patterns and trends

2. **analytics** - existing
   - Spec: docs/specs/skills/analytics.md
   - Track and analyze performance metrics

## Required Agent Capabilities

- **Primary**: `social_media_agent` - capabilities: [engagement_analysis, analytics]
- **Secondary**: `analytics_agent` - capabilities: [analytics, data_analysis]

## RAG Chunk References

- `category: social_media` + `source_file CONTAINS 'services/engagementService'`
- `category: analytics` + `domain: social`
- `category: usecase` + `domain: social_media`

## Related Use Cases

- **Depends on**: UC-SOC-001 (Social Calendar - requires published posts)
- **Enables**: UC-MKT-001 (Campaign Strategy - provides social insights)
- **Conflicts with**: none

## Implementation Notes

- Engagement data collected via platform webhooks and polling
- Sentiment analysis uses NLP model (BERT-based)
- ClickHouse stores time-series engagement data
- Kafka event `engagement.analyzed` emitted after analysis
- Frontend uses Chart.js for visualizations
- Real-time updates via WebSocket for live metrics
