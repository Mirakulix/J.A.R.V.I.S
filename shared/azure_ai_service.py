"""
Azure AI Service Integration for JARVIS
Handles AI-powered idea processing and enhancement
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import aiohttp
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class IdeaEnhancement:
    """Data class for AI-enhanced idea information"""
    title: str
    bullet_points: List[str]
    detailed_concept: str
    optimized_prompt: str
    category: str
    complexity: int
    tags: List[str]
    requirements_notes: str

class AzureAIService:
    """Azure AI service for processing and enhancing user-submitted ideas"""
    
    def __init__(self):
        self.api_key = self._load_azure_api_key()
        self.endpoint = os.getenv('AZURE_AI_ENDPOINT', 'https://jarvis-ai.openai.azure.com/')
        self.api_version = os.getenv('AZURE_AI_API_VERSION', '2024-02-15-preview')
        self.deployment_name = os.getenv('AZURE_AI_DEPLOYMENT', 'gpt-4')
        self.session = None
        
    def _load_azure_api_key(self) -> str:
        """Load Azure AI API key from environment variable"""
        try:
            # Use environment variable directly
            return os.getenv('AZURE_AI_API_KEY', '')
        except Exception as e:
            logger.error(f"Failed to load Azure AI API key: {e}")
            return ''
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def process_idea(self, original_prompt: str, user_context: Optional[str] = None) -> IdeaEnhancement:
        """
        Process a user idea and generate enhanced information using Azure AI
        
        Args:
            original_prompt: The original user-submitted idea
            user_context: Optional context about the user or system
            
        Returns:
            IdeaEnhancement object with AI-generated content
        """
        try:
            # Create the system prompt for idea enhancement
            system_prompt = self._create_system_prompt()
            
            # Create the user prompt with the idea
            user_prompt = self._create_user_prompt(original_prompt, user_context)
            
            # Make the API call to Azure AI
            response = await self._call_azure_ai(system_prompt, user_prompt)
            
            # Parse and validate the response
            enhancement = self._parse_ai_response(response)
            
            logger.info(f"Successfully processed idea: {enhancement.title}")
            return enhancement
            
        except Exception as e:
            logger.error(f"Failed to process idea: {e}")
            # Return a basic enhancement as fallback
            return self._create_fallback_enhancement(original_prompt)
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for Azure AI"""
        return """You are an expert AI system designer and software architect for JARVIS, a sophisticated multi-container AI development environment. Your task is to analyze user-submitted ideas for new capabilities or features and enhance them with detailed specifications.

For each idea, you must generate:
1. A compelling, clear title (max 100 characters)
2. Three bullet points describing the feature for a preview tile (each max 80 characters)
3. A detailed concept document with technical specifications
4. An optimized prompt for Claude Code to implement the feature
5. Categorization, complexity assessment, and implementation guidance

Focus on:
- Technical feasibility within the JARVIS architecture
- Integration with existing microservices (core, functions, test, code, monitor, android)
- Security and performance considerations
- User experience and practical value
- Clear implementation steps

The JARVIS system uses:
- Docker microservices architecture
- PostgreSQL databases (persons, organization, medical, trading)
- ChromaDB for vector embeddings
- Redis for caching
- AutoGen for multi-agent AI workflows
- Claude Code integration
- Android automation capabilities
- Prometheus monitoring

Respond in valid JSON format with the specified structure."""

    def _create_user_prompt(self, original_prompt: str, user_context: Optional[str] = None) -> str:
        """Create the user prompt with the idea"""
        context_info = f"\nUser context: {user_context}" if user_context else ""
        
        return f"""Please analyze and enhance this idea for a new JARVIS capability:

Original idea: {original_prompt}{context_info}

Generate a JSON response with this exact structure:
{{
    "title": "Clear, compelling title for the feature",
    "bullet_points": [
        "First benefit/feature description",
        "Second key capability", 
        "Third advantage or use case"
    ],
    "detailed_concept": "Comprehensive technical specification including architecture, implementation approach, integration points, security considerations, and user workflow. Should be detailed enough for a senior developer to understand the full scope.",
    "optimized_prompt": "A carefully crafted prompt for Claude Code that includes: specific technical requirements, architectural constraints, integration points, security requirements, testing approach, and step-by-step implementation guidance. This prompt should enable Claude Code to implement the feature effectively.",
    "category": "Primary category (automation|ai|integration|ui|security|data|monitoring|testing|android|development)",
    "complexity": 1-5,
    "tags": ["relevant", "searchable", "tags"],
    "requirements_notes": "Key requirements, dependencies, and constraints for implementation"
}}

Ensure the response is valid JSON and follows JARVIS system architecture principles."""

    async def _call_azure_ai(self, system_prompt: str, user_prompt: str) -> Dict:
        """Make API call to Azure AI"""
        if not self.api_key:
            raise ValueError("Azure AI API key not configured")
        
        url = f"{self.endpoint}openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': self.api_key
        }
        
        payload = {
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'max_tokens': 2000,
            'temperature': 0.7,
            'top_p': 0.9,
            'frequency_penalty': 0.1,
            'presence_penalty': 0.1
        }
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        async with self.session.post(url, headers=headers, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Azure AI API error {response.status}: {error_text}")
            
            result = await response.json()
            return result
    
    def _parse_ai_response(self, response: Dict) -> IdeaEnhancement:
        """Parse Azure AI response and create IdeaEnhancement object"""
        try:
            content = response['choices'][0]['message']['content']
            
            # Extract JSON from the response (handle potential markdown formatting)
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in AI response")
            
            json_content = content[json_start:json_end]
            parsed = json.loads(json_content)
            
            # Validate required fields
            required_fields = ['title', 'bullet_points', 'detailed_concept', 'optimized_prompt']
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure bullet_points has exactly 3 items
            bullet_points = parsed['bullet_points']
            if len(bullet_points) != 3:
                # Pad or trim to exactly 3 items
                bullet_points = (bullet_points + ['', '', ''])[:3]
            
            return IdeaEnhancement(
                title=parsed['title'][:500],  # Ensure max length
                bullet_points=bullet_points,
                detailed_concept=parsed['detailed_concept'],
                optimized_prompt=parsed['optimized_prompt'],
                category=parsed.get('category', 'development'),
                complexity=max(1, min(5, parsed.get('complexity', 3))),  # Ensure 1-5 range
                tags=parsed.get('tags', []),
                requirements_notes=parsed.get('requirements_notes', '')
            )
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise ValueError(f"Invalid AI response format: {e}")
    
    def _create_fallback_enhancement(self, original_prompt: str) -> IdeaEnhancement:
        """Create a basic enhancement when AI processing fails"""
        return IdeaEnhancement(
            title=f"New Feature: {original_prompt[:50]}...",
            bullet_points=[
                "User-submitted feature request",
                "Requires manual review and planning",
                "AI processing temporarily unavailable"
            ],
            detailed_concept=f"Original user idea: {original_prompt}\n\nThis idea requires manual review and enhancement as automatic AI processing was not available.",
            optimized_prompt=f"Please implement this user-requested feature for JARVIS: {original_prompt}\n\nConsider the JARVIS microservices architecture and ensure proper integration with existing services.",
            category="development",
            complexity=3,
            tags=["user-request", "manual-review"],
            requirements_notes="Requires manual analysis and specification"
        )

# Utility functions for easy integration
async def process_idea_with_azure_ai(original_prompt: str, user_context: Optional[str] = None) -> IdeaEnhancement:
    """Convenience function to process an idea with Azure AI"""
    async with AzureAIService() as ai_service:
        return await ai_service.process_idea(original_prompt, user_context)

def validate_azure_ai_config() -> bool:
    """Check if Azure AI is properly configured"""
    try:
        service = AzureAIService()
        return bool(service.api_key and service.endpoint)
    except Exception:
        return False