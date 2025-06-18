# Russian Energy Platform

## Overview

This is a Telegram-based Russian energy utility platform that provides customer services through a Telegram bot and integrated Mini App. The platform enables customers to submit meter readings, view history, request meter replacements, and access support services directly within Telegram's ecosystem.

## System Architecture

The system follows a microservices architecture with the following main components:

### Telegram Mini App
- **Interface**: Progressive Web App integrated into Telegram
- **Features**: Meter readings submission, history viewing, service orders, support contact
- **Technologies**: Telegram WebApp API, vanilla JavaScript, CSS3, HTML5
- **Theme**: Automatically adapts to user's Telegram theme (light/dark mode)

### Backend
- **API Server**: FastAPI-based REST API
- **Authentication**: OAuth2 integration with Gosuslugi (Russian government services)
- **Database**: SQLite for data persistence
- **Technologies**: Python 3.11, FastAPI, SQLite, Pydantic

### Bot Service
- **Telegram Bot**: Interactive bot for customer services with Mini App integration
- **Features**: Mini App launcher, quick meter readings, support contact, service orders
- **Technologies**: python-telegram-bot library, asyncio, Telegram WebApp API
- **Integration**: Seamless data exchange between bot and Mini App

### Service Management
- **Orchestration**: Centralized service manager for running all components
- **Database Initialization**: Automated schema setup and migration
- **Process Management**: Signal handling and graceful shutdown

## Key Components

### Database Layer (`database.py`)
- Multi-database initialization system
- Separate databases for different services:
  - `bot_data.db`: Telegram bot user data and interactions
  - `backend_data.db`: Web portal and API data
  - `auth_users.db`: OAuth authentication data
  - `readings.db`: Meter readings and history
- Automated schema creation and migration

### Web Application (`index.html`, `style.css`, `script.js`)
- Promotional content management with filtering
- Email subscription functionality
- Responsive design for mobile and desktop
- Integration links to Telegram bot

### API Backend (`backend.py`)
- OAuth2 flow handling for Gosuslugi integration
- REST API endpoints for web portal
- CORS configuration for cross-origin requests
- User data management and validation

### Telegram Bot (`bot.py`)
- Conversational interface for utility services
- Meter reading submission workflow
- History viewing and support contact
- OAuth authentication integration
- Keyboard-based navigation

### Service Orchestrator (`run_services.py`)
- Dependency checking and validation
- Multi-service startup and management
- Signal handling for graceful shutdown
- Process monitoring and error handling

## Data Flow

1. **User Authentication**: Users can authenticate via Gosuslugi OAuth on both web and Telegram
2. **Meter Readings**: Submitted through Telegram bot, stored in readings database
3. **Web Portal**: Displays promotional content, handles email subscriptions
4. **Cross-Service Data**: User authentication data shared between web and bot services
5. **Database Persistence**: All user interactions and data stored in SQLite databases

## External Dependencies

### Required Python Packages
- `fastapi`: Web API framework
- `uvicorn`: ASGI server for FastAPI
- `python-telegram-bot`: Telegram bot API wrapper
- `requests`: HTTP client for OAuth integration
- `aiosqlite`: Async SQLite database adapter
- `nest_asyncio`: Nested event loop support
- `pydantic[email]`: Data validation with email support

### External Services
- **Gosuslugi OAuth**: Russian government authentication service
- **Telegram Bot API**: For bot functionality
- **SQLite**: Embedded database system

### Environment Variables
- `BOT_TOKEN`: Telegram bot token
- `GOSUSLUGI_CLIENT_ID`: OAuth client ID for Gosuslugi
- `GOSUSLUGI_CLIENT_SECRET`: OAuth client secret
- `REDIRECT_URI`: OAuth callback URL

## Deployment Strategy

### Local Development
- Single command startup via `run_services.py`
- Automatic dependency installation
- Database initialization on first run
- All services run in parallel processes

### Production Considerations
- Environment variable configuration required
- SSL certificates needed for OAuth callbacks
- Database backup and migration strategy
- Process monitoring and restart capabilities
- Load balancing for multiple instances

### Replit Deployment
- Configured for Replit environment with `.replit` file
- Python 3.11 runtime with required packages
- Port 5000 exposed for web access
- Parallel service execution via workflows

## Changelog
- June 18, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.