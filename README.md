# Russian Energy Platform

## Overview

A comprehensive Telegram-based energy utility platform that provides customer services through a Telegram bot and integrated Mini App. The platform enables customers to submit meter readings, view consumption history, request services, and access support directly within Telegram's ecosystem.

## Features

### Telegram Mini App
- **Modern Interface**: Glass-morphism design with smooth animations
- **Multi-utility Support**: Electric, gas, and water meter readings
- **Real-time Statistics**: Dashboard with consumption charts and analytics
- **Service Requests**: Meter replacement, consultations, inspections, repairs
- **Responsive Design**: Adapts to Telegram's light/dark themes

### Backend API
- **FastAPI Framework**: High-performance async REST API
- **PostgreSQL Database**: Robust data persistence with SQLAlchemy ORM
- **OAuth Integration**: Secure authentication with Gosuslugi (Russian government services)
- **CORS Support**: Cross-origin requests for web integration

### Bot Service
- **Interactive Commands**: Intuitive Telegram bot interface
- **Mini App Integration**: Seamless data exchange between bot and web app
- **Service Management**: Complete customer service workflow

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Chart.js
- **Integration**: Telegram WebApp API, Telegram Bot API
- **Database**: PostgreSQL with environment-based configuration
- **Deployment**: Replit-optimized with automatic scaling

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Telegram Bot Token
- Gosuslugi OAuth credentials (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/russian-energy-platform.git
cd russian-energy-platform
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Database
export DATABASE_URL="postgresql://user:password@localhost/dbname"

# Telegram Bot (optional)
export BOT_TOKEN="your_telegram_bot_token"

# Gosuslugi OAuth (optional)
export GOSUSLUGI_CLIENT_ID="your_client_id"
export GOSUSLUGI_CLIENT_SECRET="your_client_secret"
export REDIRECT_URI="http://localhost:5000/callback"
```

4. Initialize the database:
```bash
python -c "from models import create_tables; create_tables()"
```

5. Start the application:
```bash
python start_web.py
```

The application will be available at `http://localhost:5000`

## API Documentation

Once running, visit `http://localhost:5000/docs` for interactive API documentation.

### Key Endpoints

- `POST /api/readings` - Submit meter readings
- `GET /api/readings/{telegram_id}` - Get reading history
- `POST /api/service-request` - Create service requests
- `POST /api/subscribe` - Email subscriptions
- `GET /api/stats` - Platform statistics

## Project Structure

```
russian-energy-platform/
├── backend.py              # FastAPI application
├── models.py               # Database models
├── bot.py                  # Telegram bot
├── start_web.py           # Web server startup
├── static/                # Web assets
│   ├── index.html         # Mini App interface
│   ├── script.js          # Frontend logic
│   └── style.css          # Styling
├── database.py            # Database utilities
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Development

### Database Migrations

The application automatically creates tables on startup. For schema changes:

1. Update models in `models.py`
2. Restart the application
3. Tables will be updated automatically

### Adding New Features

1. Update backend API in `backend.py`
2. Modify frontend in `static/`
3. Update bot commands in `bot.py`
4. Test integration end-to-end

## Deployment

### Replit Deployment

The project is optimized for Replit deployment:

1. Import the repository to Replit
2. Set environment variables in Replit Secrets
3. Run the project - it will automatically start on port 5000

### Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "start_web.py"]
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in this repository
- Contact the development team
- Check the documentation at `/docs`

## Changelog

### Version 2.0.0 (June 19, 2025)
- Complete platform redesign with modern UI
- PostgreSQL database migration
- Enhanced API with comprehensive endpoints
- Multi-utility support (electric, gas, water)
- Real-time charts and analytics
- Improved error handling and user experience

### Version 1.0.0 (June 18, 2025)
- Initial release
- Basic meter reading functionality
- Telegram bot integration
- SQLite database support