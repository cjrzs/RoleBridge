"""
Streaming Utilities - SSE / Stream Helpers
"""
from typing import AsyncIterator, Optional
from core.engine import TranslationEngine


async def generate_translation_stream(
    engine: TranslationEngine,
    content: str,
    target_role: str,
    source_role: Optional[str] = None
) -> AsyncIterator[str]:
    """
    Generate SSE stream for translation results
    
    Args:
        engine: Translation engine instance
        content: Input content
        target_role: Target role
        source_role: Optional source role
    
    Yields:
        SSE formatted chunks
    """
    async for chunk in engine.translate_stream(content, target_role, source_role):
        # Format as SSE
        yield f"data: {chunk}\n\n"
    
    # Send completion signal
    yield "data: [DONE]\n\n"
