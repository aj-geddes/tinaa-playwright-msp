# TINAA Enhanced Architecture Design

## Overview

This document outlines the enhanced architecture for TINAA, transforming it from a basic testing tool into a comprehensive AI-powered testing platform with workspace management, project orchestration, and intelligent guidance.

## Current State Analysis

### Existing Components
- **FastAPI HTTP Server**: REST API with WebSocket support
- **FastMCP Integration**: Playwright automation via MCP protocol
- **Progress Tracking**: Real-time test execution monitoring
- **Basic Playbook System**: Sequential test step execution
- **Playwright Controller**: Browser automation engine

### Current Limitations
- No user interface
- Basic workspace functionality
- No project management
- No AI integration for guidance
- Limited repository management
- No LLM-powered troubleshooting

## Enhanced Architecture Components

### 1. Frontend Architecture

#### Technology Stack
- **Framework**: React with TypeScript
- **State Management**: Zustand for lightweight state management
- **UI Components**: Shadcn/ui + Tailwind CSS
- **Real-time**: WebSocket integration for live updates
- **Build Tool**: Vite for fast development

#### Core Frontend Features
```typescript
// Core UI Components
- Dashboard: Activity overview, workspace status
- Workspace Manager: Project list, repository management
- Test Runner: Interactive test execution with live progress
- Playbook Builder: Visual test sequence designer
- AI Assistant: Chat interface for guidance and troubleshooting
- Settings: AI provider configuration, preferences
```

#### Component Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard/
│   │   ├── WorkspaceManager/
│   │   ├── TestRunner/
│   │   ├── PlaybookBuilder/
│   │   ├── AIAssistant/
│   │   └── Settings/
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useWorkspace.ts
│   │   └── useAIAssistant.ts
│   ├── store/
│   │   ├── workspaceStore.ts
│   │   ├── testingStore.ts
│   │   └── aiStore.ts
│   └── types/
│       ├── workspace.ts
│       ├── testing.ts
│       └── ai.ts
```

### 2. Enhanced Workspace Management

#### Workspace Structure
```
/mnt/workspace/
├── projects/
│   ├── <project-id>/
│   │   ├── .tinaa/
│   │   │   ├── config.json
│   │   │   ├── playbooks/
│   │   │   ├── reports/
│   │   │   └── ai-context.json
│   │   ├── src/
│   │   ├── tests/
│   │   ├── package.json
│   │   └── playwright.config.ts
├── templates/
│   ├── basic-web-testing/
│   ├── e2e-workflow/
│   └── api-testing/
└── shared/
    ├── utilities/
    ├── fixtures/
    └── resources/
```

#### Project Management Features
- **Repository Cloning**: Git integration for project initialization
- **Template System**: Predefined project structures
- **Configuration Management**: Per-project TINAA settings
- **Artifact Storage**: Screenshots, reports, traces
- **Version Control**: Integration with Git workflows

### 3. AI Integration Architecture

#### AI Provider Support
```python
# Supported AI Providers
providers = {
    "openai": {
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "capabilities": ["chat", "code-generation", "analysis"]
    },
    "anthropic": {
        "models": ["claude-3-sonnet", "claude-3-haiku"],
        "capabilities": ["chat", "code-generation", "analysis"]
    },
    "local": {
        "models": ["ollama/*"],
        "capabilities": ["chat", "code-generation"]
    }
}
```

#### MCP Server Transformation
```python
# TINAA as MCP Server
class TinaaServerMCP:
    """TINAA MCP Server providing testing tools to AI clients"""
    
    tools = [
        "create_project",
        "clone_repository", 
        "generate_playbook",
        "execute_tests",
        "analyze_results",
        "troubleshoot_issues",
        "optimize_tests"
    ]
    
    resources = [
        "workspace://projects",
        "templates://testing-patterns",
        "docs://best-practices"
    ]
```

### 4. Backend API Enhancements

#### New API Endpoints
```python
# Workspace Management
POST /api/workspace/projects              # Create new project
GET  /api/workspace/projects              # List projects
POST /api/workspace/projects/{id}/clone   # Clone repository
DELETE /api/workspace/projects/{id}       # Delete project

# AI Integration
POST /api/ai/chat                        # AI chat interface
POST /api/ai/generate-playbook           # Generate test playbook
POST /api/ai/analyze-project             # Project analysis
POST /api/ai/troubleshoot               # Troubleshooting assistance

# Enhanced Testing
POST /api/tests/guided-execution        # AI-guided test execution
GET  /api/tests/recommendations         # Test improvement suggestions
POST /api/tests/auto-generate           # Auto-generate tests from URL

# Project Management
GET  /api/projects/{id}/status          # Project health status
POST /api/projects/{id}/setup           # Initialize project structure
GET  /api/projects/{id}/insights        # AI-powered insights
```

### 5. Database Schema

#### Project & Workspace Tables
```sql
-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    repository_url VARCHAR(500),
    workspace_path VARCHAR(500),
    ai_context JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Test Sessions table  
CREATE TABLE test_sessions (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    playbook_id UUID,
    status VARCHAR(50),
    results JSONB,
    ai_insights JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI Interactions table
CREATE TABLE ai_interactions (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    interaction_type VARCHAR(100),
    input_data JSONB,
    output_data JSONB,
    provider VARCHAR(50),
    model VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 6. AI-Powered Features

#### Intelligent Playbook Generation
```python
class PlaybookGenerator:
    """AI-powered test playbook generation"""
    
    async def generate_from_url(self, url: str) -> Playbook:
        """Generate playbook by analyzing a URL"""
        
    async def generate_from_repository(self, repo_path: str) -> Playbook:
        """Generate playbook from repository analysis"""
        
    async def enhance_existing(self, playbook: Playbook) -> Playbook:
        """Enhance existing playbook with AI suggestions"""
```

#### Project Troubleshooting
```python
class AITroubleshooter:
    """AI-powered project troubleshooting"""
    
    async def diagnose_test_failures(self, session_id: str) -> DiagnosisReport:
        """Analyze test failures and provide solutions"""
        
    async def optimize_performance(self, project_id: str) -> OptimizationPlan:
        """Suggest performance improvements"""
        
    async def suggest_test_coverage(self, project_id: str) -> CoverageReport:
        """Analyze and suggest test coverage improvements"""
```

## Implementation Phases

### Phase 1: Enhanced Workspace & PVC
1. Update Helm chart for larger PVC (50GB+)
2. Implement workspace structure
3. Add project management API endpoints
4. Create repository cloning functionality

### Phase 2: Frontend Development
1. Set up React application with Vite
2. Implement core UI components
3. Add WebSocket integration
4. Create workspace management interface

### Phase 3: AI Integration
1. Add AI provider libraries to requirements
2. Implement MCP server functionality
3. Create AI chat interface
4. Add playbook generation capabilities

### Phase 4: Advanced Features
1. Implement troubleshooting system
2. Add performance optimization
3. Create guided testing workflows
4. Enhance reporting with AI insights

## Security Considerations

### API Security
- JWT authentication for frontend
- Rate limiting for AI endpoints
- Secure API key storage for AI providers
- RBAC for workspace access

### Workspace Security
- Isolated project environments
- Secure git credential management
- File access controls
- Container security policies

### AI Security
- Input sanitization for AI prompts
- Output validation and filtering
- API key encryption and rotation
- Usage monitoring and quotas

## Deployment Architecture

### Kubernetes Resources
```yaml
# Enhanced PVC for workspace
spec:
  capacity:
    storage: 100Gi  # Increased from 10Gi
  accessModes:
    - ReadWriteOnce
    
# Additional services
- tinaa-frontend (React app)
- tinaa-backend (Enhanced FastAPI)
- tinaa-ai-proxy (AI provider gateway)
- tinaa-db (PostgreSQL for metadata)
```

### Docker Compose for Development
```yaml
services:
  tinaa-backend:
    build: .
    volumes:
      - ./workspace:/mnt/workspace
      - ./ai-cache:/app/ai-cache
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      
  tinaa-frontend:
    build: ./frontend
    ports:
      - "3000:3000"
      
  tinaa-db:
    image: postgres:15
    environment:
      - POSTGRES_DB=tinaa
      - POSTGRES_USER=tinaa
      - POSTGRES_PASSWORD=tinaa_dev
```

## Success Metrics

### User Experience
- Project setup time < 2 minutes
- AI response time < 3 seconds
- Test execution visibility with real-time updates
- Intuitive playbook builder interface

### AI Integration
- Playbook generation accuracy > 85%
- Troubleshooting success rate > 70%
- User satisfaction with AI guidance > 4.0/5.0

### Performance
- Workspace operations < 1 second
- Concurrent project support: 10+
- Frontend bundle size < 2MB
- WebSocket latency < 100ms

This enhanced architecture transforms TINAA into a comprehensive, AI-powered testing platform that guides users through intelligent test creation, execution, and optimization while maintaining the robust Playwright automation core.