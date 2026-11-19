# AI Chat Assistant

A modern, responsive AI chat app built with **FastAPI**, **OpenAI**, **MongoDB**, and plain HTML/CSS/JavaScript.

## Features
- User and AI message bubbles
- Real-time streaming (responses appear gradually)
- Sidebar with saved conversations (reopen or delete any chat)
- Conversations, prompts, AI responses and timestamps stored in MongoDB
- Tone selector: Professional, Casual, Concise (sent to OpenAI as a system instruction)
- Copy AI response and Export chat as TXT
- Input validation and friendly error messages
- Secrets kept in a `.env` file

## Project structure
```
ai-chat-assistant/
├── main.py                  # App entry point
├── config.py                # Reads .env settings
├── database.py              # MongoDB connection
├── schemas.py               # Request validation
├── routes/chat_routes.py    # API endpoints
├── services/openai_service.py  # OpenAI + tone instructions
├── static/                  # index.html, style.css, app.js
├── requirements.txt
├── .env.example
└── README.md
```

## Setup (VSCode terminal)

Requirements: Python 3.10+, a MongoDB database (local or free MongoDB Atlas), and an OpenAI API key.

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

If PowerShell blocks activation, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Configure
Open `.env` and set:
```
OPENAI_API_KEY=your real key
MONGODB_URI=mongodb://localhost:27017        # or your Atlas connection string
```

## Run
```bash
uvicorn main:app --reload
```
Open **http://127.0.0.1:8000**

## API endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat/stream` | Send a message, stream the reply |
| GET | `/api/conversations` | List saved chats |
| GET | `/api/conversations/{id}` | Open a chat |
| DELETE | `/api/conversations/{id}` | Delete a chat |
| GET | `/api/conversations/{id}/export` | Download chat as TXT |

## Troubleshooting
- **Missing environment variable**: you did not create `.env` or left the placeholder key.
- **ServerSelectionTimeoutError**: MongoDB is not running, or the Atlas IP allow-list / URI is wrong.
- **Invalid API key / quota reached**: check your key and billing at platform.openai.com.
