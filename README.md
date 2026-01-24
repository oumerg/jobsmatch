# Telegram Job Matching Bot

An intelligent Telegram bot that scans job postings from specified groups and channels, stores them in a database, and matches them to user queries based on job title, description, location, salary, or keywords.

## Features

- 🔍 **Scanning**: Monitors messages in joined groups and channels for job-related content
- 📝 **Parsing**: Extracts structured data from messages using NLP and regex patterns
- 💾 **Storage**: Saves parsed jobs in SQLite database for quick querying
- 🤖 **User Interaction**: Users can send queries via private messages or inline queries
- 🎯 **Matching**: Uses keyword matching and fuzzy search to recommend jobs
- 🔔 **Notifications**: Optional push notifications for new matching jobs

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd job-matching-bot

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (optional, for advanced parsing)
python -m spacy download en_core_web_sm
```

### 2. Configuration

#### Option 1: PostgreSQL (Recommended for Production)

1. **Install PostgreSQL locally**:
   ```bash
   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql
   
   # Windows
   # Download from https://postgresql.org/download/windows/
   ```

2. **Run the setup script**:
   ```bash
   python scripts/setup_local_postgres.py
   ```

3. **Or use Docker** (easiest):
   ```bash
   docker-compose up -d
   ```

4. **Create `.env` file**:
   ```env
   # Database Configuration
   DB_TYPE=postgresql
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=jobbot
   POSTGRES_USER=jobbot_user
   POSTGRES_PASSWORD=jobbot_password
   
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=target_channel_id
   ```

#### Option 2: SQLite (Default/Development)

Create a `.env` file:
```env
DB_TYPE=sqlite
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=target_channel_id
```

### 3. Run the Bot

```bash
python run.py
```

## Project Structure

```
job-matching-bot/
├── .env                      # Environment variables
├── .gitignore
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── run.py                    # Main entry point
│
├── config/                   # Configuration
│   ├── __init__.py
│   ├── settings.py           # Environment settings
│   └── constants.py          # Job keywords, enums
│
├── bot/                      # Core Telegram bot logic
│   ├── __init__.py
│   └── application.py        # Application setup
│
├── handlers/                 # Message/command handlers
│   ├── __init__.py
│   ├── start.py              # /start, /help commands
│   ├── user_query.py         # Job search messages
│   ├── admin.py              # Admin commands
│   └── error.py              # Error handlers
│
├── scanners/                 # Message scanning logic
│   ├── __init__.py
│   ├── message_scanner.py    # Main scanner
│   └── job_detector.py       # Job posting detection
│
├── parsers/                  # Job parsing
│   ├── __init__.py
│   ├── rule_based.py         # Regex-based parser
│   ├── nlp_parser.py         # NLP-based parser
│   └── utils.py              # Text utilities
│
├── database/                 # Database layer
│   ├── __init__.py
│   ├── models.py             # Data models
│   ├── repository.py         # Abstract repository
│   └── sqlite.py             # SQLite implementation
│
├── services/                 # Business logic
│   ├── __init__.py
│   ├── job_service.py        # Job operations
│   ├── match_service.py      # Matching algorithms
│   └── notification_service.py  # Notifications
│
└── utils/                    # Helper functions
    ├── __init__.py
    ├── logging.py
    └── keyboards.py          # UI keyboards
```

## Usage

### For Users

1. **Start the bot**: Send `/start` to get welcome message and menu
2. **Search jobs**: Type what you're looking for, e.g.:
   - "Python developer in Addis Ababa"
   - "Remote marketing jobs"
   - "Entry level design positions"
3. **Recent jobs**: Use `/recent` to see latest postings
4. **Get help**: Use `/help` for all commands

### For Administrators

1. **Admin panel**: Use `/admin` to access admin functions
2. **Scan channels**: Use `/scan <channel_id>` to scan specific channels
3. **View stats**: Use `/admin_stats` for detailed statistics
4. **Cleanup**: Use `/cleanup` to remove old jobs

## Configuration Options

### Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
- `TELEGRAM_CHAT_ID`: Default channel to monitor
- `DB_TYPE`: Database type ('sqlite', 'postgresql', 'mongodb')
- `POSTGRES_HOST`: PostgreSQL host (default: localhost)
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)
- `POSTGRES_DB`: PostgreSQL database name (default: jobbot)
- `POSTGRES_USER`: PostgreSQL username (default: jobbot_user)
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRESQL_URI`: Full PostgreSQL connection string (optional)
- `SQLITE_DB_PATH`: SQLite database file path
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Bot Settings

- `MAX_MESSAGE_LENGTH`: Maximum message length (default: 4096)
- `JOBS_PER_PAGE`: Jobs to show per search (default: 10)
- `MATCH_THRESHOLD`: Minimum match score (default: 0.6)
- `SCAN_INTERVAL`: Scanning interval in seconds (default: 30)
- `MAX_JOB_AGE_DAYS`: Maximum job age in days (default: 30)

## API Reference

### Database Models

- **JobModel**: Represents a job posting
- **UserModel**: Represents a bot user
- **SearchQuery**: Represents a user search
- **JobMatch**: Represents a job-user match

### Services

- **JobService**: Job CRUD operations
- **MatchService**: Job matching algorithms
- **NotificationService**: User notifications

### Parsers

- **RuleBasedParser**: Regex-based job parsing
- **NLPParser**: Advanced NLP-based parsing

## Development

### Adding New Features

1. **New Commands**: Add handlers in `handlers/` directory
2. **Database Changes**: Update models in `database/models.py`
3. **Parsing Logic**: Modify parsers in `parsers/` directory
4. **Business Logic**: Add services in `services/` directory

### Testing

```bash
# Run tests (when implemented)
python -m pytest tests/

# Test parsing
python -c "from parsers.rule_based import RuleBasedParser; print(RuleBasedParser().parse_message('test message', 'channel', 1))"
```

### Deployment

1. Set up environment variables
2. Install dependencies
3. Run with `python run.py`
4. Consider using process managers like `systemd` or `supervisor`

## Troubleshooting

### Common Issues

1. **Bot Token Error**: Ensure `TELEGRAM_BOT_TOKEN` is correct
2. **Database Issues**: Check file permissions for SQLite
3. **Parsing Errors**: Review job posting patterns in `config/constants.py`
4. **Memory Issues**: Adjust `SCAN_INTERVAL` and cleanup settings

### Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the bot administrator
- Check the logs for error details

---

**Note**: This bot is designed to be ethical and respects user privacy. It only processes publicly available job postings and does not store personal information without consent.
