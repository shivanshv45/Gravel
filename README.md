# Gravel

> **Note: Gravel is currently in active development (Dev Mode).**

## Overview
Gravel is a privacy-first, AI-powered code intelligence platform designed for developers and enterprises. It enables advanced code search, exploration, and natural language querying capabilities over your codebase—without ever leaking proprietary intellectual property.

The core premise of Gravel is to allow you to interact with your codebase using Large Language Models (LLMs) securely. It achieves this by performing local AST (Abstract Syntax Tree) parsing and code anonymization, replacing proprietary identifiers with cryptographic tokens before any code is sent to external LLM providers. 

## Key Features (In Development)
- **Hybrid-Secure Pipeline:** Local anonymization of code before external AI processing.
- **Repository Ingestion:** Scanning and parsing local repositories to extract structural metadata.
- **Semantic Code Search:** Vector-based querying to find relevant code snippets.
- **Privacy Budget Tracking:** Audit logs and tracking for tokens masked and data sent externally.

## Architecture
- **Frontend:** Next.js 14 (App Router)
- **Backend:** FastAPI (Python)
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Vector Store:** ChromaDB
- **Deployment:** Docker & Docker Compose

## Getting Started
1. Copy `.env.example` to `.env` and fill in the necessary API keys.
2. Run `docker compose up --build` to start the services.
3. Access the frontend at `http://localhost:3000` and the API at `http://localhost:8000/docs`.

