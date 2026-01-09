<div align="center">

<img src="frontend/static/logo_800.png" alt="JarIt" width="150">
<h1>JarIt!</h1>
</div>

**AI-powered recipe extraction from videos to Mealie**

JarIt is an intelligent application that automatically extracts structured recipes from video content (YouTube, TikTok, Instagram, and more using AI and seamlessly uploads them to your [Mealie](https://mealie.io/) recipe manager.


## Features

- **Multi-Platform Support** - Extract recipes from YouTube, TikTok, Instagram, and 1500+ video platforms via yt-dlp
- **AI-Powered Extraction** - Uses Pydantic AI with support for multiple LLM providers:
  - Google Gemini (default)
  - OpenAI GPT Models
  - Ollama (local models)
- **Audio Transcription** - Automatic video transcription using OpenAI Whisper
- **Smart Recipe Parsing** - Extracts ingredients, instructions, timing, and metadata
- **Multi-Language** - Translate recipes to your preferred language during extraction
- **Recipe Editor** - Review and edit extracted recipes before uploading
- **Mealie Integration** - One-click upload to your Mealie instance
- **Multi-User Support** - User authentication with admin panel
- **Secure** - JWT authentication, encrypted API keys, role-based access
- **Docker Ready** - Complete Docker setup for easy deployment

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Quick Start (Docker)](#quick-start-docker)
- [Configuration](#configuration)
  - [Obtaining Mealie API Key](#obtaining-mealie-api-key)
- [Usage](#usage)
- [Architecture](#architecture)
- [Development](#development)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

- **Docker** & **Docker Compose** 
- **Mealie instance**
- **API Keys** for LLM provider:
  - Google Gemini API key (got the best results so far - free tier available)
  - OR OpenAI API key
  - OR Ollama installed locally
- **OpenAI API key** (required for Whisper audio transcription, if recipe is not in the video description)

## Installation

### Quick Start (Docker Compose)

The fastest way to get started is using Docker:

```bash
# 1. Clone the repository
git clone https://github.com/eFroD/recipeAgent
cd recipe-agent

# 2. Copy and configure environment file
cp .env_example .env
nano .env  # Edit with your API keys

# 3. Start all services (PostgreSQL, Backend, Frontend)
docker-compose -d

# 4. Access the application
# Frontend: http://localhost
# Backend API docs: http://localhost:8000/docs
```

That's it! The application should now be running.

### Without Cloning the Repo
You can also use the docker-compose.yml directly:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - recipe-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    image: ghcr.io/efrod/jarit/backend:latest
    expose:
      - "8000"
    environment:
      - PYTHONPATH=/app
      - DATABASE_URL=${DATABASE_URL}
      - LOGFIRE_WRITE_TOKEN=${LOGFIRE_WRITE_TOKEN:-}
      - LLM_PROVIDER=${LLM_PROVIDER}
      - MODEL_NAME=${MODEL_NAME}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OLLAMA_URL=${OLLAMA_URL:-}
      - ALLOW_REGISTRATION=${ALLOW_REGISTRATION:-false}
      - ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-30}
      - SECRET_KEY=${SECRET_KEY}
      - ALGORITHM=${ALGORITHM:-HS256}
    command: uv run uvicorn main:app --host 0.0.0.0 --port 8000 --env-file /app/.env
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - recipe-network
    restart: unless-stopped

  frontend:
    image: ghcr.io/efrod/jarit/frontend:latest
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - recipe-network
    restart: unless-stopped

networks:
  recipe-network:
    driver: bridge

volumes:
  postgres_data:

```

But then you will also have to add the .env file:

```bash
# Settings and API-Keys for Models to use
# Note OPENAI_API_KEY is mandatory, as it powers whisper
# Get the model names and provider names from the pydantic AI documentation.
LLM_PROVIDER=google
MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=YOUR-KEY-HERE
OPENAI_API_KEY=YOUR-KEY-HERE

# JWT settings
# Allow users to create new accounts. Set it to false if you want full control over who can access the app.
# If false, the first user created will be an admin user who can create other users.
ALLOW_REGISTRATION=false
ACCESS_TOKEN_EXPIRE_MINUTES=30
SECRET_KEY=CHANGEME
ALGORITHM=HS256

# PostgreSQL settings - Change credentials
POSTGRES_DB=devdb
POSTGRES_USER=devuser
POSTGRES_PASSWORD=devpassword
DATABASE_URL=postgresql://devuser:devpassword@postgres:5432/devdb

# Monitoring (optional but useful for debugging)
LOGFIRE_WRITE_TOKEN=LOGFIRE_TOKEN

```

### Build Docker Images Locally
Follow the instruction from the quick start but use the `docker-compose.dev.yml` file:


```bash
# 1. Clone the repository
git clone https://github.com/eFroD/recipeAgent
cd recipe-agent

# 2. Copy and configure environment file
cp .env_example .env
nano .env  # Edit with your API keys

# 3. Start all services (PostgreSQL, Backend, Frontend)
docker compose -f docker-compose.dev.yml up --build -d

# 4. Access the application
# Frontend: http://localhost
# Backend API docs: http://localhost:8000/docs
```

### Development Setup

For local development with hot reload:

#### Backend Setup

```bash
# 1. Install uv package manager (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Navigate to project root
cd recipe-agent

# 3. Install Python dependencies
uv sync

# 4. Start PostgreSQL (using Docker)
docker-compose up postgres -d

# 5. Configure environment
cp .env_example .env
nano .env  # Add your API keys

# 6. Run backend with hot reload
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload --env-file .env
```

#### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Configure environment
echo "VITE_API_BASE=http://localhost:8000/api/v1" > .env.local

# 4. Start development server
npm run dev

# Frontend will be available at http://localhost:5173
```

## Configuration

### Environment Variables

Edit the `.env` file in the project root:

```bash
# LLM Provider Configuration
LLM_PROVIDER=google              # Options: google, openai, ollama
MODEL_NAME=gemini-2.5-flash      # Model to use for extraction
GOOGLE_API_KEY=your_key_here     # Required if using Google
OPENAI_API_KEY=your_key_here     # Required for Whisper (always) and GPT models

# Authentication Settings
ALLOW_REGISTRATION=true          # Enable/disable public registration
ACCESS_TOKEN_EXPIRE_MINUTES=30   # JWT token expiration
SECRET_KEY=your_secret_key       
ALGORITHM=HS256


POSTGRES_DB=devdb
POSTGRES_USER=devuser
POSTGRES_PASSWORD=devpassword    
DATABASE_URL=postgresql://devuser:devpassword@postgres:5432/devdb

VITE_API_BASE=http://localhost:8000/api/v1
```

### Obtaining API Keys

#### Google Gemini API Key

Google Gemini offers a free tier:

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Get API Key" or "Create API Key"
4. Copy the generated API key
5. Add to `.env`: `GOOGLE_API_KEY=your_key_here`

#### OpenAI API Key

Required for Whisper transcription (mandatory) and optional for GPT models:

1. Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Name your key 
5. Copy the API key
6. Add to `.env`: `OPENAI_API_KEY=your_key_here`

**Note:** OpenAI requires payment setup. Whisper API is very affordable (~$0.006/minute).

### Obtaining Mealie API Key

To upload recipes to Mealie, you need to generate an API token:

#### Step 1: Access Your Mealie Instance

Open your Mealie instance in a web browser (e.g., `http://your-mealie-instance:9000`)

#### Step 2: Log In

Log in with your Mealie credentials

#### Step 3: Navigate to Profile Settings

1. Click on your **profile icon** (usually in the top-right corner)
2. Select **"Profile"** from the dropdown menu

#### Step 4: Go to API Tokens Section

1. In your profile page, look for the **"API Tokens"** section
2. Click on **"API Tokens"** or scroll down to the tokens section

#### Step 5: Generate New Token

1. Click the **"Create API Token"** or **"Generate Token"** button
2. Enter a name for your token.
3. Set an expiration date (optional - "Never" is recommended for convenience)
4. Click **"Create"** or **"Generate"**

#### Step 6: Copy Your API Token

1. Your new API token will be displayed (usually only once!)
2. **Copy the entire token** - it should look something like:
   ```
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiw...
   ```
3. Store it securely - you won't be able to see it again!

#### Step 7: Configure in JarIt

1. Log in to JarIt
2. Navigate to your **Dashboard**
3. Scroll to the **"Mealie Configuration"** section
4. Enter your Mealie details:
   - **Base URL**: Your Mealie instance URL (e.g., `http://192.168.1.100:9000`)
   - **API Key**: Paste the token you just copied
5. Click **"Save"** or **"Test Connection"**

## Usage

### First Time Setup

1. **Access the application** at `http://localhost` (Docker) or `http://localhost:5173` (dev)
2. **Register the first user** - they will automatically become an admin
3. **Set up Mealie integration** in the dashboard (see [Obtaining Mealie API Key](#obtaining-mealie-api-key))
4. **(Optional) Disable registration** - Set `ALLOW_REGISTRATION=false` in `.env` for security

### Extracting a Recipe

1. **Navigate to Dashboard**
2. **Paste a video URL** (YouTube, TikTok, Instagram, etc.)
3. **Select target language** (optional - defaults to English)
4. **Click "Extract Recipe"**
5. Wait for AI to process (10-60 seconds depending on video length)
6. **Review and edit** the extracted recipe
7. **Upload to Mealie** with one click!

### Admin Panel

Admins can manage users:

1. Navigate to **Admin Panel** 
2. **View all users** and their roles
3. **Create new users** manually
4. **Delete users**
