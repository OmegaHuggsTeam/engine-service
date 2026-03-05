# [UC-CAM-003] Dashboard de Analytics de Campanha

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-CAM-003 |
| **Domain** | campaigns |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P2-Medium |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Exibe metricas agregadas de performance de campanhas incluindo taxas de entrega, abertura, clique e conversao. Utiliza ClickHouse para queries analiticas de alta performance e apresenta dados em dashboard com filtros temporais e comparativos.

### Data Models

- **Model**: CampaignAnalytics (repo: platform-backend, path: `backend/src/domain/models/CampaignAnalytics.js`)
  - Fields: `campaign_id: ObjectId`, `sent: number`, `delivered: number`, `opened: number`, `clicked: number`, `converted: number`, `revenue: number`
- **Model**: CampaignSmsSummary (repo: platform-backend, path: `backend/src/domain/models/CampaignSmsSummary.js`)
  - Fields: `campaign_id: ObjectId`, `total_sent: number`, `total_delivered: number`, `cost: number`

### Services

- **Service**: campaignAnalyticsService (repo: platform-backend, path: `backend/src/application/services/campaignAnalyticsService.js`)
  - Methods: `getSummary()`, `getTimeSeries()`, `getByChannel()`, `compareVariants()`
- **Service**: campaignSmsSummaryService (repo: platform-backend, path: `backend/src/application/services/campaignSmsSummaryService.js`)
  - Methods: `getSummary()`, `getCostBreakdown()`, `getDeliveryRate()`

### Routes/Endpoints

- `GET /api/campaigns/:id/analytics` -> `campaignAnalyticsService.getSummary()`
- `GET /api/campaigns/:id/analytics/timeseries` -> `campaignAnalyticsService.getTimeSeries()`
- `GET /api/campaigns/:id/sms-summary` -> `campaignSmsSummaryService.getSummary()`

### Frontend Components

- **Page**: CampaignDetailPage (repo: engage-ai-flow, path: `client/src/pages/CampaignDetailPage.tsx`)
  - Analytics tab com graficos de performance
- **Component**: CampaignAnalyticsChart (repo: engage-ai-flow, path: `client/src/components/campaigns/CampaignAnalyticsChart.tsx`)

## Acceptance Criteria

1. GIVEN uma campanha ativa com envios realizados
   WHEN o usuario acessa a aba de analytics na CampaignDetailPage
   THEN exibe metricas de sent, delivered, opened, clicked, converted com percentuais

2. GIVEN filtro temporal selecionado (7d, 30d, custom)
   WHEN o dashboard recarrega
   THEN as metricas sao recalculadas via ClickHouse para o periodo selecionado

3. GIVEN campanha com A/B test ativo
   WHEN acessa analytics
   THEN exibe comparativo side-by-side das variantes com indicacao visual do vencedor

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

2. **ClickHouseAnalytics** - nova
   - Spec: docs/specs/skills/clickhouse_analytics.md
   - Queries analiticas em ClickHouse para metricas de campanha

## Required Agent Capabilities

- **Primary**: `crm_data_agent` - capabilities: [analytics, clickhouse, data_pipeline]
- **Secondary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, charts]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'services/campaignAnalyticsService'`
- `category: crm_backend` + `source_file CONTAINS 'services/campaignSmsSummaryService'`
- `category: crm_frontend` + `source_file CONTAINS 'pages/CampaignDetailPage'`
- `category: usecase` + `domain: campaigns`

## Related Use Cases

- **Depends on**: UC-CAM-001 (Criar Campanha - necessario ter campanha), UC-CAM-002 (A/B Testing - dados comparativos)
- **Enables**: UC-JRN-004 (Journey Analytics - compartilha infraestrutura ClickHouse)
- **Conflicts with**: nenhum

## Implementation Notes

- ClickHouse e usado para queries analiticas (nao MongoDB)
- Metricas sao ingeridas via Kafka consumer que escreve em ClickHouse
- Frontend usa Recharts para graficos
- Dados de SMS summary sao separados por custo e provider
- Cache de 60s nas queries mais pesadas de timeseries
