"""
AI 友好型数据转换器

将标注数据转换为 LLM 训练格式，支持多种主流格式。

Validates: 设计文档 - AI 友好型数据转换
"""

import logging
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field

from src.i18n.translations import get_translation

logger = logging.getLogger(__name__)


class AIDataFormat(str, Enum):
    """AI 训练数据格式"""
    ALPACA = "alpaca"                  # Alpaca 格式
    SHAREGPT = "sharegpt"              # ShareGPT 格式
    OPENAI = "openai"                  # OpenAI 微调格式
    LLAMA_FACTORY = "llama_factory"    # LLaMA-Factory 格式
    FASTCHAT = "fastchat"              # FastChat 格式
    BELLE = "belle"                    # BELLE 格式（中文）
    CUSTOM = "custom"                  # 自定义格式
    
    @classmethod
    def get_display_name(cls, format_type: "AIDataFormat", lang: str = "zh") -> str:
        """获取格式的显示名称"""
        names = {
            cls.ALPACA: {"zh": "Alpaca 格式", "en": "Alpaca Format"},
            cls.SHAREGPT: {"zh": "ShareGPT 格式", "en": "ShareGPT Format"},
            cls.OPENAI: {"zh": "OpenAI 微调格式", "en": "OpenAI Fine-tuning Format"},
            cls.LLAMA_FACTORY: {"zh": "LLaMA-Factory 格式", "en": "LLaMA-Factory Format"},
            cls.FASTCHAT: {"zh": "FastChat 格式", "en": "FastChat Format"},
            cls.BELLE: {"zh": "BELLE 格式", "en": "BELLE Format"},
            cls.CUSTOM: {"zh": "自定义格式", "en": "Custom Format"},
        }
        return names.get(format_type, {}).get(lang, format_type.value)


class ConversionMetadata(BaseModel):
    """转换元数据"""
    source: str = Field(default="superinsight", description="数据来源")
    annotation_id: Optional[str] = Field(None, description="标注ID")
    quality_score: Optional[float] = Field(None, description="质量分数")
    annotator_id: Optional[str] = Field(None, description="标注员ID")
    project_id: Optional[str] = Field(None, description="项目ID")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="创建时间")
    lineage_id: Optional[str] = Field(None, description="血缘ID")


class ConversionResult(BaseModel):
    """转换结果"""
    success: bool = Field(..., description="是否成功")
    format: AIDataFormat = Field(..., description="目标格式")
    total_records: int = Field(default=0, description="总记录数")
    converted_records: int = Field(default=0, description="转换成功数")
    failed_records: int = Field(default=0, description="转换失败数")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="转换后的数据")
    errors: List[str] = Field(default_factory=list, description="错误信息")
    conversion_time_ms: float = Field(default=0.0, description="转换耗时（毫秒）")


class AIDataConverter:
    """
    AI 数据转换器
    
    将标注数据转换为各种 LLM 训练格式
    """
    
    def __init__(self, ontology_manager=None):
        """
        初始化 AI 数据转换器
        
        Args:
            ontology_manager: 企业本体管理器（可选）
        """
        self.ontology_manager = ontology_manager
        logger.info(get_translation("ontology.converter.initialized", "zh"))
    
    async def convert_annotations_to_training_data(
        self,
        annotations: List[Dict[str, Any]],
        output_format: AIDataFormat,
        include_lineage: bool = True,
        include_metadata: bool = True,
        system_prompt: Optional[str] = None
    ) -> ConversionResult:
        """
        将标注数据转换为 AI 训练格式
        
        Args:
            annotations: 标注数据列表
            output_format: 输出格式
            include_lineage: 是否包含血缘信息
            include_metadata: 是否包含元数据
            system_prompt: 系统提示词（可选）
            
        Returns:
            转换结果
        """
        start_time = datetime.now()
        result = ConversionResult(
            success=True,
            format=output_format,
            total_records=len(annotations)
        )
        
        try:
            if output_format == AIDataFormat.ALPACA:
                result.data = self._to_alpaca_format(
                    annotations, include_metadata, include_lineage
                )
            elif output_format == AIDataFormat.SHAREGPT:
                result.data = self._to_sharegpt_format(
                    annotations, include_metadata, system_prompt
                )
            elif output_format == AIDataFormat.OPENAI:
                result.data = self._to_openai_format(
                    annotations, include_metadata, system_prompt
                )
            elif output_format == AIDataFormat.LLAMA_FACTORY:
                result.data = self._to_llama_factory_format(
                    annotations, include_metadata
                )
            elif output_format == AIDataFormat.FASTCHAT:
                result.data = self._to_fastchat_format(
                    annotations, include_metadata, system_prompt
                )
            elif output_format == AIDataFormat.BELLE:
                result.data = self._to_belle_format(
                    annotations, include_metadata
                )
            else:
                result.data = annotations
            
            result.converted_records = len(result.data)
            result.failed_records = result.total_records - result.converted_records
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            logger.error(f"Conversion failed: {e}")
        
        end_time = datetime.now()
        result.conversion_time_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(
            f"Converted {result.converted_records}/{result.total_records} "
            f"annotations to {output_format.value} format"
        )
        
        return result
    
    def _to_alpaca_format(
        self,
        annotations: List[Dict[str, Any]],
        include_metadata: bool = True,
        include_lineage: bool = True
    ) -> List[Dict[str, Any]]:
        """
        转换为 Alpaca 格式
        
        格式:
        {
            "instruction": "问题/指令",
            "input": "上下文（可选）",
            "output": "回答",
            "metadata": {...}  # 可选
        }
        """
        result = []
        for ann in annotations:
            item = {
                "instruction": ann.get("question", ann.get("instruction", "")),
                "input": ann.get("context", ann.get("input", "")),
                "output": ann.get("answer", ann.get("output", "")),
            }
            
            if include_metadata:
                item["metadata"] = {
                    "source": "superinsight",
                    "annotation_id": ann.get("id"),
                    "quality_score": ann.get("quality_score", 1.0),
                    "annotator_id": ann.get("annotator_id"),
                    "project_id": ann.get("project_id"),
                }
                
                if include_lineage and ann.get("lineage_id"):
                    item["metadata"]["lineage_id"] = ann.get("lineage_id")
            
            result.append(item)
        
        return result
    
    def _to_sharegpt_format(
        self,
        annotations: List[Dict[str, Any]],
        include_metadata: bool = True,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        转换为 ShareGPT 格式
        
        格式:
        {
            "conversations": [
                {"from": "human", "value": "问题"},
                {"from": "gpt", "value": "回答"}
            ],
            "system": "系统提示词",
            "metadata": {...}
        }
        """
        result = []
        for ann in annotations:
            conversations = []
            
            # 添加用户问题
            question = ann.get("question", ann.get("instruction", ""))
            context = ann.get("context", ann.get("input", ""))
            
            if context:
                user_content = f"{context}\n\n{question}"
            else:
                user_content = question
            
            conversations.append({
                "from": "human",
                "value": user_content
            })
            
            # 添加助手回答
            conversations.append({
                "from": "gpt",
                "value": ann.get("answer", ann.get("output", ""))
            })
            
            # 处理多轮对话历史
            if ann.get("history"):
                for hist in ann["history"]:
                    if isinstance(hist, dict):
                        conversations.insert(-2, {
                            "from": "human",
                            "value": hist.get("question", "")
                        })
                        conversations.insert(-1, {
                            "from": "gpt",
                            "value": hist.get("answer", "")
                        })
            
            item = {
                "conversations": conversations,
                "system": system_prompt or ann.get("system_prompt", ""),
            }
            
            if include_metadata:
                item["metadata"] = {
                    "source": "superinsight",
                    "annotation_id": ann.get("id"),
                    "quality_score": ann.get("quality_score", 1.0),
                }
            
            result.append(item)
        
        return result
    
    def _to_openai_format(
        self,
        annotations: List[Dict[str, Any]],
        include_metadata: bool = True,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        转换为 OpenAI 微调格式
        
        格式:
        {
            "messages": [
                {"role": "system", "content": "系统提示词"},
                {"role": "user", "content": "问题"},
                {"role": "assistant", "content": "回答"}
            ]
        }
        """
        result = []
        for ann in annotations:
            messages = []
            
            # 系统提示词
            sys_prompt = system_prompt or ann.get("system_prompt")
            if sys_prompt:
                messages.append({
                    "role": "system",
                    "content": sys_prompt
                })
            
            # 处理多轮对话历史
            if ann.get("history"):
                for hist in ann["history"]:
                    if isinstance(hist, dict):
                        messages.append({
                            "role": "user",
                            "content": hist.get("question", "")
                        })
                        messages.append({
                            "role": "assistant",
                            "content": hist.get("answer", "")
                        })
            
            # 用户问题
            question = ann.get("question", ann.get("instruction", ""))
            context = ann.get("context", ann.get("input", ""))
            
            if context:
                user_content = f"{context}\n\n{question}"
            else:
                user_content = question
            
            messages.append({
                "role": "user",
                "content": user_content
            })
            
            # 助手回答
            messages.append({
                "role": "assistant",
                "content": ann.get("answer", ann.get("output", ""))
            })
            
            item = {"messages": messages}
            
            # OpenAI 格式通常不包含额外元数据
            # 但可以通过 name 字段添加标识
            if include_metadata and ann.get("id"):
                # 在第一条消息中添加标识
                if messages and messages[0].get("role") == "system":
                    messages[0]["name"] = f"ann_{ann.get('id', '')[:8]}"
            
            result.append(item)
        
        return result
    
    def _to_llama_factory_format(
        self,
        annotations: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        转换为 LLaMA-Factory 格式
        
        格式:
        {
            "instruction": "指令",
            "input": "输入",
            "output": "输出",
            "history": [["问题1", "回答1"], ["问题2", "回答2"]]
        }
        """
        result = []
        for ann in annotations:
            item = {
                "instruction": ann.get("question", ann.get("instruction", "")),
                "input": ann.get("context", ann.get("input", "")),
                "output": ann.get("answer", ann.get("output", "")),
            }
            
            # 处理历史对话
            history = []
            if ann.get("history"):
                for hist in ann["history"]:
                    if isinstance(hist, dict):
                        history.append([
                            hist.get("question", ""),
                            hist.get("answer", "")
                        ])
                    elif isinstance(hist, (list, tuple)) and len(hist) >= 2:
                        history.append([hist[0], hist[1]])
            
            if history:
                item["history"] = history
            
            if include_metadata:
                item["metadata"] = {
                    "source": "superinsight",
                    "annotation_id": ann.get("id"),
                }
            
            result.append(item)
        
        return result
    
    def _to_fastchat_format(
        self,
        annotations: List[Dict[str, Any]],
        include_metadata: bool = True,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        转换为 FastChat 格式
        
        格式:
        {
            "id": "唯一ID",
            "conversations": [
                {"from": "human", "value": "问题"},
                {"from": "gpt", "value": "回答"}
            ]
        }
        """
        result = []
        for ann in annotations:
            conversations = []
            
            # 系统提示词作为第一条消息
            sys_prompt = system_prompt or ann.get("system_prompt")
            if sys_prompt:
                conversations.append({
                    "from": "system",
                    "value": sys_prompt
                })
            
            # 用户问题
            question = ann.get("question", ann.get("instruction", ""))
            context = ann.get("context", ann.get("input", ""))
            
            if context:
                user_content = f"{context}\n\n{question}"
            else:
                user_content = question
            
            conversations.append({
                "from": "human",
                "value": user_content
            })
            
            # 助手回答
            conversations.append({
                "from": "gpt",
                "value": ann.get("answer", ann.get("output", ""))
            })
            
            item = {
                "id": ann.get("id", str(uuid4())),
                "conversations": conversations
            }
            
            result.append(item)
        
        return result
    
    def _to_belle_format(
        self,
        annotations: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        转换为 BELLE 格式（中文优化）
        
        格式:
        {
            "instruction": "指令",
            "input": "输入",
            "output": "输出"
        }
        """
        result = []
        for ann in annotations:
            item = {
                "instruction": ann.get("question", ann.get("instruction", "")),
                "input": ann.get("context", ann.get("input", "")),
                "output": ann.get("answer", ann.get("output", "")),
            }
            
            result.append(item)
        
        return result
    
    def get_supported_formats(self, lang: str = "zh") -> List[Dict[str, str]]:
        """
        获取支持的格式列表
        
        Args:
            lang: 语言代码
            
        Returns:
            格式列表
        """
        return [
            {
                "value": fmt.value,
                "label": AIDataFormat.get_display_name(fmt, lang),
                "description": self._get_format_description(fmt, lang)
            }
            for fmt in AIDataFormat
        ]
    
    def _get_format_description(self, fmt: AIDataFormat, lang: str = "zh") -> str:
        """获取格式描述"""
        descriptions = {
            AIDataFormat.ALPACA: {
                "zh": "Stanford Alpaca 格式，适用于指令微调",
                "en": "Stanford Alpaca format for instruction fine-tuning"
            },
            AIDataFormat.SHAREGPT: {
                "zh": "ShareGPT 对话格式，支持多轮对话",
                "en": "ShareGPT conversation format with multi-turn support"
            },
            AIDataFormat.OPENAI: {
                "zh": "OpenAI 官方微调格式",
                "en": "Official OpenAI fine-tuning format"
            },
            AIDataFormat.LLAMA_FACTORY: {
                "zh": "LLaMA-Factory 格式，支持历史对话",
                "en": "LLaMA-Factory format with history support"
            },
            AIDataFormat.FASTCHAT: {
                "zh": "FastChat 格式，适用于 Vicuna 等模型",
                "en": "FastChat format for Vicuna and similar models"
            },
            AIDataFormat.BELLE: {
                "zh": "BELLE 格式，中文优化",
                "en": "BELLE format optimized for Chinese"
            },
            AIDataFormat.CUSTOM: {
                "zh": "自定义格式，保持原始数据结构",
                "en": "Custom format, keeps original data structure"
            },
        }
        return descriptions.get(fmt, {}).get(lang, "")
    
    async def validate_annotations(
        self,
        annotations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        验证标注数据是否可以转换
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            验证结果
        """
        valid_count = 0
        invalid_count = 0
        issues = []
        
        for i, ann in enumerate(annotations):
            # 检查必需字段
            has_question = bool(ann.get("question") or ann.get("instruction"))
            has_answer = bool(ann.get("answer") or ann.get("output"))
            
            if not has_question:
                issues.append({
                    "index": i,
                    "issue": "missing_question",
                    "message_zh": "缺少问题/指令字段",
                    "message_en": "Missing question/instruction field"
                })
                invalid_count += 1
            elif not has_answer:
                issues.append({
                    "index": i,
                    "issue": "missing_answer",
                    "message_zh": "缺少回答/输出字段",
                    "message_en": "Missing answer/output field"
                })
                invalid_count += 1
            else:
                valid_count += 1
        
        return {
            "total": len(annotations),
            "valid": valid_count,
            "invalid": invalid_count,
            "issues": issues,
            "can_convert": invalid_count == 0
        }
