# Chispart AI - Blackbox Hybrid Tool

## Project Overview

Chispart AI is a multi-agent AI platform for content creation with a glassmorphism interface and collaborative workflows, powered by Blackbox AI. The project provides a FastAPI-based REST API for integrating with various AI models from Blackbox, with support for dynamic model selection via identifiers (e.g., `blackboxai/openai/o1`).

## Recent Improvements

The project has been enhanced with several key improvements:

### 1. Enhanced Error Handling
- Unified exception hierarchy in `blackbox_hybrid_tool/exceptions.py`
- Consistent HTTP error responses
- Specific exception types for common error conditions

### 2. Improved Configuration Management
- Pydantic-based settings in `blackbox_hybrid_tool/config/settings.py`
- Type-safe configuration with environment variable support
- Backward compatibility with existing .env files

### 3. Better Dependency Management
- Synced requirements.txt with setup.py dependencies
- Added pydantic-settings for configuration management

## Project Structure

```
blackbox-hybrid-tool/
├── main.py                    # Main FastAPI server
├── blackbox_hybrid_tool/      # Main Python package
│   ├── cli/                   # Command-line interface
│   │   ├── main.py            # Main CLI entry point
│   │   └── media.py           # Media generation commands
│   ├── core/                  # Core functionality
│   │   ├── ai_client.py       # AI client and orchestrator
│   │   └── test_generator.py  # Automated test generation
│   ├── config/                # Configuration files
│   │   └── models.json        # AI model configuration
│   └── utils/                 # Utility modules
│       ├── patcher.py         # Unified diff patch applier
│       ├── self_repo.py       # Self-repo analysis and management
│       ├── github_client.py   # GitHub integration
│       ├── web.py             # Web search and fetch utilities
│       ├── ssh.py             # SSH utilities
│       ├── profiles.py        # Media profile management
│       └── image.py           # Image processing utilities
├── tests/                     # Test files
├── static/                    # Static files (playground UI)
├── frontend/                  # Frontend files (main UI)
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Docker Compose configuration
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
├── pyproject.toml             # Project configuration
├── .dockerignore             # Docker ignore patterns
├── .env.example              # Example environment variables
├── README.md                 # Project documentation
└── LICENSE                   # License information
```

## Key Components

### 1. FastAPI Server (main.py)
- REST API with endpoints for chat, model management, file operations, and patch application
- Automatic documentation with Swagger UI at `/docs` and ReDoc at `/redoc`
- Built-in playground UI at `/playground`
- Support for CORS, health checks, and logging

### 2. AI Client and Orchestrator (blackbox_hybrid_tool/core/ai_client.py)
- Integration with Blackbox AI API
- Dynamic model selection via identifiers
- Support for multiple AI models with configuration management
- Function calling/tool usage capabilities

### 3. Command-Line Interface (blackbox_hybrid_tool/cli/main.py)
- Generate tests automatically for source files
- Analyze code coverage
- Query AI models directly
- Interactive REPL with session persistence
- File operations (create/write, apply patches)
- Media generation (images, videos)
- Web search and fetch capabilities
- GitHub integration (create Gists)
- Self-analysis and evolution tools
- Remote deployment via SSH

### 4. Configuration (blackbox_hybrid_tool/config/models.json)
- Model configuration with default settings
- Available models catalog with pricing information
- Support for importing models from CSV

### 5. Utilities
- Patch applier for unified diff files
- Self-repo analysis and management
- GitHub client for basic operations
- Web search and fetch tools
- SSH utilities for remote operations
- Media profile management
- Image processing utilities

## Installation and Deployment

### Using Docker Compose (Recommended)
```bash
# 1. Navigate to project directory
cd blackbox-hybrid-tool

# 2. Configure environment variables
# Create .env file with at least BLACKBOX_API_KEY
BLACKBOX_API_KEY=your_blackbox_api_key

# 3. Build and run container
docker-compose up --build

# 4. Verify application is running
curl http://localhost:8000/health
```

### Local Development
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment variables (same as above)

# 3. Run application
python main.py

# Or for development with hot reload
docker-compose --profile dev up --build
```

## API Usage

### Basic Endpoints
- `GET /` - Basic API information
- `GET /health` - Health check
- `GET /models` - List available models
- `POST /models/switch` - Switch default model
- `POST /chat` - Generate AI response
- `POST /files/write` - Create/write text files
- `POST /patch/apply` - Apply unified diff patches
- `GET /playground` - Minimal chat interface
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

### Chat Endpoint
```bash
# Simple chat with default model
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "What is the capital of France?"
     }'

# Chat with specific Blackbox model
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "Explain the theory of relativity",
       "model_type": "blackboxai/openai/o1",
       "max_tokens": 500,
       "temperature": 0.3
     }'
```

## CLI Usage

### Installation
```bash
pip install -e .
```

### Common Commands
```bash
# Show help
blackbox-tool --help

# Query AI with default model
blackbox-tool ai-query "Explain TDD briefly"

# Query AI with specific model
blackbox-tool ai-query "Summarize SOLID" -m blackboxai/openai/o1

# Generate tests for a file
blackbox-tool generate-tests src/main.py

# Analyze code coverage
blackbox-tool analyze-coverage tests/

# List available models
blackbox-tool list-models

# View current configuration
blackbox-tool config

# Switch default model
blackbox-tool switch-model blackboxai/anthropic/claude-3.7-sonnet

# Interactive REPL
blackbox-tool repl

# Create/write files
blackbox-tool write-file docs/note.txt -c "Hello world"

# Apply patches
blackbox-tool apply-patch -f changes.patch

# Web search
blackbox-tool web-search -q "pytest best practices" -n 3

# Web fetch
blackbox-tool web-fetch https://docs.pytest.org/

# GitHub integration
blackbox-tool gh-status
blackbox-tool gh-create-gist -f README.md -n README.md -d "Copy of README" --public

# Self-analysis tools
blackbox-tool self-snapshot
blackbox-tool self-extract -o .self_extract
blackbox-tool self-analyze --from current
blackbox-tool self-test
blackbox-tool self-apply-patch -f changes.patch

# AI-assisted development
blackbox-tool ai-dev "Add 'hello' command to CLI" --out-dir patches
blackbox-tool ai-dev "Refactor ai_client for retries" -s reasoning
blackbox-tool ai-dev "Create /metrics endpoint" -m blackboxai/openai/o1 --apply
```

## Development

### Running Tests
```bash
python -m pytest
```

### Environment Variables
- `BLACKBOX_API_KEY` - Blackbox AI API key (required)
- `CONFIG_FILE` - Path to models configuration file
- `BLACKBOX_MODELS_CSV` - Path to CSV file with available models
- `SERPAPI_KEY` - SerpAPI key for web search (optional)
- `TAVILY_API_KEY` - Tavily API key for web search (optional)
- `GH_TOKEN` - GitHub personal access token (optional)

## Monitoring and Logs

### Health Check
```bash
curl http://localhost:8000/health
```

### View Logs
```bash
# Docker container logs
docker-compose logs -f blackbox-hybrid-tool

# Application logs (inside container)
docker-compose logs -f | grep "blackbox"
```

## Troubleshooting

### AI Model Connection Errors
- Verify API keys are correctly configured in `.env`
- Ensure container has internet access
- Check logs for specific error messages

### API 500 Errors
- Check container logs for details
- Verify model configuration in `models.json`
- Ensure all required models are enabled

### Docker Issues
- Ensure Docker is running
- Clean old images/containers: `docker system prune -a`
- Verify ports 8000/8001 are available