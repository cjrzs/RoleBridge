"""
Role Router - Role identification and routing to appropriate templates
"""
from typing import Dict, Optional
from core.role_profile import RoleProfileAnalyzer


class RoleRouter:
    """
    Routes content to appropriate role-specific handlers
    """
    
    # Predefined role mappings
    PREDEFINED_ROLES = {
        "developer": "developer",
        "dev": "developer",
        "开发": "developer",
        "product": "product",
        "pm": "product",
        "产品": "product",
        "ops": "ops",
        "运营": "ops",
        "management": "management",
        "manager": "management",
        "管理": "management",
    }
    
    def __init__(self):
        self.profile_analyzer = RoleProfileAnalyzer()
    
    async def analyze_role(self, role_name: str) -> Dict:
        """
        Analyze role and return role profile
        
        Args:
            role_name: Name of the target role
        
        Returns:
            Dictionary containing role profile information
        """
        # Normalize role name
        normalized_role = self._normalize_role(role_name)
        
        # Check if it's a predefined role
        if normalized_role in self.PREDEFINED_ROLES:
            template_key = self.PREDEFINED_ROLES[normalized_role]
            return {
                "role_name": role_name,
                "normalized_role": template_key,
                "is_predefined": True,
                "template": template_key
            }
        
        # For unknown roles, use dynamic analysis
        profile = await self.profile_analyzer.analyze(role_name)
        return {
            "role_name": role_name,
            "normalized_role": "dynamic",
            "is_predefined": False,
            "profile": profile,
            "template": "dynamic"
        }
    
    def _normalize_role(self, role_name: str) -> str:
        """
        Normalize role name to lowercase
        """
        return role_name.lower().strip()

