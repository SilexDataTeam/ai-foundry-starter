<p align="center" width="100%">
  <img width="33%" src="https://www.silexdata.com/wp-content/uploads/2023/07/SILEX-LOGOS.png"> 
</p>

# Silex AI Foundry Starter

This project is a production-ready starter kit for building and deploying AI applications powered by LangChain/LangGraph — complete with streaming chat, robust authentication, a Kong-based multi-model gateway, and modern cloud-native infrastructure easily deployable on Red Hat OpenShift.

---

<p align="center" width="100%">
  <img src="https://github.com/silexdatateam/ai-foundry-starter/blob/main/docs/architecture.png?raw=true">
</p>

<p align="center" width="100%">
  <img src="https://github.com/silexdatateam/ai-foundry-starter/blob/main/docs/chat.gif?raw=true">
</p>

## Key Features

- **LangChain/LangGraph** for flexible AI agent development  
- Support for **agentic capabilities** including tool calling, database interactions, and API integrations  
- **Streaming chat interface** for real-time AI responses  
- **Document ingestion pipeline** using PGVector for vector embeddings  
- Multiple **RAG patterns** implemented (basic, advanced, agentic approaches)

### Frontend
- **Vite + React** web application with real-time chat interface
- **Server-Sent Events (SSE)** for streaming AI responses
- Responsive design using **Tailwind CSS**
- **Keycloak.js** for authentication
- **Thumbs up/down** feedback system for AI responses

### Backend
- **FastAPI** service with async support  
- **Keycloak** integration for authentication and authorization  
- **Chat history** persistence in PostgreSQL  
- **OpenTelemetry** integration via Traceloop for observability  
- Comprehensive **unit test coverage**

### Infrastructure
- **Kong API Gateway** for:
  - Multi-model LLM support  
  - Request/response logging  
  - API governance  
  - Rate limiting  
- **PostgreSQL** for:
  - Chat history storage  
  - Vector embeddings (pgvector)  
- **Tekton Pipelines** for automated document ingestion  
- **Helm charts** for easy deployment on Kubernetes/OpenShift  
- Automated telemetry setup with **OpenTelemetry** collector and **Jaeger**

---

## Architecture

The system consists of several key components:

1. **Chat Frontend (frontend/)**
2. **Backend API (backend/)**  
3. **Kong AI Gateway (model-gateway/)**  
4. **PostgreSQL Database + PGVector**  
5. **Keycloak Authentication**  
6. **OpenTelemetry Collector**  
7. **Document Ingestion Pipeline**

---

## Contributing

Contributions are welcome via pull requests. We will be publishing a contribution guide in the future.

## Documentation

Documentation is currently in progress and deployment guides will be provided soon.

## Bug Reports/Issues/Assistance

Please report any issues with this project via a GitHub issue. An issue can also be created if you have questions or have suggestions. 

## Feedback

All feedback is appreciated - if you prefer, you may contact us via email at [ai-foundry@silexdata.com](mailto:ai-foundry@silexdata.com).