"""
Translation Agent - ReAct-based Agent for role translation
"""
from typing import Dict, Optional, Callable, Any, AsyncIterator
from enum import Enum
import asyncio
from core.tools import ToolRegistry
from core.thinking import ThinkingProcess, ThinkingStepType
from core.confirmation import ConfirmationManager, ConfirmationRequest
from services.llm_client import LLMClient


class AgentState(str, Enum):
    """Agent execution states"""
    INITIALIZING = "initializing"
    CHECKING_ROLE = "checking_role"
    ANALYZING_ROLE = "analyzing_role"
    EXTRACTING_FRAMEWORK = "extracting_framework"
    GENERATING_TRANSLATION = "generating_translation"
    NEEDS_CONFIRMATION = "needs_confirmation"
    COMPLETED = "completed"
    ERROR = "error"


class TranslationAgent:
    """
    ReAct-based Agent for role translation
    """
    
    # Predefined role mappings (same as RoleRouter)
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
    
    def __init__(
        self,
        websocket_send: Optional[Callable[[Dict], None]] = None
    ):
        """
        Initialize the Agent
        
        Args:
            websocket_send: Optional callback for sending WebSocket messages
        """
        self.tools = ToolRegistry()
        self.llm_client = LLMClient()
        self.thinking = ThinkingProcess()
        self.confirmation_manager = ConfirmationManager()
        self.websocket_send = websocket_send
        
        self.state = AgentState.INITIALIZING
        self.role_profile: Optional[Dict] = None
        self.framework_data: Optional[Dict] = None
        self.translated_content: Optional[str] = None
        self.error: Optional[str] = None
    
    async def run(
        self,
        content: str,
        target_role: str,
        source_role: Optional[str] = None
    ) -> Dict:
        """
        Main execution loop - ReAct workflow
        
        Args:
            content: Input content to translate
            target_role: Target role name
            source_role: Optional source role
            
        Returns:
            Dictionary containing translation result and metadata
        """
        try:
            # Step 1: Think - Analyze the task
            await self._think(f"开始翻译任务：将内容从{source_role or '未知'}角色视角转换为{target_role}角色视角")
            
            # Step 2: Act - Check role
            await self._think("检查目标角色是否为预定义角色")
            role_info = await self._check_role(target_role)
            
            # Step 3: Observe - Process role information
            await self._observe(f"角色信息：{role_info}")
            
            # Step 4: Act - Get or generate role template
            if role_info["is_predefined"]:
                await self._think(f"角色'{target_role}'是预定义角色，直接读取模板")
                template = self.tools.read_role_template(role_info["normalized_role"])
                if not template:
                    # Fallback to dynamic template if predefined template not found
                    template = await self.tools.load_dynamic_template()
                self.role_profile = {
                    "role_name": target_role,
                    "normalized_role": role_info["normalized_role"],
                    "is_predefined": True,
                    "template": template or ""
                }
            else:
                await self._think(f"角色'{target_role}'是未知角色，需要进行分析并生成模板")
                await self._analyze_unknown_role(target_role)
            
            # Step 5: Act - Extract framework data
            await self._think("提取决策框架数据")
            self.framework_data = await self.tools.extract_framework_data(content, source_role)
            await self._observe(f"框架数据提取完成，发现{len(self.framework_data.get('uncertainties', []))}个不确定点")
            
            # Step 6: Act - Generate translation based on template (for all roles)
            await self._think("根据确定的模板生成翻译内容")
            self.translated_content = await self._generate_translation(
                content,
                target_role,
                source_role
            )
            
            # Step 7: Decision - Complete
            await self._decision("翻译任务完成")
            self.state = AgentState.COMPLETED
            
            return {
                "content": self.translated_content,
                "role_analysis": self.role_profile,
                "framework_data": self.framework_data,
                "uncertainties": self.framework_data.get("uncertainties", []),
                "thinking_process": self.thinking.to_dict()
            }
            
        except Exception as e:
            self.state = AgentState.ERROR
            self.error = str(e)
            await self._think(f"发生错误：{str(e)}")
            raise
    
    async def run_stream(
        self,
        content: str,
        target_role: str,
        source_role: Optional[str] = None
    ) -> AsyncIterator[Dict]:
        """
        Stream version of run - yields progress updates
        
        Args:
            content: Input content to translate
            target_role: Target role name
            source_role: Optional source role
            
        Yields:
            Progress update dictionaries
        """
        try:
            # Step 1: Think
            await self._think(f"开始翻译任务：将内容从{source_role or '未知'}角色视角转换为{target_role}角色视角")
            
            # Step 2: Check role
            await self._think("检查目标角色是否为预定义角色")
            
            role_info = await self._check_role(target_role)
            yield {"type": "role_check", "data": role_info}
            
            # Step 3: Get or generate template
            if role_info["is_predefined"]:
                await self._think(f"角色'{target_role}'是预定义角色，直接读取模板")
                
                template = self.tools.read_role_template(role_info["normalized_role"])
                self.role_profile = {
                    "role_name": target_role,
                    "normalized_role": role_info["normalized_role"],
                    "is_predefined": True,
                    "template": template
                }
            else:
                await self._think(f"角色'{target_role}'是未知角色，需要进行分析并生成模板")
                
                async for update in self._analyze_unknown_role_stream(target_role):
                    yield update
            
            # Step 4: Extract framework data
            await self._think("提取决策框架数据")
            
            self.framework_data = await self.tools.extract_framework_data(content, source_role)
            yield {
                "type": "framework_extracted",
                "data": {
                    "uncertainties_count": len(self.framework_data.get("uncertainties", []))
                }
            }
            
            # Step 5: Generate translation based on template (for all roles)
            await self._think("根据确定的模板生成翻译内容")
            
            async for chunk in self._generate_translation_stream(
                content,
                target_role,
                source_role
            ):
                yield {"type": "translation_chunk", "data": chunk}
            
            # Step 6: Complete
            await self._decision("翻译任务完成")
            
            self.state = AgentState.COMPLETED
            yield {
                "type": "completed",
                "data": {
                    "role_analysis": self.role_profile,
                    "uncertainties": self.framework_data.get("uncertainties", []),
                    "thinking_process": self.thinking.to_dict()
                }
            }
            
        except Exception as e:
            self.state = AgentState.ERROR
            self.error = str(e)
            await self._think(f"发生错误：{str(e)}")
            yield {"type": "error", "data": {"error": str(e)}}
    
    async def _check_role(self, role_name: str) -> Dict:
        """
        Check if role is predefined
        
        Args:
            role_name: Role name to check
            
        Returns:
            Dictionary with role information
        """
        normalized = role_name.lower().strip()
        
        if normalized in self.PREDEFINED_ROLES:
            normalized_role = self.PREDEFINED_ROLES[normalized]
            return {
                "role_name": role_name,
                "normalized_role": normalized_role,
                "is_predefined": True
            }
        else:
            return {
                "role_name": role_name,
                "normalized_role": normalized,
                "is_predefined": False
            }
    
    async def _analyze_unknown_role(self, role_name: str):
        """
        Analyze unknown role and generate template
        
        Args:
            role_name: Unknown role name
        """
        await self._think(f"开始分析未知角色'{role_name}'的模板需求")
        
        # Step 1: Load existing templates as few-shot examples
        await self._think(f"加载已有角色模板作为参考示例，以便理解模板结构和风格")
        examples = self.tools.load_existing_templates()
        await self._observe(f"已加载{len(examples)}个预定义角色模板作为参考: {', '.join(examples.keys())}")
        
        # Step 2: Load dynamic template
        await self._think(f"加载动态角色模板作为基础框架")
        dynamic_template = await self.tools.load_dynamic_template()
        await self._observe(f"动态模板已加载，将作为生成'{role_name}'角色模板的基础框架")
        
        # Step 3: Analyze role characteristics
        await self._think(f"分析'{role_name}'角色的特征：")
        await self._think(f"  - 职责范围：该角色通常负责哪些工作")
        await self._think(f"  - 决策类型：该角色需要做出哪些类型的决策")
        await self._think(f"  - 关注重点：该角色最关心哪些方面的信息")
        await self._think(f"  - 输出需求：该角色需要什么格式的信息才能有效决策")
        
        # Step 4: Use LLM to analyze role
        await self._think(f"使用LLM基于已有模板示例分析'{role_name}'角色，生成适合的输出模板")
        analysis_result = await self.tools.analyze_role_with_llm(
            role_name,
            examples,
            dynamic_template
        )
        await self._observe(f"LLM分析完成，获得了'{role_name}'角色的特征分析结果")
        
        # Step 5: Explain template determination process
        await self._think(f"基于分析结果确定模板结构：")
        await self._think(f"  1. 参考了{len(examples)}个预定义角色的模板结构")
        await self._think(f"  2. 结合了动态模板的灵活性")
        await self._think(f"  3. 针对'{role_name}'角色的特定需求进行了定制化调整")
        
        self.role_profile = {
            "role_name": role_name,
            "normalized_role": "dynamic",
            "is_predefined": False,
            "analysis": analysis_result.get("analysis"),
            "template": analysis_result.get("template", dynamic_template)
        }
        
        await self._observe(f"已为'{role_name}'角色生成输出模板结构")
        await self._decision(f"模板确定过程完成：通过参考现有模板、分析角色特征、结合动态框架，为'{role_name}'角色定制了输出模板")
    
    async def _analyze_unknown_role_stream(self, role_name: str) -> AsyncIterator[Dict]:
        """
        Stream version of unknown role analysis
        
        Args:
            role_name: Unknown role name
            
        Yields:
            Progress updates
        """
        await self._think(f"开始分析未知角色'{role_name}'的模板需求")
        
        # Step 1: Load existing templates as examples
        await self._think(f"加载已有角色模板作为参考示例，以便理解模板结构和风格")
        examples = self.tools.load_existing_templates()
        
        await self._observe(f"已加载{len(examples)}个预定义角色模板作为参考: {', '.join(examples.keys())}")
        
        # Step 2: Load dynamic template
        await self._think(f"加载动态角色模板作为基础框架")
        dynamic_template = await self.tools.load_dynamic_template()
        
        await self._observe(f"动态模板已加载，将作为生成'{role_name}'角色模板的基础框架")
        
        # Step 3: Analyze role characteristics
        await self._think(f"分析'{role_name}'角色的特征：")
        await self._think(f"  - 职责范围：该角色通常负责哪些工作")
        await self._think(f"  - 决策类型：该角色需要做出哪些类型的决策")
        await self._think(f"  - 关注重点：该角色最关心哪些方面的信息")
        await self._think(f"  - 输出需求：该角色需要什么格式的信息才能有效决策")
        
        # Step 4: Use LLM to analyze
        await self._think(f"使用LLM基于已有模板示例分析'{role_name}'角色，生成适合的输出模板")
        
        analysis_result = await self.tools.analyze_role_with_llm(
            role_name,
            examples,
            dynamic_template
        )
        
        await self._observe(f"LLM分析完成，获得了'{role_name}'角色的特征分析结果")
        
        # Step 5: Explain template determination process
        await self._think(f"基于分析结果确定模板结构：")
        await self._think(f"  1. 参考了{len(examples)}个预定义角色的模板结构")
        await self._think(f"  2. 结合了动态模板的灵活性")
        await self._think(f"  3. 针对'{role_name}'角色的特定需求进行了定制化调整")
        
        self.role_profile = {
            "role_name": role_name,
            "normalized_role": "dynamic",
            "is_predefined": False,
            "analysis": analysis_result.get("analysis"),
            "template": analysis_result.get("template", dynamic_template)
        }
        
        await self._observe(f"已为'{role_name}'角色生成输出模板结构")
        await self._decision(f"模板确定过程完成：通过参考现有模板、分析角色特征、结合动态框架，为'{role_name}'角色定制了输出模板")
        
        yield {
            "type": "role_analyzed",
            "data": {
                "role_name": role_name,
                "template_generated": True,
                "analysis": analysis_result.get("analysis")
            }
        }
    
    async def _generate_translation(
        self,
        content: str,
        target_role: str,
        source_role: Optional[str]
    ) -> str:
        """
        Generate translation using LLM
        
        Args:
            content: Input content
            target_role: Target role
            source_role: Source role
            
        Returns:
            Translated content
        """
        template = self.role_profile.get("template", "")
        
        prompt = f"""请将以下内容转换为 {target_role} 角色的视角：

原始内容：
{content}

源角色：{source_role or "未指定"}

请使用以下模板结构输出：
{template}

注意：
1. 必须使用 Markdown 格式输出
2. 如果信息不足，请在相应位置明确说明不确定性
3. 不要简单复述原文，要切换视角重新表达
"""
        
        system_prompt = self.llm_client._load_system_prompt()
        
        response = await self.llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response
    
    async def _generate_translation_stream(
        self,
        content: str,
        target_role: str,
        source_role: Optional[str]
    ) -> AsyncIterator[str]:
        """
        Stream version of translation generation
        
        Args:
            content: Input content
            target_role: Target role
            source_role: Source role
            
        Yields:
            Translation chunks
        """
        template = self.role_profile.get("template", "")
        
        prompt = f"""请将以下内容转换为 {target_role} 角色的视角：

原始内容：
{content}

源角色：{source_role or "未指定"}

请使用以下模板结构输出：
{template}

注意：
1. 必须使用 Markdown 格式输出
2. 如果信息不足，请在相应位置明确说明不确定性
3. 不要简单复述原文，要切换视角重新表达
"""
        
        system_prompt = self.llm_client._load_system_prompt()
        
        # Use streaming translation
        async for chunk in self.llm_client.translate_stream(
            content=content,
            role_profile=self.role_profile,
            framework_data=self.framework_data or {},
            target_role=target_role
        ):
            yield chunk
    
    async def _think(self, content: str, metadata: Optional[Dict] = None):
        """
        Think step - record thinking process
        
        Args:
            content: Thinking content
            metadata: Optional metadata
        """
        step = self.thinking.add_step(ThinkingStepType.THINK, content, metadata)
        if self.websocket_send:
            self.websocket_send({
                "type": "thinking",
                "data": step.to_dict()
            })
    
    async def _act(self, action: str, metadata: Optional[Dict] = None):
        """
        Act step - record action
        
        Args:
            action: Action description
            metadata: Optional metadata
        """
        step = self.thinking.add_step(ThinkingStepType.ACT, action, metadata)
        if self.websocket_send:
            self.websocket_send({
                "type": "action",
                "data": step.to_dict()
            })
    
    async def _observe(self, observation: str, metadata: Optional[Dict] = None):
        """
        Observe step - record observation
        
        Args:
            observation: Observation content
            metadata: Optional metadata
        """
        step = self.thinking.add_step(ThinkingStepType.OBSERVE, observation, metadata)
        if self.websocket_send:
            self.websocket_send({
                "type": "observation",
                "data": step.to_dict()
            })
    
    async def _decision(self, decision: str, metadata: Optional[Dict] = None):
        """
        Decision step - record decision
        
        Args:
            decision: Decision content
            metadata: Optional metadata
        """
        step = self.thinking.add_step(ThinkingStepType.DECISION, decision, metadata)
        if self.websocket_send:
            self.websocket_send({
                "type": "decision",
                "data": step.to_dict()
            })
    
    async def _confirm(
        self,
        question: str,
        options: Optional[Dict] = None,
        timeout: float = 30.0
    ) -> Any:
        """
        Request user confirmation
        
        Args:
            question: Question to ask
            options: Optional options
            timeout: Timeout in seconds
            
        Returns:
            User response or None if timeout
        """
        request = self.confirmation_manager.create_request(question, options, timeout)
        
        # Send confirmation request via WebSocket
        if self.websocket_send:
            self.websocket_send({
                "type": "confirmation_request",
                "data": request.to_dict()
            })
        
        # Wait for response
        response = await request.wait_for_response()
        
        if response is None:
            await self._think(f"确认请求超时，使用默认策略")
        else:
            await self._observe(f"用户确认：{response}")
        
        return response

