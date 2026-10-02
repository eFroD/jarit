<div align="center">

<img src="frontend/static/logo_800.png" alt="JarIt" width="150">
<h1>JarIt!</h1>
</div>

**AI-powered recipe extraction from videos to Mealie**

JarIt is an intelligent application that automatically extracts structured recipes from video content (YouTube, TikTok, Instagram, and more using AI and seamlessly uploads them to your [Mealie](https://mealie.io/) recipe manager.


## Features

- **Multi-Platform Support** - Extract recipes from YouTube, TikTok, Instagram, and more via yt-dlp
- **AI-Powered Extraction** - Uses Pydantic AI with support for multiple LLM providers:
  - Google Gemini (default)
  - OpenAI GPT Models
  - Ollama (local models)
- **Audio Transcription** - Automatic video transcription using OpenAI Whisper
- **Smart Recipe Parsing** - Extracts ingredients, instructions, timing, and metadata
- **Multi-Language** - The app speaks English, German, Spanish, French and Italian; recipes are written in your language by default and can be translated into any of them during extraction
- **Background Extraction** - Extraction runs in the background with live progress; leave the page and come back any time
- **Extraction History** - Every extraction is kept: reopen, edit and upload recipes later, see which ones are already in Mealie
- **Recipe Editor** - Review and edit extracted recipes before uploading; edits are saved
- **Mealie Integration** - One-click upload to your Mealie instance
- **Multi-User Support** - User authentication with admin panel
- **Secure** - JWT authentication, role-based access, and users' integration credentials (e.g. Mealie API keys) encrypted at rest
- **Docker Ready** - Complete Docker setup for easy deployment

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Quick Start (Docker)](#quick-start-docker-compose)
  - [Without Cloning the Repo](#without-cloning-the-repo)
  - [Build Docker Images Locally](#build-docker-images-locally)
  - [Development Setup](#development-setup)
- [Configuration](#configuration)
  - [Encryption Key for Integration Credentials](#encryption-key-for-integration-credentials)
  - [Background Extraction and Database Migrations](#background-extraction-and-database-migrations)
  - [Obtaining Mealie API Key](#obtaining-mealie-api-key)
- [Usage](#usage)
  - [Language](#language)
- [Contributing](#contributing)

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
      - JARIT_ENCRYPTION_KEY=${JARIT_ENCRYPTION_KEY}
      - JARIT_MAX_CONCURRENT_EXTRACTIONS=${JARIT_MAX_CONCURRENT_EXTRACTIONS:-2}
      - ALGORITHM=${ALGORITHM:-HS256}
    command: uv run uvicorn main:app --host 0.0.0.0 --port 8000
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

# Encryption of user integration credentials - required, see below
JARIT_ENCRYPTION_KEY=CHANGEME

# Maximum number of extractions running at the same time (default 2)
JARIT_MAX_CONCURRENT_EXTRACTIONS=2

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
git clone https://github.com/eFroD/jarit
cd jarit

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
cd jarit

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

# Encryption of users' integration credentials (required)
JARIT_ENCRYPTION_KEY=your_generated_key

# Recipe extraction
JARIT_MAX_CONCURRENT_EXTRACTIONS=2   # Extractions running at the same time; more wait their turn


POSTGRES_DB=devdb
POSTGRES_USER=devuser
POSTGRES_PASSWORD=devpassword    
DATABASE_URL=postgresql://devuser:devpassword@postgres:5432/devdb

VITE_API_BASE=http://localhost:8000/api/v1
```

### Encryption Key for Integration Credentials

Users store their own integration credentials (e.g. Mealie API keys) in JarIt. These are encrypted in the database with a key that only you, the host, hold. The key is read from the `JARIT_ENCRYPTION_KEY` environment variable and is never written to the database or the logs.

**Generate a key** with one of these commands:

```bash
# With uv, inside a checkout of this repository
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# With Docker only
docker run --rm python:3.13-slim sh -c "pip -q install cryptography && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
```

Add the output to your `.env` file:

```bash
JARIT_ENCRYPTION_KEY=<your generated key>
```

If the key is missing or invalid, the backend does not start. Instead it prints a freshly generated key and the exact `.env` line to copy into your `.env`. That suggestion appears in the container log, so if you prefer, generate the key yourself with one of the commands above.

**Back up the key** together with your database backups. Without it, the stored integration credentials cannot be read.

**Rotating or losing the key:** JarIt uses exactly one key and does not re-encrypt existing data. If you change or lose it, all stored integration credentials become unreadable. The app keeps working, and affected users see a message asking them to enter their Mealie API key again in the settings. There is no way to recover the old values without the old key.

**Upgrading from an earlier version:** Older versions stored integration credentials in plain text. Set `JARIT_ENCRYPTION_KEY` before upgrading. On the first start, JarIt encrypts all existing credentials automatically, and users do not need to do anything.

### Background Extraction and Database Migrations

Extractions run as background jobs **inside the backend process** – no extra worker, queue or cache service is needed. Keep this in mind:

- **Run the backend as a single process.** Do not start uvicorn with `--workers` greater than 1; the provided compose files already run one process.
- **`JARIT_MAX_CONCURRENT_EXTRACTIONS`** (default `2`) limits how many extractions run at the same time. Further jobs wait in submission order. An invalid value falls back to `2` with a warning in the log.
- **Restarts interrupt running jobs.** Jobs that were waiting or running when the backend stopped are marked as failed ("Interrupted by an application restart") on the next start. Users can start them again with one click.
- An extraction that takes longer than 10 minutes is stopped and marked as timed out.

**Database migrations run automatically** when the backend starts, before it accepts requests. Upgrading needs no manual steps: pull the new image and restart. Installations created by an older version (without migration history) are detected and brought under migration control without data loss. As with any upgrade, **back up your database first**.

For development, the same migrations are available through Alembic (uses `DATABASE_URL`):

```bash
uv run alembic upgrade head                              # apply migrations
uv run alembic revision --autogenerate -m "describe it"  # create a new migration after changing models
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
3. **Select the recipe language** (optional - your own language is preselected; the recipe is translated if the video is in another language)
4. **Click "Extract Recipe"** – you are taken to a progress page right away
5. Follow the steps (fetching the description, transcribing audio if needed, extracting the recipe). This usually takes 10-60 seconds; you can leave the page and come back via the dashboard or **History**
6. **Review and edit** the extracted recipe – use **Save changes** to keep your edits
7. **Upload to Mealie** with one click!

If an extraction fails, the progress page and the history show the reason (e.g. "Video unreachable") and a **Try again** button.

### History

**History** in the navigation lists all your extractions, newest first, with their status and whether the recipe is already in Mealie. From there you can reopen and edit a recipe, upload it (again), retry failed extractions, or delete entries. Each user only ever sees their own extractions, admins included. Deleting an entry does not remove the recipe from Mealie.

### Language

Every user has a language: **English, Deutsch, Español, Français or Italiano**. It is used for

- the whole app (texts, error messages, dates), and
- the preselected recipe language when you extract a recipe.

Change it any time under **Dashboard → Language**; the app switches immediately. New accounts start with the language chosen at registration (preselected from the browser), existing accounts with English. Before signing in, the app follows the browser language.

Changing your language never changes recipes you already extracted.

**Adding or changing a UI text** (developers): all texts live in `frontend/src/lib/i18n/messages/`. Add the key to `en.ts` first, then to `de.ts`, `es.ts`, `fr.ts` and `it.ts`; `npm run check` fails as long as any language is missing a key.

**API clients**: `PATCH /api/v1/users/me` with `{"language": "de"}` changes the language; `POST /api/v1/extraction-jobs` without `target_language` uses it. Error responses contain a stable `code` next to the English `detail`, e.g. `{"detail": "Only failed extractions can be retried", "code": "JOB_NOT_RETRYABLE"}`.

### Admin Panel

Admins can manage users:

1. Navigate to **Admin Panel** 
2. **View all users** and their roles
3. **Create new users** manually
4. **Delete users**

## Contributing
I think the app has much more potential, than what it can do now. Check the [Issues](https://github.com/eFroD/jarit/issues) if you want to see what is going on. I also think of the following enhancements:
+ Integrate new recipe databases beyond mealie. The app is designed in a way, that you can write your own integrator. The database can store multiple api keys, identified by a service name.
+ Support for more LLM providers and better self-hosted model support. I did not test any of the self-hosted functionalities yet. Any insight is greatly appreciated.
+ And more! If you have any Idea, feel free to post an issue.