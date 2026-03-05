# [UC-MKT-001] Campaign Strategy Development

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-MKT-001 |
| **Domain** | marketing |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P1-High |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Enables marketing teams to develop comprehensive campaign strategies including audience segmentation, messaging frameworks, channel selection, and success metrics. The agent analyzes historical campaign data, market trends, and audience behavior to recommend optimal strategies.

### Data Models

- **Model**: Campaign (repo: platform-backend, path: `backend/src/domain/models/Campaign.js`)
  - Fields: `name: string`, `status: enum[draft|active|paused|completed]`, `strategy: object`, `target_audience: object`, `channels: array`, `kpis: object`
- **Model**: Audience (repo: platform-backend, path: `backend/src/domain/models/Audience.js`)
  - Fields: `name: string`, `criteria: object`, `size: number`, `demographics: object`

### Services

- **Service**: campaignService (repo: platform-backend, path: `backend/src/application/services/campaignService.js`)
  - Methods: `create()`, `updateStrategy()`, `analyzePerformance()`
- **Service**: audienceService (repo: platform-backend, path: `backend/src/application/services/audienceService.js`)
  - Methods: `segment()`, `analyze()`, `recommend()`

### Routes/Endpoints

- `POST /api/campaigns/strategy` -> `campaignService.updateStrategy()`
- `GET /api/audiences/segments` -> `audienceService.segment()`
- `POST /api/campaigns/analyze` -> `campaignService.analyzePerformance()`

### Frontend Components

- **Page**: CampaignStrategyPage (repo: engage-ai-flow, path: `client/src/pages/CampaignStrategyPage.tsx`)
- **Component**: AudienceSegmentBuilder (repo: engage-ai-flow, path: `client/src/components/AudienceSegmentBuilder.tsx`)

## Acceptance Criteria

1. GIVEN a marketing team with campaign objectives
   WHEN they request strategy development via POST /api/campaigns/strategy
   THEN the system analyzes audience data and returns recommended strategy with channels, messaging, and KPIs

2. GIVEN historical campaign data exists
   WHEN strategy is requested
   THEN recommendations include insights from past performance with confidence scores >= 0.7

3. GIVEN invalid audience criteria
   WHEN strategy development is attempted
   THEN returns 400 with validation message indicating required audience parameters

## Required Skills

1. **copywriting** - new
   - Spec: docs/specs/skills/copywriting.md
   - Generate compelling campaign messaging and copy

2. **audience_targeting** - new
   - Spec: docs/specs/skills/audience_targeting.md
   - Segment and target audiences based on behavioral and demographic data

## Required Agent Capabilities

- **Primary**: `marketing_agent` - capabilities: [copywriting, campaign_strategy, audience_targeting]
- **Secondary**: `analytics_agent` - capabilities: [analytics, campaign_analytics]

## RAG Chunk References

- `category: marketing` + `source_file CONTAINS 'services/campaignService'`
- `category: marketing` + `domain: campaigns`
- `category: usecase` + `domain: marketing`

## Related Use Cases

- **Depends on**: none (entry point)
- **Enables**: UC-MKT-002 (A/B Testing - requires strategy), UC-CAM-001 (Campaign Creation)
- **Conflicts with**: none

## Implementation Notes

- Strategy recommendations use ML scoring from historical data
- Audience segmentation integrates with ClickHouse analytics
- Frontend uses React with Tailwind CSS
- Authentication via JWT with `x-company-id` header
