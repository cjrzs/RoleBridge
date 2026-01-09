"""
Tools System - Tools available for Agent to use
"""
import os
from typing import Dict, List, Optional
from pathlib import Path
from services.llm_client import LLMClient


class ToolRegistry:
    """
    Registry of tools available to the Agent
    """
    
    def __init__(self):
        self.llm_client = LLMClient()
        # Try multiple possible paths
        possible_paths = [
            Path("backend/prompts/roles"),
            Path("prompts/roles"),
            Path(__file__).parent.parent / "prompts" / "roles",
            Path(__file__).parent.parent.parent / "prompts" / "roles"
        ]
        self.roles_dir = None
        for path in possible_paths:
            if path.exists():
                self.roles_dir = path
                break
        if self.roles_dir is None:
            # Default fallback - try relative to current working directory
            self.roles_dir = Path("prompts/roles")
        self.predefined_roles = ["developer", "product", "ops", "management"]
    
    def read_role_template(self, role_name: str) -> Optional[str]:
        """
        Read predefined role template
        
        Args:
            role_name: Name of the role
            
        Returns:
            Template content or None if not found
        """
        template_file = self.roles_dir / f"{role_name}.md"
        try:
            if template_file.exists():
                with open(template_file, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            print(f"Error reading template {role_name}: {e}")
        return None
    
    def load_existing_templates(self) -> Dict[str, str]:
        """
        Load all existing role templates as few-shot examples
        
        Returns:
            Dictionary mapping role names to template content
        """
        templates = {}
        for role in self.predefined_roles:
            # read_role_template is synchronous, so we can call it directly
            template = self.read_role_template(role)
            if template:
                templates[role] = template
        return templates
    
    async def load_dynamic_template(self) -> str:
        """
        Load dynamic role template
        
        Returns:
            Dynamic template content
        """
        template_file = self.roles_dir / "dynamic.md"
        try:
            if template_file.exists():
                with open(template_file, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception:
            pass
        return "# Dynamic Role Template\n\n请根据角色特点，结构化输出内容。"
    
    async def analyze_role_with_llm(
        self,
        role_name: str,
        examples: Dict[str, str],
        dynamic_template: str
    ) -> Dict:
        """
        Use LLM to analyze unknown role and generate template
        
        Args:
            role_name: Name of the unknown role
            examples: Existing role templates as few-shot examples
            dynamic_template: Dynamic role template as guidance
            
        Returns:
            Dictionary containing role analysis and generated template
        """
        # Build few-shot examples string
        examples_text = ""
        for role, template in examples.items():
            examples_text += f"\n\n## {role}角色模板示例:\n{template}\n"
        
        prompt = f"""你是一个角色分析专家。请分析"{role_name}"这个角色，并为其生成一个输出模板。

## 动态角色处理指南:
{dynamic_template}

## 已有角色模板示例（作为参考）:
{examples_text}

## 任务要求:
1. 分析"{role_name}"角色的职责范围、决策类型和关注重点
2. 参考已有模板的结构，为"{role_name}"生成一个适合的输出模板
3. 模板应该符合该角色的思维模型和决策需求
4. 使用Markdown格式输出

请按照以下JSON格式输出:
{{
    "role_name": "{role_name}",
    "responsibilities": ["职责1", "职责2", ...],
    "decision_types": ["决策类型1", "决策类型2", ...],
    "focus_areas": ["关注点1", "关注点2", ...],
    "output_template": "生成的Markdown模板内容"
}}
"""
        
        try:
            # Use LLM to analyze
            response = await self.llm_client.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的角色分析专家，擅长分析不同角色的职责和思维模式。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7
            )
            
            # Parse response (simplified - in production, use proper JSON parsing)
            # For now, return the response as template
            return {
                "role_name": role_name,
                "analysis": response,
                "template": response  # Simplified: use full response as template
            }
        except Exception as e:
            print(f"Error analyzing role with LLM: {e}")
            return {
                "role_name": role_name,
                "analysis": None,
                "template": dynamic_template  # Fallback to dynamic template
            }
    
    async def extract_framework_data(self, content: str, source_role: Optional[str] = None) -> Dict:
        """
        Extract decision framework data from content
        
        Args:
            content: Input content
            source_role: Optional source role for context
            
        Returns:
            Dictionary containing extracted framework data
        """
        framework_dimensions = [
            "context",      # 事情是什么
            "goal",         # 目标与意图
            "action",       # 可采取的行动或方案
            "value",        # 预期收益或价值
            "cost",         # 成本与投入
            "risk",         # 风险与不确定性
            "decision"      # 决策建议或下一步
        ]
        
        prompt = f"""请从以下内容中提取决策框架信息。

内容:
{content}

源角色: {source_role or "未指定"}

请按照以下维度提取信息:
1. Context (事情是什么) - 当前情况描述、相关背景信息
2. Goal (目标与意图) - 想要达成的目标、期望的结果
3. Action (可采取的行动或方案) - 可行的解决方案、实施步骤
4. Value (预期收益或价值) - 对用户/业务的价值、长期收益
5. Cost (成本与投入) - 人力成本、时间成本、资源投入
6. Risk (风险与不确定性) - 技术风险、业务风险、需要澄清的问题
7. Decision (决策建议或下一步) - 推荐方案、下一步行动

请以JSON格式输出，如果某个维度信息不足，请标记为null或列出需要澄清的问题。
"""
        
        try:
            response = await self.llm_client.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个信息提取专家，擅长从文本中提取结构化信息。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3
            )
            
            # Simplified: return response as framework data
            # In production, parse JSON properly
            framework_data = {
                "context": None,
                "goal": None,
                "action": None,
                "value": None,
                "cost": None,
                "risk": None,
                "decision": None,
                "uncertainties": [],
                "raw_extraction": response
            }
            
            # Identify uncertainties
            uncertainties = self._identify_uncertainties(content)
            framework_data["uncertainties"] = uncertainties
            
            return framework_data
        except Exception as e:
            print(f"Error extracting framework data: {e}")
            return {
                "context": None,
                "goal": None,
                "action": None,
                "value": None,
                "cost": None,
                "risk": None,
                "decision": None,
                "uncertainties": self._identify_uncertainties(content)
            }
    
    def _identify_uncertainties(self, content: str) -> List[str]:
        """
        Identify areas of uncertainty in the content
        
        Args:
            content: Input content
            
        Returns:
            List of uncertainty questions
        """
        uncertainties = []
        vague_indicators = ["可能", "也许", "大概", "不确定", "需要确认", "待定"]
        for indicator in vague_indicators:
            if indicator in content:
                uncertainties.append(f"内容中包含不确定性表述: {indicator}")
        return uncertainties

