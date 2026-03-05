"""
Cypher query templates para o Neural Link.
Todas as queries como constantes para reutilizacao e testabilidade.
"""

# ============================================================
# Schema Creation
# ============================================================

CREATE_CHUNK_CONSTRAINT = """
CREATE CONSTRAINT chunk_id IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE
"""

CREATE_CONCEPT_CONSTRAINT = """
CREATE CONSTRAINT concept_id IF NOT EXISTS
FOR (c:Concept) REQUIRE c.id IS UNIQUE
"""

CREATE_AGENT_CONSTRAINT = """
CREATE CONSTRAINT agent_id IF NOT EXISTS
FOR (a:Agent) REQUIRE a.id IS UNIQUE
"""

CREATE_SKILL_CONSTRAINT = """
CREATE CONSTRAINT skill_id IF NOT EXISTS
FOR (s:Skill) REQUIRE s.id IS UNIQUE
"""

CREATE_TASK_CONSTRAINT = """
CREATE CONSTRAINT task_id IF NOT EXISTS
FOR (t:Task) REQUIRE t.id IS UNIQUE
"""

CREATE_ERROR_CONSTRAINT = """
CREATE CONSTRAINT error_id IF NOT EXISTS
FOR (e:Error) REQUIRE e.id IS UNIQUE
"""

CREATE_SESSION_CONSTRAINT = """
CREATE CONSTRAINT session_id IF NOT EXISTS
FOR (s:Session) REQUIRE s.id IS UNIQUE
"""

# Indexes for performance
CREATE_CHUNK_SOURCE_INDEX = """
CREATE INDEX chunk_source IF NOT EXISTS
FOR (c:Chunk) ON (c.source_file)
"""

CREATE_CONCEPT_NAME_INDEX = """
CREATE INDEX concept_name IF NOT EXISTS
FOR (c:Concept) ON (c.name)
"""

CREATE_CONCEPT_DOMAIN_INDEX = """
CREATE INDEX concept_domain IF NOT EXISTS
FOR (c:Concept) ON (c.domain)
"""

CREATE_AGENT_TYPE_INDEX = """
CREATE INDEX agent_type IF NOT EXISTS
FOR (a:Agent) ON (a.type)
"""

CREATE_TASK_STATUS_INDEX = """
CREATE INDEX task_status IF NOT EXISTS
FOR (t:Task) ON (t.status)
"""

CREATE_ERROR_TYPE_INDEX = """
CREATE INDEX error_type IF NOT EXISTS
FOR (e:Error) ON (e.error_type)
"""

# Fulltext indexes
CREATE_CHUNK_FULLTEXT = """
CREATE FULLTEXT INDEX chunk_content IF NOT EXISTS
FOR (c:Chunk) ON EACH [c.content]
"""

CREATE_CONCEPT_FULLTEXT = """
CREATE FULLTEXT INDEX concept_search IF NOT EXISTS
FOR (c:Concept) ON EACH [c.name, c.description]
"""

# ============================================================
# Node CRUD
# ============================================================

UPSERT_CHUNK = """
MERGE (c:Chunk {id: $id})
SET c.content = $content,
    c.source_file = $source_file,
    c.chunk_index = $chunk_index,
    c.category = $category,
    c.agent_specialty = $agent_specialty,
    c.created_at = coalesce(c.created_at, $created_at),
    c.access_count = coalesce(c.access_count, 0)
RETURN c
"""

UPSERT_CONCEPT = """
MERGE (c:Concept {id: $id})
SET c.name = $name,
    c.domain = $domain,
    c.description = $description,
    c.confidence = $confidence,
    c.source = $source
RETURN c
"""

UPSERT_AGENT = """
MERGE (a:Agent {id: $id})
SET a.name = $name,
    a.type = $type,
    a.module_path = $module_path,
    a.capabilities = $capabilities,
    a.status = $status,
    a.success_rate = coalesce(a.success_rate, 1.0)
RETURN a
"""

UPSERT_SKILL = """
MERGE (s:Skill {id: $id})
SET s.name = $name,
    s.code = $code,
    s.source = $source,
    s.target_error = $target_error,
    s.success_count = coalesce(s.success_count, 0),
    s.failure_count = coalesce(s.failure_count, 0)
RETURN s
"""

UPSERT_TASK = """
MERGE (t:Task {id: $id})
SET t.description = $description,
    t.type = $type,
    t.status = $status,
    t.priority = $priority,
    t.input = $input,
    t.output = $output,
    t.created_at = coalesce(t.created_at, $created_at)
RETURN t
"""

UPSERT_ERROR = """
MERGE (e:Error {id: $id})
SET e.error_type = $error_type,
    e.message = $message,
    e.library = $library,
    e.frequency = coalesce(e.frequency, 0) + 1,
    e.resolved = $resolved
RETURN e
"""

UPSERT_SESSION = """
MERGE (s:Session {id: $id})
SET s.source = $source,
    s.started_at = coalesce(s.started_at, $started_at),
    s.task_count = $task_count,
    s.success_count = $success_count
RETURN s
"""

# ============================================================
# Relationships
# ============================================================

CREATE_CHUNK_MENTIONS_CONCEPT = """
MATCH (c:Chunk {id: $chunk_id})
MATCH (co:Concept {id: $concept_id})
MERGE (c)-[r:MENTIONS]->(co)
SET r.confidence = $confidence
RETURN r
"""

CREATE_CHUNK_NEXT = """
MATCH (c1:Chunk {id: $chunk_id_1})
MATCH (c2:Chunk {id: $chunk_id_2})
MERGE (c1)-[:NEXT_CHUNK]->(c2)
"""

CREATE_CHUNK_SAME_SOURCE = """
MATCH (c1:Chunk {id: $chunk_id_1})
MATCH (c2:Chunk {id: $chunk_id_2})
MERGE (c1)-[:SAME_SOURCE]->(c2)
"""

CREATE_CONCEPT_RELATED = """
MATCH (c1:Concept {id: $concept_id_1})
MATCH (c2:Concept {id: $concept_id_2})
MERGE (c1)-[r:RELATED_TO]->(c2)
SET r.weight = $weight, r.type = $relation_type
RETURN r
"""

CREATE_AGENT_SPECIALIZES = """
MATCH (a:Agent {id: $agent_id})
MATCH (c:Concept {id: $concept_id})
MERGE (a)-[:SPECIALIZES_IN]->(c)
"""

CREATE_AGENT_OWNS_SKILL = """
MATCH (a:Agent {id: $agent_id})
MATCH (s:Skill {id: $skill_id})
MERGE (a)-[:OWNS]->(s)
"""

CREATE_TASK_ASSIGNED = """
MATCH (t:Task {id: $task_id})
MATCH (a:Agent {id: $agent_id})
MERGE (t)-[:ASSIGNED_TO]->(a)
"""

CREATE_TASK_USED_CHUNK = """
MATCH (t:Task {id: $task_id})
MATCH (c:Chunk {id: $chunk_id})
MERGE (t)-[r:USED_CHUNK]->(c)
SET r.relevance = $relevance
"""

CREATE_ERROR_RESOLVED_BY = """
MATCH (e:Error {id: $error_id})
MATCH (s:Skill {id: $skill_id})
MERGE (e)-[:RESOLVED_BY]->(s)
"""

CREATE_ERROR_SIMILAR = """
MATCH (e1:Error {id: $error_id_1})
MATCH (e2:Error {id: $error_id_2})
MERGE (e1)-[:SIMILAR_TO]->(e2)
"""

# ============================================================
# Queries
# ============================================================

GET_CHUNKS_BY_SOURCE = """
MATCH (c:Chunk)
WHERE c.source_file = $source_file
RETURN c ORDER BY c.chunk_index
"""

GET_AGENT_BY_CAPABILITIES = """
MATCH (a:Agent)
WHERE any(cap IN $required_capabilities WHERE cap IN a.capabilities)
RETURN a ORDER BY a.success_rate DESC
LIMIT $limit
"""

GET_CONCEPTS_BY_NAME = """
MATCH (c:Concept)
WHERE toLower(c.name) CONTAINS toLower($name)
RETURN c
LIMIT $limit
"""

FULLTEXT_SEARCH_CHUNKS = """
CALL db.index.fulltext.queryNodes('chunk_content', $query)
YIELD node, score
RETURN node AS chunk, score
ORDER BY score DESC
LIMIT $limit
"""

FULLTEXT_SEARCH_CONCEPTS = """
CALL db.index.fulltext.queryNodes('concept_search', $query)
YIELD node, score
RETURN node AS concept, score
ORDER BY score DESC
LIMIT $limit
"""

GET_RELATED_CONCEPTS = """
MATCH (c:Concept {id: $concept_id})-[r:RELATED_TO]-(related:Concept)
RETURN related, r.weight AS weight, r.type AS relation_type
ORDER BY r.weight DESC
LIMIT $limit
"""

GET_CHUNKS_FOR_CONCEPT = """
MATCH (c:Chunk)-[r:MENTIONS]->(co:Concept {id: $concept_id})
RETURN c, r.confidence AS confidence
ORDER BY r.confidence DESC
LIMIT $limit
"""

GET_ERROR_RESOLUTION = """
MATCH (e:Error)-[:RESOLVED_BY]->(s:Skill)
WHERE toLower(e.error_type) CONTAINS toLower($error_type)
   OR toLower(e.message) CONTAINS toLower($error_message)
RETURN e, s
LIMIT $limit
"""

GET_SIMILAR_ERRORS = """
MATCH (e:Error {id: $error_id})-[:SIMILAR_TO]-(similar:Error)
OPTIONAL MATCH (similar)-[:RESOLVED_BY]->(s:Skill)
RETURN similar, s
LIMIT $limit
"""

GET_GRAPH_STATS = """
MATCH (n)
WITH labels(n) AS lbls, count(n) AS cnt
UNWIND lbls AS label
RETURN label, sum(cnt) AS count
ORDER BY count DESC
"""

GET_AGENT_PERFORMANCE = """
MATCH (a:Agent)
RETURN a.id AS id, a.name AS name, a.type AS type,
       a.success_rate AS success_rate, a.status AS status
ORDER BY a.success_rate DESC
"""

INCREMENT_CHUNK_ACCESS = """
MATCH (c:Chunk {id: $chunk_id})
SET c.access_count = coalesce(c.access_count, 0) + 1
RETURN c.access_count AS access_count
"""

UPDATE_AGENT_SUCCESS_RATE = """
MATCH (a:Agent {id: $agent_id})
SET a.success_rate = $success_rate
RETURN a
"""

DECAY_CONCEPT_CONFIDENCE = """
MATCH (c:Concept)
WHERE c.confidence > 0.1
  AND c.last_accessed < datetime() - duration({days: $days_threshold})
SET c.confidence = c.confidence * $decay_factor
RETURN count(c) AS decayed_count
"""

GET_RECENT_TASKS = """
MATCH (t:Task)
RETURN t
ORDER BY t.created_at DESC
LIMIT $limit
"""

# ============================================================
# Identity Manager Queries
# ============================================================

GET_PENDING_TASKS_BY_TYPE = """
MATCH (t:Task)
WHERE t.status = 'pending' AND t.type = $task_type
RETURN t
ORDER BY t.created_at ASC
"""

UPDATE_TASK_STATUS = """
MATCH (t:Task {id: $task_id})
SET t.status = $status,
    t.output = $output,
    t.updated_at = datetime()
RETURN t
"""

GET_TASK_QUEUE_BY_PROVIDER = """
MATCH (t:Task)
WHERE t.type = $provider
RETURN t
ORDER BY t.priority DESC, t.created_at ASC
"""

# ============================================================
# Task Evaluation Queries
# ============================================================

UPDATE_TASK_QUALITY_SCORE = """
MATCH (t:Task {id: $task_id})
SET t.quality_score = $quality_score,
    t.evaluation_feedback = $evaluation_feedback,
    t.refinement_count = $refinement_count,
    t.evaluated_at = datetime()
RETURN t
"""

GET_TASK_WITH_SPEC = """
MATCH (t:Task {id: $task_id})
RETURN t.id AS id, t.description AS description, t.type AS type,
       t.input AS input, t.output AS output, t.status AS status,
       t.quality_score AS quality_score, t.refinement_count AS refinement_count
"""

GET_TASK_EVALUATION_HISTORY = """
MATCH (t:Task {id: $task_id})
RETURN t.id AS id, t.quality_score AS quality_score,
       t.evaluation_feedback AS evaluation_feedback,
       t.refinement_count AS refinement_count, t.evaluated_at AS evaluated_at
"""

# ============================================================
# Telemetry / Obsidian Bridge Queries
# ============================================================

GET_TASKS_WITH_AGENTS = """
MATCH (t:Task)-[:ASSIGNED_TO]->(a:Agent)
RETURN t.id AS task_id, t.description AS description, t.type AS type,
       t.quality_score AS quality_score, t.evaluation_feedback AS feedback,
       t.status AS status, a.id AS agent_id, a.name AS agent_name,
       t.created_at AS created_at
ORDER BY t.created_at DESC
LIMIT $limit
"""

# ============================================================
# Phase 6: External Sync / Macro Synchronization
# ============================================================

CREATE_EXTERNAL_SYNC_CONSTRAINT = """
CREATE CONSTRAINT external_sync_id IF NOT EXISTS
FOR (es:ExternalSync) REQUIRE es.id IS UNIQUE
"""

CREATE_EXTERNAL_SYNC_SOURCE_INDEX = """
CREATE INDEX external_sync_source IF NOT EXISTS
FOR (es:ExternalSync) ON (es.source)
"""

UPSERT_EXTERNAL_SYNC = """
MERGE (es:ExternalSync {id: $id})
SET es.source = $source,
    es.event_type = $event_type,
    es.message = $message,
    es.data = $data,
    es.phase = $phase,
    es.created_at = coalesce(es.created_at, $created_at)
RETURN es
"""

GET_EXTERNAL_SYNCS = """
MATCH (es:ExternalSync)
WHERE es.source = $source
RETURN es.id AS id, es.source AS source, es.event_type AS event_type,
       es.message AS message, es.data AS data, es.phase AS phase,
       es.created_at AS created_at
ORDER BY es.created_at DESC
LIMIT $limit
"""

GET_EXTERNAL_SYNC_STATS = """
MATCH (es:ExternalSync)
RETURN es.source AS source, es.phase AS phase, count(es) AS count
ORDER BY count DESC
"""

LINK_SYNC_TO_TASK = """
MATCH (es:ExternalSync {id: $sync_id})
MATCH (t:Task {id: $task_id})
MERGE (es)-[:TRIGGERED]->(t)
"""

# ============================================================
# Performance Anomaly Detection (Mission 002 trigger)
# ============================================================

GET_PERFORMANCE_ANOMALIES = """
MATCH (t:Task)-[:ASSIGNED_TO]->(a:Agent)
WHERE t.quality_score < $quality_threshold
  AND t.evaluated_at > datetime() - duration({minutes: $minutes_window})
RETURN a.id AS agent_id, a.name AS agent_name, a.success_rate AS success_rate,
       t.id AS task_id, t.quality_score AS quality_score,
       t.evaluation_feedback AS feedback, t.evaluated_at AS evaluated_at
ORDER BY t.quality_score ASC
"""

# ============================================================
# GraphSynergy: n8n Service / Node Graph
# ============================================================

CREATE_SERVICE_CONSTRAINT = """
CREATE CONSTRAINT service_id IF NOT EXISTS
FOR (s:Service) REQUIRE s.id IS UNIQUE
"""

CREATE_N8N_NODE_CONSTRAINT = """
CREATE CONSTRAINT n8n_node_id IF NOT EXISTS
FOR (n:N8nNode) REQUIRE n.id IS UNIQUE
"""

CREATE_SERVICE_NAME_INDEX = """
CREATE INDEX service_name IF NOT EXISTS
FOR (s:Service) ON (s.name)
"""

CREATE_N8N_NODE_TYPE_INDEX = """
CREATE INDEX n8n_node_type IF NOT EXISTS
FOR (n:N8nNode) ON (n.node_type)
"""

CREATE_N8N_NODE_WORKFLOW_INDEX = """
CREATE INDEX n8n_node_workflow IF NOT EXISTS
FOR (n:N8nNode) ON (n.workflow)
"""

UPSERT_SERVICE = """
MERGE (s:Service {id: $id})
SET s.name = $name,
    s.updated_at = datetime()
RETURN s
"""

UPSERT_N8N_NODE = """
MERGE (n:N8nNode {id: $id})
SET n.name = $name,
    n.node_type = $node_type,
    n.service = $service,
    n.type_version = $type_version,
    n.workflow = $workflow,
    n.updated_at = datetime()
RETURN n
"""

CREATE_SERVICE_USES_NODE = """
MATCH (s:Service {id: $service_id})
MATCH (n:N8nNode {id: $node_id})
MERGE (s)-[:USES]->(n)
"""

CREATE_NODE_CONNECTS_TO = """
MATCH (n1:N8nNode {id: $source_id})
MATCH (n2:N8nNode {id: $target_id})
MERGE (n1)-[:CONNECTS_TO]->(n2)
"""

FIND_PATH_BETWEEN_SERVICES = """
MATCH (s1:Service {name: $service_a})-[:USES]->(start:N8nNode),
      (s2:Service {name: $service_b})-[:USES]->(end:N8nNode)
MATCH path = (start)-[:CONNECTS_TO*1..6]->(end)
RETURN [n IN nodes(path) | n.name] AS chain,
       [n IN nodes(path) | n.service] AS services,
       length(path) AS hops,
       start.workflow AS workflow
ORDER BY hops ASC
LIMIT $limit
"""

GET_SERVICE_NEIGHBORS = """
MATCH (s:Service {name: $service_name})-[:USES]->(n:N8nNode)-[:CONNECTS_TO]->(neighbor:N8nNode)
RETURN DISTINCT neighbor.service AS connected_service, neighbor.name AS node_name,
       neighbor.workflow AS workflow
ORDER BY connected_service
"""

GET_ALL_SERVICES = """
MATCH (s:Service)-[:USES]->(n:N8nNode)
RETURN s.name AS service, count(n) AS node_count
ORDER BY node_count DESC
"""

# ============================================================
# CRM: Self-Sovereign CRM (Lead / Flow / Interaction)
# ============================================================

# -- Schema ----------------------------------------------------------

CREATE_LEAD_CONSTRAINT = """
CREATE CONSTRAINT lead_id IF NOT EXISTS
FOR (l:Lead) REQUIRE l.id IS UNIQUE
"""

CREATE_FLOW_CONSTRAINT = """
CREATE CONSTRAINT flow_id IF NOT EXISTS
FOR (f:Flow) REQUIRE f.id IS UNIQUE
"""

CREATE_INTERACTION_CONSTRAINT = """
CREATE CONSTRAINT interaction_id IF NOT EXISTS
FOR (i:Interaction) REQUIRE i.id IS UNIQUE
"""

CREATE_LEAD_NAME_INDEX = """
CREATE INDEX lead_name IF NOT EXISTS
FOR (l:Lead) ON (l.name)
"""

CREATE_LEAD_EMAIL_INDEX = """
CREATE INDEX lead_email IF NOT EXISTS
FOR (l:Lead) ON (l.email)
"""

CREATE_LEAD_SOURCE_INDEX = """
CREATE INDEX lead_source IF NOT EXISTS
FOR (l:Lead) ON (l.source_channel)
"""

CREATE_FLOW_STATUS_INDEX = """
CREATE INDEX flow_status IF NOT EXISTS
FOR (f:Flow) ON (f.status)
"""

CREATE_INTERACTION_TIMESTAMP_INDEX = """
CREATE INDEX interaction_timestamp IF NOT EXISTS
FOR (i:Interaction) ON (i.timestamp)
"""

CREATE_LEAD_FULLTEXT = """
CREATE FULLTEXT INDEX lead_search IF NOT EXISTS
FOR (l:Lead) ON EACH [l.name, l.email, l.company]
"""

# -- CRUD ------------------------------------------------------------

UPSERT_LEAD = """
MERGE (l:Lead {id: $id})
SET l.name = $name,
    l.email = $email,
    l.company = $company,
    l.trust = coalesce($trust, l.trust, 0.5),
    l.interaction_count = coalesce(l.interaction_count, 0),
    l.source_channel = $source_channel,
    l.tags = $tags,
    l.created_at = coalesce(l.created_at, $created_at),
    l.updated_at = $updated_at
RETURN l
"""

UPSERT_FLOW = """
MERGE (f:Flow {id: $id})
SET f.name = $name,
    f.objective = $objective,
    f.n8n_workflow_id = $n8n_workflow_id,
    f.status = coalesce(f.status, $status),
    f.created_at = coalesce(f.created_at, $created_at)
RETURN f
"""

UPSERT_INTERACTION = """
MERGE (i:Interaction {id: $id})
SET i.lead_id = $lead_id,
    i.agent_id = $agent_id,
    i.channel = $channel,
    i.action = $action,
    i.detail = $detail,
    i.timestamp = coalesce(i.timestamp, $timestamp)
RETURN i
"""

UPDATE_LEAD_TRUST = """
MATCH (l:Lead {id: $lead_id})
SET l.trust = $trust,
    l.updated_at = $updated_at
RETURN l
"""

UPDATE_LEAD = """
MATCH (l:Lead {id: $id})
SET l.name = coalesce($name, l.name),
    l.email = coalesce($email, l.email),
    l.company = coalesce($company, l.company),
    l.tags = coalesce($tags, l.tags),
    l.trust = coalesce($trust, l.trust),
    l.updated_at = datetime()
RETURN l
"""

SOFT_DELETE_LEAD = """
MATCH (l:Lead {id: $id})
SET l.deleted_at = datetime(),
    l.active = false
RETURN l
"""

INCREMENT_LEAD_INTERACTION_COUNT = """
MATCH (l:Lead {id: $lead_id})
SET l.interaction_count = coalesce(l.interaction_count, 0) + 1,
    l.updated_at = $updated_at
RETURN l.interaction_count AS interaction_count
"""

UPDATE_FLOW_STATUS = """
MATCH (f:Flow {id: $flow_id})
SET f.status = $status
RETURN f
"""

UPDATE_FLOW = """
MATCH (f:Flow {id: $id})
SET f.name = coalesce($name, f.name),
    f.objective = coalesce($objective, f.objective),
    f.status = coalesce($status, f.status),
    f.updated_at = datetime()
RETURN f
"""

SOFT_DELETE_FLOW = """
MATCH (f:Flow {id: $id})
SET f.deleted_at = datetime(),
    f.active = false
RETURN f
"""

CALCULATE_LEAD_SCORE = """
MATCH (l:Lead {id: $id})
OPTIONAL MATCH (l)<-[:FOR_LEAD]-(i:Interaction)
OPTIONAL MATCH (l)-[:PART_OF_FLOW]->(f:Flow)
WITH l,
     count(DISTINCT i) AS interaction_count,
     max(i.timestamp) AS last_interaction,
     count(DISTINCT f) AS flow_count
RETURN l.id AS id,
       interaction_count,
       last_interaction,
       flow_count
"""

# -- Relationships ---------------------------------------------------

CREATE_LEAD_INTERACTED_WITH = """
MATCH (l1:Lead {id: $lead_id_1})
MATCH (l2:Lead {id: $lead_id_2})
MERGE (l1)-[r:INTERACTED_WITH]->(l2)
SET r.updated_at = $updated_at
"""

CREATE_LEAD_PART_OF_FLOW = """
MATCH (l:Lead {id: $lead_id})
MATCH (f:Flow {id: $flow_id})
MERGE (l)-[r:PART_OF_FLOW]->(f)
SET r.added_at = coalesce(r.added_at, $added_at)
"""

CREATE_FLOW_MENTIONED_IN = """
MATCH (f:Flow {id: $flow_id})
MATCH (c:Chunk {id: $chunk_id})
MERGE (f)-[:MENTIONED_IN]->(c)
"""

CREATE_INTERACTION_FOR_LEAD = """
MATCH (i:Interaction {id: $interaction_id})
MATCH (l:Lead {id: $lead_id})
MERGE (i)-[:FOR_LEAD]->(l)
"""

CREATE_INTERACTION_BY_AGENT = """
MATCH (i:Interaction {id: $interaction_id})
MATCH (a:Agent {id: $agent_id})
MERGE (i)-[:BY_AGENT]->(a)
"""

CREATE_FLOW_USES_WORKFLOW = """
MATCH (f:Flow {id: $flow_id})
MATCH (n:N8nNode {id: $node_id})
MERGE (f)-[:USES_WORKFLOW]->(n)
"""

# -- Read queries ----------------------------------------------------

GET_ALL_LEADS = """
MATCH (l:Lead)
WHERE l.active IS NULL OR l.active = true
RETURN l.id AS id, l.name AS name, l.email AS email, l.company AS company,
       l.trust AS trust, l.interaction_count AS interaction_count,
       l.source_channel AS source_channel, l.tags AS tags,
       l.created_at AS created_at, l.updated_at AS updated_at
ORDER BY l.created_at DESC
LIMIT $limit
"""

GET_LEAD_BY_ID = """
MATCH (l:Lead {id: $lead_id})
RETURN l.id AS id, l.name AS name, l.email AS email, l.company AS company,
       l.trust AS trust, l.interaction_count AS interaction_count,
       l.source_channel AS source_channel, l.tags AS tags,
       l.created_at AS created_at, l.updated_at AS updated_at
"""

GET_LEAD_NETWORK = """
MATCH (l:Lead {id: $lead_id})-[*1..3]-(connected)
RETURN DISTINCT connected
LIMIT $limit
"""

GET_LEAD_GRAPH = """
MATCH (l:Lead)
OPTIONAL MATCH (l)-[r1:PART_OF_FLOW]->(f:Flow)
OPTIONAL MATCH (l)-[r2:INTERACTED_WITH]-(l2:Lead)
OPTIONAL MATCH (i:Interaction)-[r3:FOR_LEAD]->(l)
OPTIONAL MATCH (i)-[r4:BY_AGENT]->(a:Agent)
RETURN l, f, l2, i, a, r1, r2, r3, r4
LIMIT $limit
"""

GET_ALL_FLOWS = """
MATCH (f:Flow)
WHERE f.active IS NULL OR f.active = true
OPTIONAL MATCH (l:Lead)-[:PART_OF_FLOW]->(f)
RETURN f.id AS id, f.name AS name, f.objective AS objective,
       f.n8n_workflow_id AS n8n_workflow_id, f.status AS status,
       count(l) AS lead_count, f.created_at AS created_at
ORDER BY f.created_at DESC
LIMIT $limit
"""

GET_FLOW_BY_ID = """
MATCH (f:Flow {id: $flow_id})
OPTIONAL MATCH (l:Lead)-[:PART_OF_FLOW]->(f)
RETURN f.id AS id, f.name AS name, f.objective AS objective,
       f.n8n_workflow_id AS n8n_workflow_id, f.status AS status,
       collect(l.id) AS lead_ids, f.created_at AS created_at
"""

GET_FLOW_GRAPH = """
MATCH (f:Flow {id: $flow_id})
OPTIONAL MATCH (l:Lead)-[r:PART_OF_FLOW]->(f)
RETURN f, l, r
"""

GET_LEAD_INTERACTIONS = """
MATCH (i:Interaction)-[:FOR_LEAD]->(l:Lead {id: $lead_id})
OPTIONAL MATCH (i)-[:BY_AGENT]->(a:Agent)
RETURN i.id AS id, i.lead_id AS lead_id, i.agent_id AS agent_id,
       i.channel AS channel, i.action AS action, i.detail AS detail,
       i.timestamp AS timestamp, a.name AS agent_name
ORDER BY i.timestamp DESC
LIMIT $limit
"""

FULLTEXT_SEARCH_LEADS = """
CALL db.index.fulltext.queryNodes('lead_search', $query)
YIELD node, score
RETURN node.id AS id, node.name AS name, node.email AS email,
       node.company AS company, node.trust AS trust,
       node.interaction_count AS interaction_count,
       node.source_channel AS source_channel, node.tags AS tags,
       node.created_at AS created_at, node.updated_at AS updated_at,
       score
ORDER BY score DESC
LIMIT $limit
"""

GET_CRM_STATS = """
OPTIONAL MATCH (l:Lead)
WITH count(l) AS total_leads, avg(l.trust) AS avg_trust
OPTIONAL MATCH (f:Flow)
WITH total_leads, avg_trust, count(f) AS total_flows
OPTIONAL MATCH (i:Interaction)
RETURN total_leads, total_flows, count(i) AS total_interactions,
       coalesce(avg_trust, 0.0) AS avg_trust
"""

# ============================================================
# CRM Use Cases: Module / UseCase Graph
# ============================================================

# -- Schema ----------------------------------------------------------

CREATE_MODULE_CONSTRAINT = """
CREATE CONSTRAINT module_id IF NOT EXISTS
FOR (m:Module) REQUIRE m.id IS UNIQUE
"""

CREATE_USECASE_CONSTRAINT = """
CREATE CONSTRAINT usecase_id IF NOT EXISTS
FOR (uc:UseCase) REQUIRE uc.id IS UNIQUE
"""

CREATE_MODULE_REPO_INDEX = """
CREATE INDEX module_repo IF NOT EXISTS
FOR (m:Module) ON (m.repo)
"""

CREATE_MODULE_DOMAIN_INDEX = """
CREATE INDEX module_domain IF NOT EXISTS
FOR (m:Module) ON (m.domain)
"""

CREATE_USECASE_DOMAIN_INDEX = """
CREATE INDEX usecase_domain IF NOT EXISTS
FOR (uc:UseCase) ON (uc.domain)
"""

CREATE_USECASE_STATUS_INDEX = """
CREATE INDEX usecase_status IF NOT EXISTS
FOR (uc:UseCase) ON (uc.status)
"""

CREATE_USECASE_FULLTEXT = """
CREATE FULLTEXT INDEX usecase_search IF NOT EXISTS
FOR (uc:UseCase) ON EACH [uc.name, uc.acceptance_criteria]
"""

# -- CRUD ------------------------------------------------------------

UPSERT_MODULE = """
MERGE (m:Module {id: $id})
SET m.name = $name,
    m.type = $type,
    m.repo = $repo,
    m.file_path = $file_path,
    m.language = $language,
    m.domain = $domain,
    m.description = $description,
    m.updated_at = datetime()
RETURN m
"""

UPSERT_USE_CASE = """
MERGE (uc:UseCase {id: $id})
SET uc.name = $name,
    uc.domain = $domain,
    uc.status = $status,
    uc.acceptance_criteria = $acceptance_criteria,
    uc.priority = $priority,
    uc.complexity = $complexity,
    uc.repos = $repos,
    uc.created_at = coalesce(uc.created_at, $created_at),
    uc.updated_at = datetime()
RETURN uc
"""

# -- Relationships ---------------------------------------------------

CREATE_USECASE_REQUIRES_SKILL = """
MATCH (uc:UseCase {id: $usecase_id})
MATCH (s:Skill {id: $skill_id})
MERGE (uc)-[r:REQUIRES_SKILL]->(s)
SET r.criticality = $criticality
"""

CREATE_USECASE_ASSIGNED_AGENT = """
MATCH (uc:UseCase {id: $usecase_id})
MATCH (a:Agent {id: $agent_id})
MERGE (uc)-[r:ASSIGNED_TO]->(a)
SET r.role = $role
"""

CREATE_USECASE_REFERENCES_MODULE = """
MATCH (uc:UseCase {id: $usecase_id})
MATCH (m:Module {id: $module_id})
MERGE (uc)-[:REFERENCES]->(m)
"""

CREATE_USECASE_DEPENDS_ON = """
MATCH (uc1:UseCase {id: $usecase_id})
MATCH (uc2:UseCase {id: $depends_on_id})
MERGE (uc1)-[:DEPENDS_ON]->(uc2)
"""

CREATE_MODULE_CALLS = """
MATCH (m1:Module {id: $source_id})
MATCH (m2:Module {id: $target_id})
MERGE (m1)-[r:CALLS]->(m2)
SET r.call_type = $call_type
"""

CREATE_MODULE_RENDERS = """
MATCH (m1:Module {id: $component_id})
MATCH (m2:Module {id: $rendered_by_id})
MERGE (m1)-[:RENDERS]->(m2)
"""

# -- Read queries ----------------------------------------------------

GET_ALL_MODULES = """
MATCH (m:Module)
RETURN m.id AS id, m.name AS name, m.type AS type, m.repo AS repo,
       m.file_path AS file_path, m.language AS language,
       m.domain AS domain, m.description AS description
ORDER BY m.repo, m.domain, m.name
LIMIT $limit
"""

GET_MODULES_BY_REPO = """
MATCH (m:Module)
WHERE m.repo = $repo
RETURN m.id AS id, m.name AS name, m.type AS type,
       m.file_path AS file_path, m.domain AS domain, m.description AS description
ORDER BY m.domain, m.name
"""

GET_MODULES_BY_DOMAIN = """
MATCH (m:Module)
WHERE m.domain = $domain
RETURN m.id AS id, m.name AS name, m.type AS type, m.repo AS repo,
       m.file_path AS file_path, m.description AS description
ORDER BY m.repo, m.name
"""

GET_ALL_USECASES = """
MATCH (uc:UseCase)
OPTIONAL MATCH (uc)-[:ASSIGNED_TO]->(a:Agent)
OPTIONAL MATCH (uc)-[:REQUIRES_SKILL]->(s:Skill)
RETURN uc.id AS id, uc.name AS name, uc.domain AS domain,
       uc.status AS status, uc.priority AS priority, uc.complexity AS complexity,
       uc.repos AS repos, uc.created_at AS created_at,
       collect(DISTINCT a.id) AS agents, collect(DISTINCT s.id) AS skills
ORDER BY uc.priority DESC, uc.domain
LIMIT $limit
"""

GET_USECASE_BY_ID = """
MATCH (uc:UseCase {id: $usecase_id})
OPTIONAL MATCH (uc)-[:ASSIGNED_TO]->(a:Agent)
OPTIONAL MATCH (uc)-[rs:REQUIRES_SKILL]->(s:Skill)
OPTIONAL MATCH (uc)-[:REFERENCES]->(m:Module)
OPTIONAL MATCH (uc)-[:DEPENDS_ON]->(dep:UseCase)
RETURN uc, collect(DISTINCT {id: a.id, name: a.name}) AS agents,
       collect(DISTINCT {id: s.id, name: s.name, criticality: rs.criticality}) AS skills,
       collect(DISTINCT {id: m.id, name: m.name, repo: m.repo}) AS modules,
       collect(DISTINCT {id: dep.id, name: dep.name}) AS dependencies
"""

GET_USECASES_BY_DOMAIN = """
MATCH (uc:UseCase)
WHERE uc.domain = $domain
RETURN uc.id AS id, uc.name AS name, uc.status AS status,
       uc.priority AS priority, uc.complexity AS complexity
ORDER BY uc.priority DESC
"""

GET_USECASES_BY_STATUS = """
MATCH (uc:UseCase)
WHERE uc.status = $status
RETURN uc.id AS id, uc.name AS name, uc.domain AS domain,
       uc.priority AS priority, uc.complexity AS complexity
ORDER BY uc.priority DESC, uc.domain
"""

GET_USECASE_COVERAGE = """
MATCH (a:Agent)
OPTIONAL MATCH (uc:UseCase)-[:ASSIGNED_TO]->(a)
RETURN a.id AS agent_id, a.name AS agent_name, a.type AS agent_type,
       collect(uc.id) AS usecase_ids, count(uc) AS usecase_count
ORDER BY usecase_count DESC
"""

GET_USECASE_SKILL_GAPS = """
MATCH (uc:UseCase)-[r:REQUIRES_SKILL]->(s:Skill)
WHERE NOT exists((s)<-[:OWNS]-(:Agent))
RETURN uc.id AS usecase_id, uc.name AS usecase_name,
       s.id AS skill_id, s.name AS skill_name, r.criticality AS criticality
ORDER BY r.criticality DESC
"""

FULLTEXT_SEARCH_USECASES = """
CALL db.index.fulltext.queryNodes('usecase_search', $query)
YIELD node, score
RETURN node.id AS id, node.name AS name, node.domain AS domain,
       node.status AS status, node.priority AS priority, score
ORDER BY score DESC
LIMIT $limit
"""

GET_USECASE_ROADMAP = """
MATCH (uc:UseCase)
OPTIONAL MATCH (uc)-[:DEPENDS_ON]->(dep:UseCase)
OPTIONAL MATCH (uc)-[:ASSIGNED_TO]->(a:Agent)
RETURN uc.id AS id, uc.name AS name, uc.domain AS domain,
       uc.status AS status, uc.priority AS priority, uc.complexity AS complexity,
       uc.repos AS repos,
       collect(DISTINCT dep.id) AS depends_on,
       collect(DISTINCT a.id) AS agents
ORDER BY uc.priority DESC, uc.domain
"""

# ============================================================
# KPI Metrics Intelligence: ModelMetric / ToolReview /
#     RequestMetric / DailyAggregate
# ============================================================

# -- Schema ----------------------------------------------------------

CREATE_MODEL_METRIC_CONSTRAINT = """
CREATE CONSTRAINT model_metric_id IF NOT EXISTS
FOR (mm:ModelMetric) REQUIRE mm.id IS UNIQUE
"""

CREATE_TOOL_REVIEW_CONSTRAINT = """
CREATE CONSTRAINT tool_review_id IF NOT EXISTS
FOR (tr:ToolReview) REQUIRE tr.id IS UNIQUE
"""

CREATE_REQUEST_METRIC_CONSTRAINT = """
CREATE CONSTRAINT request_metric_id IF NOT EXISTS
FOR (rm:RequestMetric) REQUIRE rm.id IS UNIQUE
"""

CREATE_DAILY_AGGREGATE_CONSTRAINT = """
CREATE CONSTRAINT daily_aggregate_id IF NOT EXISTS
FOR (da:DailyAggregate) REQUIRE da.id IS UNIQUE
"""

CREATE_MODEL_METRIC_DATE_INDEX = """
CREATE INDEX model_metric_date IF NOT EXISTS
FOR (mm:ModelMetric) ON (mm.date)
"""

CREATE_TOOL_REVIEW_TOOL_INDEX = """
CREATE INDEX tool_review_tool IF NOT EXISTS
FOR (tr:ToolReview) ON (tr.tool_name)
"""

CREATE_REQUEST_METRIC_SESSION_INDEX = """
CREATE INDEX request_metric_session IF NOT EXISTS
FOR (rm:RequestMetric) ON (rm.session_id)
"""

CREATE_DAILY_AGGREGATE_DATE_INDEX = """
CREATE INDEX daily_aggregate_date IF NOT EXISTS
FOR (da:DailyAggregate) ON (da.date)
"""

# -- CRUD: ModelMetric -----------------------------------------------

UPSERT_MODEL_METRIC = """
MERGE (mm:ModelMetric {id: $id})
SET mm.model_id = $model_id,
    mm.date = $date,
    mm.total_requests = coalesce(mm.total_requests, 0) + $requests_delta,
    mm.total_tokens_in = coalesce(mm.total_tokens_in, 0) + $tokens_in_delta,
    mm.total_tokens_out = coalesce(mm.total_tokens_out, 0) + $tokens_out_delta,
    mm.total_cost_usd = coalesce(mm.total_cost_usd, 0.0) + $cost_delta,
    mm.failure_count = coalesce(mm.failure_count, 0) + $failure_delta,
    mm.avg_quality_score = $avg_quality_score,
    mm.avg_latency_ms = $avg_latency_ms,
    mm.p50_latency_ms = $p50_latency_ms,
    mm.p95_latency_ms = $p95_latency_ms,
    mm.updated_at = datetime()
RETURN mm
"""

GET_MODEL_METRICS_LEADERBOARD = """
MATCH (mm:ModelMetric)
WITH mm.model_id AS model_id,
     sum(mm.total_requests) AS total_requests,
     sum(mm.total_tokens_in) + sum(mm.total_tokens_out) AS total_tokens,
     sum(mm.total_cost_usd) AS total_cost,
     avg(mm.avg_quality_score) AS avg_quality,
     avg(mm.avg_latency_ms) AS avg_latency,
     sum(mm.failure_count) AS failures
RETURN model_id, total_requests, total_tokens, total_cost, avg_quality,
       avg_latency, failures,
       CASE WHEN avg_quality > 0 THEN total_cost / avg_quality ELSE 999.0 END AS cost_per_quality
ORDER BY cost_per_quality ASC
"""

GET_MODEL_METRIC_HISTORY = """
MATCH (mm:ModelMetric {model_id: $model_id})
RETURN mm.date AS date, mm.total_requests AS total_requests,
       mm.total_tokens_in AS tokens_in, mm.total_tokens_out AS tokens_out,
       mm.total_cost_usd AS cost_usd, mm.avg_quality_score AS avg_quality,
       mm.avg_latency_ms AS avg_latency, mm.failure_count AS failures
ORDER BY mm.date DESC
LIMIT $limit
"""

# -- CRUD: ToolReview ------------------------------------------------

UPSERT_TOOL_REVIEW = """
MERGE (tr:ToolReview {id: $id})
SET tr.tool_name = $tool_name,
    tr.sprint_date = $sprint_date,
    tr.score_correto = $score_correto,
    tr.score_completo = $score_completo,
    tr.score_qualidade = $score_qualidade,
    tr.nota_geral = $nota_geral,
    tr.deliverables_done = $deliverables_done,
    tr.deliverables_total = $deliverables_total,
    tr.issues_critical = $issues_critical,
    tr.issues_medium = $issues_medium,
    tr.issues_low = $issues_low,
    tr.reviewer = $reviewer,
    tr.notes = $notes,
    tr.created_at = coalesce(tr.created_at, datetime())
RETURN tr
"""

GET_TOOL_REVIEWS = """
MATCH (tr:ToolReview)
RETURN tr.id AS id, tr.tool_name AS tool_name, tr.sprint_date AS sprint_date,
       tr.score_correto AS score_correto, tr.score_completo AS score_completo,
       tr.score_qualidade AS score_qualidade, tr.nota_geral AS nota_geral,
       tr.deliverables_done AS deliverables_done, tr.deliverables_total AS deliverables_total,
       tr.issues_critical AS issues_critical, tr.issues_medium AS issues_medium,
       tr.issues_low AS issues_low, tr.reviewer AS reviewer, tr.notes AS notes
ORDER BY tr.sprint_date DESC
LIMIT $limit
"""

GET_TOOL_REVIEW_HISTORY = """
MATCH (tr:ToolReview {tool_name: $tool_name})
RETURN tr.id AS id, tr.sprint_date AS sprint_date,
       tr.score_correto AS score_correto, tr.score_completo AS score_completo,
       tr.score_qualidade AS score_qualidade, tr.nota_geral AS nota_geral,
       tr.deliverables_done AS deliverables_done, tr.deliverables_total AS deliverables_total,
       tr.issues_critical AS issues_critical, tr.issues_medium AS issues_medium,
       tr.issues_low AS issues_low, tr.reviewer AS reviewer, tr.notes AS notes
ORDER BY tr.sprint_date DESC
LIMIT $limit
"""

GET_TOOL_COMPARISON = """
MATCH (tr:ToolReview)
WITH tr.tool_name AS tool_name,
     count(tr) AS review_count,
     avg(tr.nota_geral) AS avg_score,
     avg(tr.score_correto) AS avg_correto,
     avg(tr.score_completo) AS avg_completo,
     avg(tr.score_qualidade) AS avg_qualidade,
     sum(tr.deliverables_done) AS total_done,
     sum(tr.deliverables_total) AS total_planned,
     sum(tr.issues_critical) AS total_critical
RETURN tool_name, review_count, avg_score, avg_correto, avg_completo,
       avg_qualidade, total_done, total_planned, total_critical
ORDER BY avg_score DESC
"""

# -- CRUD: RequestMetric ---------------------------------------------

UPSERT_REQUEST_METRIC = """
CREATE (rm:RequestMetric {id: $id})
SET rm.session_id = $session_id,
    rm.model_used = $model_used,
    rm.task_type = $task_type,
    rm.agent_used = $agent_used,
    rm.input_tokens = $input_tokens,
    rm.output_tokens = $output_tokens,
    rm.cost_usd = $cost_usd,
    rm.latency_ms = $latency_ms,
    rm.quality_score = $quality_score,
    rm.layer_reached = $layer_reached,
    rm.cache_hit = $cache_hit,
    rm.evaluation_skipped = $evaluation_skipped,
    rm.created_at = $created_at
RETURN rm
"""

GET_REQUEST_METRICS_BY_DATE = """
MATCH (rm:RequestMetric)
WHERE rm.created_at >= $start_date AND rm.created_at <= $end_date
RETURN rm.id AS id, rm.session_id AS session_id, rm.model_used AS model_used,
       rm.task_type AS task_type, rm.agent_used AS agent_used,
       rm.input_tokens AS input_tokens, rm.output_tokens AS output_tokens,
       rm.cost_usd AS cost_usd, rm.latency_ms AS latency_ms,
       rm.quality_score AS quality_score, rm.layer_reached AS layer_reached,
       rm.cache_hit AS cache_hit, rm.created_at AS created_at
ORDER BY rm.created_at DESC
LIMIT $limit
"""

# -- CRUD: DailyAggregate -------------------------------------------

UPSERT_DAILY_AGGREGATE = """
MERGE (da:DailyAggregate {id: $id})
SET da.date = $date,
    da.dimension_type = $dimension_type,
    da.dimension_value = $dimension_value,
    da.total_requests = $total_requests,
    da.total_cost_usd = $total_cost_usd,
    da.avg_quality = $avg_quality,
    da.avg_latency_ms = $avg_latency_ms,
    da.cache_hit_rate = $cache_hit_rate,
    da.failure_rate = $failure_rate,
    da.updated_at = datetime()
RETURN da
"""

GET_DAILY_AGGREGATES = """
MATCH (da:DailyAggregate)
WHERE da.dimension_type = $dimension_type
RETURN da.date AS date, da.dimension_type AS dimension_type,
       da.dimension_value AS dimension_value,
       da.total_requests AS total_requests, da.total_cost_usd AS total_cost_usd,
       da.avg_quality AS avg_quality, da.avg_latency_ms AS avg_latency_ms,
       da.cache_hit_rate AS cache_hit_rate, da.failure_rate AS failure_rate
ORDER BY da.date DESC
LIMIT $limit
"""

GET_DAILY_AGGREGATES_BY_VALUE = """
MATCH (da:DailyAggregate)
WHERE da.dimension_type = $dimension_type AND da.dimension_value = $dimension_value
RETURN da.date AS date, da.total_requests AS total_requests,
       da.total_cost_usd AS total_cost_usd, da.avg_quality AS avg_quality,
       da.avg_latency_ms AS avg_latency_ms, da.cache_hit_rate AS cache_hit_rate,
       da.failure_rate AS failure_rate
ORDER BY da.date DESC
LIMIT $limit
"""

# -- KPI Queries: Agent Heatmap / Anomalies -------------------------

GET_AGENT_TASK_TYPE_HEATMAP = """
MATCH (rm:RequestMetric)
WHERE rm.agent_used IS NOT NULL AND rm.quality_score IS NOT NULL
WITH rm.agent_used AS agent, rm.task_type AS task_type,
     avg(rm.quality_score) AS avg_quality, count(rm) AS request_count
RETURN agent, task_type, avg_quality, request_count
ORDER BY agent, task_type
"""

GET_COST_PER_QUALITY_BY_MODEL = """
MATCH (rm:RequestMetric)
WHERE rm.quality_score IS NOT NULL AND rm.quality_score > 0
WITH rm.model_used AS model,
     sum(rm.cost_usd) AS total_cost,
     avg(rm.quality_score) AS avg_quality,
     count(rm) AS total_requests
RETURN model, total_cost, avg_quality, total_requests,
       total_cost / avg_quality AS cost_per_quality_point
ORDER BY cost_per_quality_point ASC
"""

GET_COST_PER_QUALITY_BY_AGENT = """
MATCH (rm:RequestMetric)
WHERE rm.quality_score IS NOT NULL AND rm.quality_score > 0
  AND rm.agent_used IS NOT NULL
WITH rm.agent_used AS agent,
     sum(rm.cost_usd) AS total_cost,
     avg(rm.quality_score) AS avg_quality,
     count(rm) AS total_requests
RETURN agent, total_cost, avg_quality, total_requests,
       total_cost / avg_quality AS cost_per_quality_point
ORDER BY cost_per_quality_point ASC
"""

GET_COST_PER_QUALITY_BY_TASK_TYPE = """
MATCH (rm:RequestMetric)
WHERE rm.quality_score IS NOT NULL AND rm.quality_score > 0
WITH rm.task_type AS task_type,
     sum(rm.cost_usd) AS total_cost,
     avg(rm.quality_score) AS avg_quality,
     count(rm) AS total_requests
RETURN task_type, total_cost, avg_quality, total_requests,
       total_cost / avg_quality AS cost_per_quality_point
ORDER BY cost_per_quality_point ASC
"""

# ============================================================
# Audit: AuditResult Nodes (UC-AUDIT-001)
# ============================================================

# -- Schema ----------------------------------------------------------

CREATE_AUDIT_RESULT_CONSTRAINT = """
CREATE CONSTRAINT audit_result_id IF NOT EXISTS
FOR (ar:AuditResult) REQUIRE ar.id IS UNIQUE
"""

CREATE_AUDIT_RESULT_TARGET_INDEX = """
CREATE INDEX audit_result_target IF NOT EXISTS
FOR (ar:AuditResult) ON (ar.target)
"""

CREATE_AUDIT_RESULT_TYPE_INDEX = """
CREATE INDEX audit_result_type IF NOT EXISTS
FOR (ar:AuditResult) ON (ar.target_type)
"""

# -- CRUD ------------------------------------------------------------

UPSERT_AUDIT_RESULT = """
MERGE (ar:AuditResult {id: $id})
SET ar.target = $target,
    ar.target_type = $target_type,
    ar.score_correto = $score_correto,
    ar.score_completo = $score_completo,
    ar.score_qualidade = $score_qualidade,
    ar.nota_geral = $nota_geral,
    ar.file_count = $file_count,
    ar.test_count = $test_count,
    ar.issues = $issues,
    ar.recommendations = $recommendations,
    ar.audited_at = $audited_at
RETURN ar
"""

CREATE_AUDIT_OF = """
MATCH (ar:AuditResult {id: $audit_id})
MATCH (target {id: $target_id})
MERGE (ar)-[:AUDIT_OF]->(target)
"""

# -- Read queries ----------------------------------------------------

GET_AUDIT_RESULTS = """
MATCH (ar:AuditResult)
RETURN ar.id AS id, ar.target AS target, ar.target_type AS target_type,
       ar.score_correto AS score_correto, ar.score_completo AS score_completo,
       ar.score_qualidade AS score_qualidade, ar.nota_geral AS nota_geral,
       ar.file_count AS file_count, ar.test_count AS test_count,
       ar.issues AS issues, ar.recommendations AS recommendations,
       ar.audited_at AS audited_at
ORDER BY ar.nota_geral ASC
LIMIT $limit
"""

GET_AUDIT_RESULTS_BY_TYPE = """
MATCH (ar:AuditResult)
WHERE ar.target_type = $target_type
RETURN ar.id AS id, ar.target AS target, ar.target_type AS target_type,
       ar.score_correto AS score_correto, ar.score_completo AS score_completo,
       ar.score_qualidade AS score_qualidade, ar.nota_geral AS nota_geral,
       ar.file_count AS file_count, ar.test_count AS test_count,
       ar.issues AS issues, ar.recommendations AS recommendations,
       ar.audited_at AS audited_at
ORDER BY ar.nota_geral ASC
LIMIT $limit
"""

GET_AUDIT_SUMMARY = """
MATCH (ar:AuditResult)
WITH ar.target_type AS target_type,
     count(ar) AS total_audits,
     avg(ar.nota_geral) AS avg_score,
     min(ar.nota_geral) AS min_score,
     max(ar.nota_geral) AS max_score,
     sum(ar.file_count) AS total_files,
     sum(ar.test_count) AS total_tests
RETURN target_type, total_audits, avg_score, min_score, max_score,
       total_files, total_tests
ORDER BY avg_score ASC
"""
