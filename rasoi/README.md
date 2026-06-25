# RasOI Kitchen Intelligence

A multimodal AI-powered kitchen intelligence web application designed to reduce food waste through intelligent pantry management.

## Project Structure

```
rasoi/
├── frontend/          # React + TypeScript + Vite + Tailwind CSS
├── backend/           # FastAPI + Python
├── .gitignore         # Root gitignore
└── README.md          # This file
```

## Prerequisites

- **Node.js** 18+ and npm (for frontend)
- **Python** 3.11+ and pip (for backend)
- **Anthropic API Key** (for Claude Sonnet 4 Vision and Text APIs)

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Windows**: `venv\Scripts\activate`
   - **macOS/Linux**: `source venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

6. Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_actual_api_key_here
   ```

7. Run the backend server:
   ```bash
   python main.py
   ```
   
   The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```
   
   The app will be available at `http://localhost:5173`

## Development

### Backend Development

- **Run server**: `python main.py`
- **API docs**: Visit `http://localhost:8000/docs` for interactive API documentation
- **Health check**: `http://localhost:8000/api/health`

### Frontend Development

- **Dev server**: `npm run dev`
- **Build**: `npm run build`
- **Lint**: `npm run lint`
- **Preview**: `npm run preview`

## Features

- 📸 Multimodal ingredient input via photos or grocery receipts
- 🗄️ Live pantry inventory management
- ⚠️ Expiration detection and alerts
- 🍳 Smart meal recommendations based on available ingredients
- 🔄 Intelligent substitution engine for missing ingredients
- 👨‍🍳 Step-by-step recipe view
- 🥄 Chammach - animated talking spoon mascot for contextual guidance

## Technology Stack

### Frontend
- React 18 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- React Router for navigation
- Axios for API communication

### Backend
- FastAPI (Python 3.11+)
- Pydantic for data validation
- Anthropic Claude Sonnet 4 APIs (Vision & Text)
- SQLite for data persistence
- httpx for HTTP client

## License

Proprietary
