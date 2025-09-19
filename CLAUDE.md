# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a J.A.R.V.I.S. AI assistant project built in Python, combining multiple frameworks:
- **ChatGPT Plugin**: Basic todo list plugin using Quart framework (main.py)
- **AutoGen Multi-Agent System**: Advanced AI agent orchestration for complex tasks
- **Core Jarvis Module**: Event-driven architecture with context management
- **Machine Learning Stack**: TensorFlow, PyTorch, Transformers, and HuggingFace integration
- **OpenAI Integration**: GPT-4, vision, speech-to-text, text-to-speech capabilities

## Development Commands

**Install Dependencies:**
```bash
pip install -r requirements.txt
```

**Run ChatGPT Plugin Server:**
```bash
python main.py
```
Starts Quart server on localhost:5003 for ChatGPT plugin development.

**Run AutoGen Multi-Agent System:**
```bash
python autogen_flo.py
```
Launches multi-agent conversation system with Engineer, Developer, Scientist, Planner, and Critic agents.

**Run Core Jarvis Module Tests:**
```bash
python -m jarvis.core.event_bus
python -m jarvis.core.context_manager
python -m jarvis.speech.speech_processor
python -m jarvis.vision.vision_processor
```

**Basic AutoGen Test:**
```bash
python autogen/app.py
```

**Development Notes:**
- No formal test suite configured - testing done through individual script execution
- No build/lint configuration found - development uses standard Python practices
- API keys managed via environment variables (OPENAI_API_KEY) or .env file
- Project documentation includes feature prioritization framework and implementation roadmap in `docs/`

## Architecture

### Core Components

**ChatGPT Plugin (main.py)**
- Quart-based web server with CORS for chat.openai.com
- RESTful API for todo management (/todos/<username>)
- OpenAPI specification in openapi.yaml
- Plugin manifest at /.well-known/ai-plugin.json

**AutoGen System (autogen_flo.py)**
- Multi-agent orchestration using Microsoft AutoGen
- Specialized agents: Engineer, Developer, Scientist, Planner, Executor, Critic
- Group chat manager for coordinated problem-solving
- Configurable LLM models (GPT-4, GPT-3.5-turbo variants)

**Configuration**
- OpenAI API keys managed via environment variables (OPENAI_API_KEY) or .env file
- Model configurations in OAI_CONFIG_LIST and autogen_flo.py
- Support for multiple GPT model variants (gpt-4-1106-preview, gpt-4-vision-preview, gpt-3.5-turbo variants)
- AutoGen agents configured with approval workflows and code execution capabilities

**Core Jarvis Module (jarvis/)**
- Event-driven architecture with centralized EventBus (jarvis/core/event_bus.py)
- Context management for conversations and user sessions (jarvis/core/context_manager.py)
- Speech processing with OpenAI Whisper integration (jarvis/speech/speech_processor.py)
- Vision processing with GPT-4 Vision API (jarvis/vision/vision_processor.py)
- Modular design with clear separation of concerns

### Directory Structure

- `jarvis/` - Core J.A.R.V.I.S. modules with event-driven architecture
  - `core/` - Event bus and context management systems
  - `speech/` - Speech-to-text and text-to-speech processing
  - `vision/` - Image and video processing capabilities
- `autogen/` - AutoGen framework components
- `docs/` - Project documentation including feature prioritization and roadmaps
- `ai-models/` - HuggingFace and Ollama model configurations
- `backup-data/` - Research data and resources
- `gpt-code-assistant/` - Setup scripts and documentation

## Key Dependencies

**Core Frameworks:**
- `autogen` - Multi-agent conversational AI
- `quart` + `quart-cors` - Async web framework
- `openai` - OpenAI API client
- `flask` - Alternative web framework

**ML/AI Stack:**
- `tensorflow`, `torch` - Deep learning frameworks
- `transformers`, `huggingface-hub` - NLP models
- `langchain` + `langchain-openai` - LLM application framework
- `crewai` - AI crew coordination

**Data/Utilities:**
- `pandas`, `numpy` - Data processing
- `requests`, `aiohttp` - HTTP clients
- `redis`, `sqlalchemy` - Data persistence

## Core Architecture Patterns

**Event-Driven Communication**
- All system modules communicate through the central EventBus (jarvis/core/event_bus.py)
- Events have priorities (CRITICAL, HIGH, NORMAL, LOW) and correlation IDs for tracing
- Asynchronous processing with error handling and retry mechanisms

**Context Management**
- Multi-scope context system: SESSION, USER, GLOBAL, TASK (jarvis/core/context_manager.py)
- Automatic context expiration and cleanup
- Conversation history and user preference storage

**Agent Orchestration**
- AutoGen multi-agent system with 6 specialized roles
- Approval workflow: Admin → Planner → Engineer/Developer → Critic → Executor
- Code execution in isolated sandbox environments

## Important Notes

- **Language**: The project mixes German and English in prompts and documentation
- **Security**: API keys should be set via environment variables, never hardcoded
- **ChatGPT Plugin**: Designed for local development and testing with OpenAI ChatGPT plugins
- **AutoGen Agent Flow**: Users interact with Admin agent who must approve plans before Engineer/Developer execution
- **Code Execution**: AutoGen agents can execute code in isolated work directories ("paper", "web")
- **Multi-Agent Coordination**: Planner designs tasks, Engineer/Developer write code, Scientist analyzes, Critic reviews, Executor runs code
- **Event System**: Use the EventBus for inter-module communication rather than direct imports
- **Context Persistence**: Leverage ContextManager for maintaining state across conversations