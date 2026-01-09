"""
Translation Engine - Main translation orchestration
"""
from typing import Dict, Optional, List
from core.role_router import RoleRouter
from core.decision_framework import DecisionFramework
from services.llm_client import LLMClient


class TranslationEngine:
    """
    Main translation engine that orchestrates the translation process
    """
    
    def __init__(self):
        self.role_router = RoleRouter()
        self.decision_framework = DecisionFramework()
        self.llm_client = LLMClient()
    
    async def translate(
        self,
        content: str,
        target_role: str,
        source_role: Optional[str] = None
    ) -> Dict:
        """
        Translate content from source role perspective to target role perspective
        
        Args:
            content: Input content to translate
            target_role: Target role (e.g., "developer", "product", "ops", "management")
            source_role: Optional source role for context
        
        Returns:
            Dictionary containing translated content and metadata
        """
        # Step 1: Analyze target role
        role_profile = await self.role_router.analyze_role(target_role)
        
        # Step 2: Extract decision framework elements
        framework_data = await self.decision_framework.extract(content, source_role)
        
        # Step 3: Generate translation using LLM
        translated_content = await self.llm_client.translate(
            content=content,
            role_profile=role_profile,
            framework_data=framework_data,
            target_role=target_role
        )
        
        # Step 4: Extract uncertainties
        uncertainties = framework_data.get("uncertainties", [])
        
        return {
            "content": translated_content,
            "role_analysis": role_profile,
            "uncertainties": uncertainties
        }
    
    async def translate_stream(
        self,
        content: str,
        target_role: str,
        source_role: Optional[str] = None
    ):
        """
        Stream translation results
        """
        # Similar to translate but with streaming support
        role_profile = await self.role_router.analyze_role(target_role)
        framework_data = await self.decision_framework.extract(content, source_role)
        
        async for chunk in self.llm_client.translate_stream(
            content=content,
            role_profile=role_profile,
            framework_data=framework_data,
            target_role=target_role
        ):
            yield chunk

