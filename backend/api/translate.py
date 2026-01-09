"""
Translation API Endpoint
"""
from fastapi import APIRouter, HTTPException
from schemas.translate import TranslateRequest, TranslateResponse
from core.engine import TranslationEngine
from core.agent import TranslationAgent

router = APIRouter()

# Initialize translation engine (for backward compatibility)
engine = TranslationEngine()


@router.post("/translate", response_model=TranslateResponse)
async def translate(request: TranslateRequest):
    """
    Translate content from one role perspective to another (REST API - backward compatible)
    
    This endpoint uses the new Agent-based approach but returns results in the same format
    """
    try:
        # Use Agent for translation
        agent = TranslationAgent()
        result = await agent.run(
            content=request.content,
            target_role=request.target_role,
            source_role=request.source_role
        )
        
        return TranslateResponse(
            translated_content=result["content"],
            role_analysis=result.get("role_analysis"),
            uncertainties=result.get("uncertainties", []),
            thinking_process=result.get("thinking_process")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/translate/stream")
async def translate_stream(request: TranslateRequest):
    """
    Stream translation results (SSE) - backward compatible
    
    Note: For real-time thinking process, use WebSocket endpoint /api/ws/translate
    """
    from fastapi.responses import StreamingResponse
    from utils.streaming import generate_translation_stream
    
    async def event_generator():
        async for chunk in generate_translation_stream(
            engine=engine,
            content=request.content,
            target_role=request.target_role,
            source_role=request.source_role
        ):
            yield chunk
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

