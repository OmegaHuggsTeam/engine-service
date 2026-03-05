# [UC-MKT-002] A/B Testing Campaign Optimization

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-MKT-002 |
| **Domain** | marketing |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P1-High |
| **Complexity** | H |
| **Status** | Spec |

## Domain Context

Enables marketers to create and analyze A/B tests for campaigns, comparing different messaging, timing, channels, and audience segments. The system automatically splits audiences, tracks performance metrics, and determines statistical significance to identify winning variants.

### Data Models

- **Model**: ABTest (repo: platform-backend, path: `backend/src/domain/models/ABTest.js`)
  - Fields: `name: string`, `campaign_id: ObjectId`, `variants: array`, `status: enum[draft|running|completed]`, `winner: string`, `confidence: number`
- **Model**: Variant (repo: platform-backend, path: `backend/src/domain/models/Variant.js`)
  - Fields: `name: string`, `content: object`, `audience_split: number`, `metrics: object`

### Services

- **Service**: abTestService (repo: platform-backend, path: `backend/src/application/services/abTestService.js`)
  - Methods: `create()`, `start()`, `analyze()`, `determineWinner()`
- **Service**: analyticsService (repo: platform-backend, path: `backend/src/application/services/analyticsService.js`)
  - Methods: `trackVariantPerformance()`, `calculateSignificance()`

### Routes/Endpoints

- `POST /api/abtests` -> `abTestService.create()`
- `POST /api/abtests/:id/start` -> `abTestService.start()`
- `GET /api/abtests/:id/results` -> `abTestService.analyze()`
- `POST /api/abtests/:id/winner` -> `abTestService.determineWinner()`

### Frontend Components

- **Page**: ABTestPage (repo: engage-ai-flow, path: `client/src/pages/ABTestPage.tsx`)
- **Component**: VariantComparison (repo: engage-ai-flow, path: `client/src/components/VariantComparison.tsx`)
- **Component**: StatisticalSignificance (repo: engage-ai-flow, path: `client/src/components/StatisticalSignificance.tsx`)

## Acceptance Criteria

1. GIVEN an active campaign
   WHEN marketer creates A/B test via POST /api/abtests with 2+ variants
   THEN test is created with audience split, variants saved, and returns 201

2. GIVEN a running A/B test with sufficient data (n >= 100 per variant)
   WHEN GET /api/abtests/:id/results is called
   THEN returns performance metrics and statistical significance (p-value < 0.05 for winner)

3. GIVEN insufficient audience size for requested variants
   WHEN attempting to start test via POST /api/abtests/:id/start
   THEN returns 400 with message indicating minimum audience requirements

## Required Skills

1. **a_b_testing** - new
   - Spec: docs/specs/skills/a_b_testing.md
   - Design and analyze A/B tests with statistical rigor

2. **analytics** - existing
   - Spec: docs/specs/skills/analytics.md
   - Track and analyze campaign performance metrics

## Required Agent Capabilities

- **Primary**: `marketing_agent` - capabilities: [a_b_testing, campaign_strategy, analytics]
- **Secondary**: `analytics_agent` - capabilities: [analytics, statistical_analysis]

## RAG Chunk References

- `category: marketing` + `source_file CONTAINS 'services/abTestService'`
- `category: analytics` + `domain: campaigns`
- `category: usecase` + `domain: marketing`

## Related Use Cases

- **Depends on**: UC-MKT-001 (Campaign Strategy - requires campaign), UC-CAM-001 (Campaign Creation)
- **Enables**: UC-CAM-003 (Campaign Analytics - provides test data)
- **Conflicts with**: none

## Implementation Notes

- Statistical significance calculated using chi-square test
- Minimum sample size: 100 conversions per variant
- Kafka event `abtest.completed` emitted when winner determined
- Frontend uses D3.js for visualization
- Real-time updates via WebSocket for running tests
