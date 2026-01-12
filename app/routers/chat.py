from typing import Annotated
from fastapi import APIRouter, Request, Depends, HTTPException, status

from ..models import ChatMessage, AIChatResponse
from ..auth import get_current_user
from ..services.agents import AgentsService
from ..utils.limiter import limiter
from ..utils.logging import logger
from ..config import CONFIG
from agents import RunConfig

router = APIRouter(tags=["Chat"])


rate_limiting_config = CONFIG.rate_limiting
CHAT_RATE_LIMIT = rate_limiting_config.chat_limit

ai_service_config = CONFIG.ai_service


# agents_config = RunConfig(model=get_preffered_model(), tracing_disabled=True)
# agents_service = AgentsService(agents_config)
agents_service = AgentsService()


@router.post("/chat", response_model=AIChatResponse)
@limiter.limit(CHAT_RATE_LIMIT)
async def post_chat_message(
    request: Request,
    chat_message: ChatMessage,
    current_user: Annotated[str, Depends(get_current_user)],
):
    """
    Receives a chat message, validates it, sends it to the AI service,
    and returns the response. Requires authentication via Bearer token.
    """
    logger.info(f"Chat request received from user: {current_user}")
    logger.debug(f"Chat message: '{chat_message.message[:50]}...'")

    # Pydantic handles input validation for chat_message
    if not chat_message.message:
        logger.warning("Empty message received.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty."
        )

    try:
        ai_response_text = await agents_service.invoke(chat_message.message)
        logger.info(f"AI response successful for user: {current_user}")
        return AIChatResponse(
            response=ai_response_text,
            processed_by=agents_service.get_preffered_model_name(),
        )
    except Exception as e:
        logger.error(
            f"Error invoking AI service for user {current_user}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service encountered an error.",
        )
