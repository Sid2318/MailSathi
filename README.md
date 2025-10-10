# MailSathi

MailSathi is an email translation application that connects to your Gmail account and translates email content from English to Marathi.

## Features

- Connect to your Gmail account to view recent emails
- Translate email content from English to Marathi
- Direct text translation without needing Gmail
- Clean, responsive UI

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite
- **Translation**: Ollama LLaMA3
- **Email Integration**: Gmail API

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- Ollama with llama3 model
- Google OAuth credentials

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (if not using the existing one):
   ```bash
   python -m venv env
   ```

3. Activate the virtual environment:
   - Windows:
     ```powershell
     .\env\Scripts\Activate.ps1
     ```
   - Linux/Mac:
     ```bash
     source env/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file with your Google OAuth credentials:
   ```
   GMAIL_CLIENT_ID=your_client_id
   GMAIL_CLIENT_SECRET=your_client_secret
   ```

6. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

4. Access the application at [http://localhost:5174](http://localhost:5174)

### Ollama Setup

Make sure Ollama is running with the LLaMA3 model:

```bash
ollama serve
ollama pull llama3
```

## Usage

1. Open the application in your browser
2. Click "Connect Gmail Account" and complete OAuth flow
3. View your emails and translate them with a single click
4. Or use the direct translation box for custom text

## License

[MIT](LICENSE)