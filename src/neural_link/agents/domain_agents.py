"""
Domain Agent Wrappers - Marketing, Social Media, AI Engineer.

Extends CrmDomainAgent 3-layer context pattern:
1. UseCase specs (acceptance criteria)
2. Code chunks (implementation reality)
3. Graph context (module relationships)
"""

import logging
from typing import Any

from src.neural_link.agents.crm_domain_agent import CrmDomainAgent

logger = logging.getLogger(__name__)


class MarketingDomainAgent(CrmDomainAgent):
    """
    Marketing Domain Agent with 3-layer context injection.
    
    Specializes in: copywriting, campaign strategy, A/B testing, audience targeting.
    """

    def __init__(self):
        super().__init__(
            domain="marketing",
            categories=["marketing", "campaigns", "email", "copywriting"],
            agent_capabilities={
                "copywriting",
                "campaign_strategy",
                "a_b_testing",
                "audience_targeting",
                "email_marketing",
                "content_creation",
            },
        )


class SocialMediaDomainAgent(CrmDomainAgent):
    """
    Social Media Domain Agent with 3-layer context injection.
    
    Specializes in: social posting, engagement analysis, content calendar.
    """

    def __init__(self):
        super().__init__(
            domain="social_media",
            categories=["social_media", "engagement", "content"],
            agent_capabilities={
                "social_posting",
                "engagement_analysis",
                "content_calendar",
                "hashtag_strategy",
                "audience_growth",
                "analytics",
            },
        )


class AiEngineerDomainAgent(CrmDomainAgent):
    """
    AI Engineer Domain Agent with 3-layer context injection.
    
    Specializes in: model evaluation, pipeline design, RAG architecture.
    """

    def __init__(self):
        super().__init__(
            domain="ai_engineering",
            categories=["ml", "ai", "pipeline", "model"],
            agent_capabilities={
                "model_evaluation",
                "pipeline_design",
                "data_engineering",
                "embedding_optimization",
                "rag_architecture",
                "fine_tuning",
                "ai",
                "machine_learning",
                "llm",
                "rag",
                "embeddings",
            },
        )
