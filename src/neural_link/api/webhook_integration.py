"""
Integracao do Neural Link com o webhook system (FastAPI).
Adiciona endpoint POST /neural-link ao webhook_listener.
"""

import logging

logger = logging.getLogger(__name__)


def register_neural_link_routes(app):
    """
    Registra rotas do Neural Link no app FastAPI existente.

    Args:
        app: FastAPI app instance
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.post("/neural-link")
    async def neural_link_endpoint(request: Request):
        """
        Endpoint unificado do Neural Link.

        Body JSON:
            query (str): Texto do request
            context (dict, optional): Contexto adicional
            mode (str, optional): "process" (default) | "search" | "status" | "stats"
        """
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid JSON body"},
            )

        query = body.get("query", "")
        context = body.get("context")
        mode = body.get("mode", "process")

        try:
            from .interface import UnifiedInterface
            interface = UnifiedInterface.get_instance()

            if mode == "search":
                top_k = body.get("top_k", 10)
                results = interface.search(query, top_k=top_k)
                return JSONResponse(content={"results": results})

            elif mode == "status":
                agents = interface.get_agent_status()
                return JSONResponse(content={"agents": agents})

            elif mode == "stats":
                stats = interface.get_graph_stats()
                return JSONResponse(content={"stats": stats})

            elif mode == "health":
                health = interface.health()
                return JSONResponse(content=health)

            else:
                # Default: process (orquestracao completa)
                result = interface.process(query, context=context)
                return JSONResponse(content=result)

        except Exception as e:
            logger.error(f"Neural Link endpoint error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)},
            )

    @app.get("/neural-link/health")
    async def neural_link_health():
        """Health check do Neural Link."""
        try:
            from .interface import UnifiedInterface
            interface = UnifiedInterface.get_instance()
            return JSONResponse(content=interface.health())
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": str(e)},
            )

    logger.info("Neural Link routes registered on /neural-link")
