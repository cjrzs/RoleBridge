"""
LLM Client - DeepSeek API Integration
"""
import httpx
import os
import json
from typing import Dict, AsyncIterator, List
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径，以便导入 config 模块
ROOT_DIR = Path(__file__).parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL


class LLMClient:
    """
    DeepSeek LLM API Client
    """
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.api_base = DEEPSEEK_API_BASE
        self.model = DEEPSEEK_MODEL
        self.base_url = f"{self.api_base}/v1/chat/completions"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """
        Generic chat method for LLM calls
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature
            stream: Whether to stream the response
            
        Returns:
            Response content (or AsyncIterator if stream=True)
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": stream
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def translate(
        self,
        content: str,
        role_profile: Dict,
        framework_data: Dict,
        target_role: str
    ) -> str:
        """
        Translate content using LLM
        
        Args:
            content: Input content
            role_profile: Role profile information
            framework_data: Decision framework data
            target_role: Target role name
        
        Returns:
            Translated content in Markdown format
        """
        # Build prompt from templates
        prompt = self._build_prompt(content, role_profile, framework_data, target_role)
        
        # Call LLM API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": self._load_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "stream": False
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def translate_stream(
        self,
        content: str,
        role_profile: Dict,
        framework_data: Dict,
        target_role: str
    ) -> AsyncIterator[str]:
        """
        Stream translation results
        
        Yields:
            Chunks of translated content
        """
        prompt = self._build_prompt(content, role_profile, framework_data, target_role)
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": self._load_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "stream": True
                },
                timeout=60.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            # Parse SSE JSON data
                            json_data = json.loads(data)
                            # Extract content from choices[0].delta.content
                            if "choices" in json_data and len(json_data["choices"]) > 0:
                                delta = json_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            # Skip invalid JSON lines
                            continue
                        except Exception as e:
                            # Log error but continue processing
                            print(f"Error parsing stream data: {e}")
                            continue
    
    def _build_prompt(
        self,
        content: str,
        role_profile: Dict,
        framework_data: Dict,
        target_role: str
    ) -> str:
        """
        Build prompt from templates and data
        """
        # Get template from role_profile (it already contains template content)
        # If template is not provided, try to load by normalized_role name
        template = role_profile.get("template")
        if not template:
            # Fallback: try to load template by normalized_role name
            normalized_role = role_profile.get("normalized_role", "dynamic")
            template = self._load_role_template(normalized_role)
        
        prompt = f"""
请将以下内容转换为 {target_role} 角色的视角：

原始内容：
{content}

请使用以下模板结构输出：
{template}

注意：
1. 必须使用 Markdown 格式输出
2. 如果信息不足，请在相应位置明确说明不确定性
3. 不要简单复述原文，要切换视角重新表达
"""
        return prompt
    
    def _load_system_prompt(self) -> str:
        """
        Load system prompt from file
        """
        try:
            with open("prompts/system.md", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "你是一个专业的跨职能沟通翻译助手。"
    
    def _load_role_template(self, template_key: str) -> str:
        """
        Load role-specific template
        
        Args:
            template_key: Template key name (e.g., "developer", "dynamic")
                          Must be a simple filename without path separators
        """
        # Security check: ensure template_key is a valid filename
        # Remove any path separators and special characters
        safe_key = os.path.basename(template_key).replace(".md", "").strip()
        if not safe_key or len(safe_key) > 100:  # Prevent extremely long filenames
            safe_key = "dynamic"
        
        # Try multiple possible paths
        possible_paths = [
            Path("backend/prompts/roles"),
            Path("prompts/roles"),
            Path(__file__).parent.parent / "prompts" / "roles",
            Path(__file__).parent.parent.parent / "prompts" / "roles"
        ]
        
        template_file = None
        for base_path in possible_paths:
            candidate = base_path / f"{safe_key}.md"
            if candidate.exists():
                template_file = candidate
                break
        
        if template_file:
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading template {safe_key}: {e}")
        
        # Fallback to dynamic template
        for base_path in possible_paths:
            candidate = base_path / "dynamic.md"
            if candidate.exists():
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass
        
        # Final fallback
        return "请根据角色特点，结构化输出内容。"

