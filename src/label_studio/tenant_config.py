"""
Label Studio Tenant Configuration Manager

Manages tenant-specific Label Studio configurations and templates.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
from enum import Enum

from src.middleware.tenant_middleware import get_current_tenant
from src.database.connection import get_db_session
from src.database.models import DocumentModel, TaskModel

logger = logging.getLogger(__name__)


class AnnotationType(str, Enum):
    """Supported annotation types."""
    TEXT_CLASSIFICATION = "text_classification"
    NAMED_ENTITY_RECOGNITION = "ner"
    TEXT_SUMMARIZATION = "summarization"
    SENTIMENT_ANALYSIS = "sentiment"
    QUESTION_ANSWERING = "qa"
    IMAGE_CLASSIFICATION = "image_classification"
    OBJECT_DETECTION = "object_detection"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    CUSTOM = "custom"


@dataclass
class LabelConfig:
    """Label Studio configuration template."""
    name: str
    annotation_type: AnnotationType
    config_xml: str
    description: str
    instructions: str
    example_data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "annotation_type": self.annotation_type.value,
            "config_xml": self.config_xml,
            "description": self.description,
            "instructions": self.instructions,
            "example_data": self.example_data
        }


class LabelStudioConfigManager:
    """Manages Label Studio configurations for tenants."""
    
    def __init__(self):
        self.default_configs = self._create_default_configs()
    
    def _create_default_configs(self) -> Dict[str, LabelConfig]:
        """Create default configuration templates."""
        
        configs = {}
        
        # Text Classification
        configs["text_classification"] = LabelConfig(
            name="Text Classification",
            annotation_type=AnnotationType.TEXT_CLASSIFICATION,
            config_xml="""
            <View>
              <Header value="Classify the text"/>
              <Text name="text" value="$text"/>
              <Choices name="sentiment" toName="text" choice="single-radio">
                <Choice value="positive"/>
                <Choice value="negative"/>
                <Choice value="neutral"/>
              </Choices>
            </View>
            """,
            description="Basic text classification with sentiment analysis",
            instructions="Read the text and select the appropriate sentiment category.",
            example_data={"text": "This is a sample text for classification."}
        )
        
        # Named Entity Recognition
        configs["ner"] = LabelConfig(
            name="Named Entity Recognition",
            annotation_type=AnnotationType.NAMED_ENTITY_RECOGNITION,
            config_xml="""
            <View>
              <Header value="Label entities in the text"/>
              <Text name="text" value="$text"/>
              <Labels name="label" toName="text">
                <Label value="PERSON" background="red"/>
                <Label value="ORGANIZATION" background="blue"/>
                <Label value="LOCATION" background="green"/>
                <Label value="DATE" background="yellow"/>
                <Label value="MONEY" background="purple"/>
              </Labels>
            </View>
            """,
            description="Named entity recognition with common entity types",
            instructions="Highlight and label entities in the text according to their type.",
            example_data={"text": "John Smith works at Microsoft in Seattle since 2020."}
        )
        
        # Text Summarization
        configs["summarization"] = LabelConfig(
            name="Text Summarization",
            annotation_type=AnnotationType.TEXT_SUMMARIZATION,
            config_xml="""
            <View>
              <Header value="Create a summary of the text"/>
              <Text name="text" value="$text"/>
              <TextArea name="summary" toName="text" 
                       placeholder="Write a concise summary..."
                       maxSubmissions="1" rows="5"/>
            </View>
            """,
            description="Text summarization task",
            instructions="Read the text and write a concise summary capturing the main points.",
            example_data={"text": "Long article text that needs to be summarized..."}
        )
        
        # Sentiment Analysis
        configs["sentiment"] = LabelConfig(
            name="Sentiment Analysis",
            annotation_type=AnnotationType.SENTIMENT_ANALYSIS,
            config_xml="""
            <View>
              <Header value="Analyze sentiment and emotion"/>
              <Text name="text" value="$text"/>
              <Choices name="sentiment" toName="text" choice="single-radio">
                <Choice value="very_positive"/>
                <Choice value="positive"/>
                <Choice value="neutral"/>
                <Choice value="negative"/>
                <Choice value="very_negative"/>
              </Choices>
              <Choices name="emotion" toName="text" choice="multiple">
                <Choice value="joy"/>
                <Choice value="anger"/>
                <Choice value="fear"/>
                <Choice value="sadness"/>
                <Choice value="surprise"/>
                <Choice value="disgust"/>
              </Choices>
            </View>
            """,
            description="Detailed sentiment and emotion analysis",
            instructions="Analyze both the sentiment polarity and emotional content of the text.",
            example_data={"text": "I'm so excited about this new opportunity!"}
        )
        
        # Question Answering
        configs["qa"] = LabelConfig(
            name="Question Answering",
            annotation_type=AnnotationType.QUESTION_ANSWERING,
            config_xml="""
            <View>
              <Header value="Answer questions based on the context"/>
              <Text name="context" value="$context"/>
              <Text name="question" value="$question"/>
              <TextArea name="answer" toName="context" 
                       placeholder="Provide the answer based on the context..."
                       maxSubmissions="1" rows="3"/>
              <Choices name="answerable" toName="context" choice="single-radio">
                <Choice value="answerable"/>
                <Choice value="not_answerable"/>
              </Choices>
            </View>
            """,
            description="Question answering based on provided context",
            instructions="Read the context and answer the question. Mark as not answerable if the context doesn't contain the answer.",
            example_data={
                "context": "The company was founded in 1995 by two college students.",
                "question": "When was the company founded?"
            }
        )
        
        # Image Classification
        configs["image_classification"] = LabelConfig(
            name="Image Classification",
            annotation_type=AnnotationType.IMAGE_CLASSIFICATION,
            config_xml="""
            <View>
              <Header value="Classify the image"/>
              <Image name="image" value="$image"/>
              <Choices name="category" toName="image" choice="single-radio">
                <Choice value="cat"/>
                <Choice value="dog"/>
                <Choice value="bird"/>
                <Choice value="other"/>
              </Choices>
            </View>
            """,
            description="Basic image classification",
            instructions="Look at the image and select the appropriate category.",
            example_data={"image": "/static/sample_image.jpg"}
        )
        
        # Object Detection
        configs["object_detection"] = LabelConfig(
            name="Object Detection",
            annotation_type=AnnotationType.OBJECT_DETECTION,
            config_xml="""
            <View>
              <Header value="Draw bounding boxes around objects"/>
              <Image name="image" value="$image"/>
              <RectangleLabels name="label" toName="image">
                <Label value="person" background="red"/>
                <Label value="car" background="blue"/>
                <Label value="bicycle" background="green"/>
                <Label value="traffic_light" background="yellow"/>
              </RectangleLabels>
            </View>
            """,
            description="Object detection with bounding boxes",
            instructions="Draw bounding boxes around objects in the image and label them.",
            example_data={"image": "/static/sample_street_scene.jpg"}
        )
        
        return configs
    
    def get_config_template(self, annotation_type: AnnotationType) -> Optional[LabelConfig]:
        """Get configuration template for annotation type."""
        return self.default_configs.get(annotation_type.value)
    
    def get_all_templates(self) -> List[LabelConfig]:
        """Get all available configuration templates."""
        return list(self.default_configs.values())
    
    def create_custom_config(self, tenant_id: str, config: LabelConfig) -> bool:
        """Create a custom configuration for a tenant."""
        
        try:
            # Store custom configuration (this would typically go to database)
            # For now, we'll add it to the configs with tenant prefix
            config_key = f"{tenant_id}_{config.name.lower().replace(' ', '_')}"
            self.default_configs[config_key] = config
            
            logger.info(f"Created custom config {config.name} for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create custom config: {e}")
            return False
    
    def get_tenant_configs(self, tenant_id: str) -> List[LabelConfig]:
        """Get all configurations available to a tenant."""
        
        configs = []
        
        # Add default configs
        configs.extend(self.default_configs.values())
        
        # Add tenant-specific configs
        tenant_prefix = f"{tenant_id}_"
        for key, config in self.default_configs.items():
            if key.startswith(tenant_prefix):
                configs.append(config)
        
        return configs
    
    def generate_project_config(self, annotation_type: AnnotationType, 
                               custom_labels: List[str] = None,
                               custom_instructions: str = None) -> Optional[str]:
        """Generate Label Studio configuration XML for a project."""
        
        base_config = self.get_config_template(annotation_type)
        if not base_config:
            return None
        
        config_xml = base_config.config_xml
        
        # Customize labels if provided
        if custom_labels and annotation_type in [
            AnnotationType.TEXT_CLASSIFICATION, 
            AnnotationType.SENTIMENT_ANALYSIS
        ]:
            # Replace choice values with custom labels
            choices_section = ""
            for label in custom_labels:
                choices_section += f'    <Choice value="{label}"/>\n'
            
            # This is a simplified replacement - in practice, you'd use XML parsing
            config_xml = config_xml.replace(
                '<Choice value="positive"/>\n                <Choice value="negative"/>\n                <Choice value="neutral"/>',
                choices_section.strip()
            )
        
        return config_xml
    
    def validate_config(self, config_xml: str) -> Dict[str, Any]:
        """Validate Label Studio configuration XML."""
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Basic XML validation
            import xml.etree.ElementTree as ET
            ET.fromstring(config_xml)
            
            # Check for required elements
            if "<View>" not in config_xml:
                validation_result["errors"].append("Missing <View> root element")
                validation_result["valid"] = False
            
            # Check for common issues
            if "toName=" not in config_xml:
                validation_result["warnings"].append("No toName attributes found - annotations may not work properly")
            
            if "name=" not in config_xml:
                validation_result["warnings"].append("No name attributes found - controls may not be accessible")
            
        except ET.ParseError as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"XML parsing error: {str(e)}")
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def get_config_for_data_type(self, data_sample: Dict[str, Any]) -> Optional[LabelConfig]:
        """Suggest configuration based on data sample."""
        
        # Analyze data sample to suggest appropriate configuration
        if "text" in data_sample:
            if len(data_sample["text"]) > 1000:
                return self.get_config_template(AnnotationType.TEXT_SUMMARIZATION)
            else:
                return self.get_config_template(AnnotationType.TEXT_CLASSIFICATION)
        
        elif "image" in data_sample:
            return self.get_config_template(AnnotationType.IMAGE_CLASSIFICATION)
        
        elif "audio" in data_sample:
            return self.get_config_template(AnnotationType.AUDIO_TRANSCRIPTION)
        
        elif "context" in data_sample and "question" in data_sample:
            return self.get_config_template(AnnotationType.QUESTION_ANSWERING)
        
        return None
    
    def export_tenant_configs(self, tenant_id: str) -> Dict[str, Any]:
        """Export all configurations for a tenant."""
        
        configs = self.get_tenant_configs(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "export_timestamp": "2026-01-08T12:00:00Z",
            "configs": [config.to_dict() for config in configs]
        }
    
    def import_tenant_configs(self, tenant_id: str, config_data: Dict[str, Any]) -> bool:
        """Import configurations for a tenant."""
        
        try:
            configs = config_data.get("configs", [])
            
            for config_dict in configs:
                config = LabelConfig(
                    name=config_dict["name"],
                    annotation_type=AnnotationType(config_dict["annotation_type"]),
                    config_xml=config_dict["config_xml"],
                    description=config_dict["description"],
                    instructions=config_dict["instructions"],
                    example_data=config_dict["example_data"]
                )
                
                self.create_custom_config(tenant_id, config)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to import configs: {e}")
            return False


class TenantProjectTemplate:
    """Template for creating tenant-specific Label Studio projects."""
    
    def __init__(self, config_manager: LabelStudioConfigManager):
        self.config_manager = config_manager
    
    def create_project_from_template(self, tenant_id: str, template_name: str,
                                   project_title: str, data_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a Label Studio project from a template."""
        
        try:
            # Get configuration template
            config = None
            for template_config in self.config_manager.get_tenant_configs(tenant_id):
                if template_config.name.lower().replace(' ', '_') == template_name:
                    config = template_config
                    break
            
            if not config:
                raise Exception(f"Template {template_name} not found")
            
            # Prepare project data
            project_data = {
                "title": project_title,
                "description": f"Project created from {config.name} template",
                "label_config": config.config_xml,
                "is_published": False,
                "maximum_annotations": 1,
                "show_instruction": True,
                "show_skip_button": True,
                "enable_empty_annotation": True,
                "instruction": config.instructions
            }
            
            # Add sample data if provided
            if data_samples:
                project_data["tasks"] = data_samples
            
            return project_data
            
        except Exception as e:
            logger.error(f"Failed to create project from template: {e}")
            return {}
    
    def get_available_templates(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get available project templates for a tenant."""
        
        configs = self.config_manager.get_tenant_configs(tenant_id)
        
        templates = []
        for config in configs:
            templates.append({
                "name": config.name.lower().replace(' ', '_'),
                "display_name": config.name,
                "annotation_type": config.annotation_type.value,
                "description": config.description,
                "example_data": config.example_data
            })
        
        return templates


# Global instances
config_manager = LabelStudioConfigManager()
project_template = TenantProjectTemplate(config_manager)


def get_config_manager() -> LabelStudioConfigManager:
    """Get the global configuration manager."""
    return config_manager


def get_project_template() -> TenantProjectTemplate:
    """Get the global project template manager."""
    return project_template