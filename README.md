# Gravel

**Gravel is an AI coding assistant that actually respects your privacy.**

If you've ever wanted to use AI to chat with your codebase but couldn't because of strict company policies or fear of leaking proprietary intellectual property, Gravel is built for you.

### How It Works

Before sending *any* code to an external AI model, Gravel acts as a secure local proxy. 

It parses your code locally and uses Abstract Syntax Tree (AST) masking to strip out all your sensitive IP—such as proprietary function names, variables, and internal business logic. It replaces these with secure cryptographic tokens. 

The AI receives a completely anonymized "skeleton" of your code. This gives the model enough structural context to answer your questions, explain concepts, or find bugs, but the payload itself is completely useless to anyone trying to reverse-engineer your application. When the AI responds, Gravel decodes the tokens and translates the response back into your original code locally on your machine.

### Core Features

Beyond just privacy, Gravel is designed to help developers navigate and understand large, complex codebases:

- **Intelligent Semantic Search:** Ask questions in plain English (e.g., "Where is the authentication middleware?") and get precisely the right code snippets back.
- **Code Playground:** A built-in, isolated environment to experiment with code changes and see how they might affect the broader system.
- **Bug Radar:** Proactively identify potential vulnerabilities, edge cases, and architectural flaws hidden within your codebase.
- **Onboard Me:** Generate instant, high-level summaries and architectural breakdowns of unfamiliar projects, drastically reducing the time it takes for new engineers to get up to speed.

### Tech Stack

- **Frontend:** Next.js 14 (App Router)
- **Backend:** FastAPI (Python)
- **Database:** SQLite (for local dev) / PostgreSQL (for production)
- **Vector Search:** ChromaDB

### Quick Start

1. Copy `.env.example` to `.env` and fill in your relevant API keys.
2. Spin up the services with Docker: 
   ```bash
   docker compose up --build
   ```
3. The frontend will be available at `http://localhost:3000`.
4. The API documentation will be available at `http://localhost:8000/docs`.
