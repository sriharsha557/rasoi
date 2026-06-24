# 🥄 RasOI — Powered by Organic Intelligence

> *Rasoi (रसोई) — Hindi for kitchen. OI — Organic Intelligence.*
> 
> **Turn what's in your fridge into tonight's dinner. Zero waste. Zero guesswork.**

---

## 🏆 Built for Colruyt Group India Hackathon 2025

**Problem Statement:** Scan, Plan & Cook — Intelligent Pantry  
**Team:** [Your Team Name]  
**Category:** Multimodal AI / Consumer App

---

## 🌟 What is RasOI?

RasOI is a multimodal AI-powered kitchen intelligence web app that helps you:

- 📸 **Scan** your fridge, pantry shelf, or grocery receipt using your camera
- 🧠 **Detect** what's expiring soon and highlight it automatically
- 🍳 **Plan** meals that use ingredients before they go bad
- 🔄 **Substitute** missing ingredients intelligently
- 👨‍🍳 **Cook** with step-by-step guidance and auto-update your pantry when done

And your guide through all of it? **Chammach** 🥄 — RasOI's friendly talking spoon mascot.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 📸 Ingredient Scan | Upload a fridge photo or receipt — Claude Vision extracts ingredients instantly |
| 🟥 Expiry Alerts | Color-coded pantry: Green (fresh) · Amber (2 days) · Red (today) |
| 🍽️ Smart Meal Recommendations | AI ranks meals by expiry priority — uses what needs to go first |
| 🔄 Substitution Engine | Missing an ingredient? AI suggests the best swap with explanation |
| 👨‍🍳 Step-by-Step Recipes | Built-in timers, ingredient amounts adjusted to your pantry |
| 🥄 Chammach Mascot | Animated talking spoon that reacts to every app state with contextual dialogue |
| 🗣️ Voice Input | "I just bought tomatoes" — updates pantry via Web Speech API |
| 🛒 Shopping List | Auto-generates a list of missing ingredients |

---

## 🥄 Meet Chammach

Chammach (चम्मच — spoon in Hindi) is RasOI's animated mascot and conversational guide.

He bounces, wiggles, blinks, and reacts to everything happening in the app:

```
App loads     → "Namaste! I'm Chammach. Show me your fridge!"
Scan complete → "Found 8 ingredients! Your paneer expires tomorrow."
Missing item  → "No cream? No problem. Milk + butter works just as well!"
Meal cooked   → "Well cooked! I've updated your pantry. What's for tomorrow?"
```

Chammach is built as a pure SVG React component with CSS animations — no external libraries needed.

---

## 🏗️ Tech Stack

```
Frontend    →  React + Tailwind CSS
Backend     →  FastAPI (Python)
AI Engine   →  Claude claude-sonnet-4-6 (Vision + Text via Anthropic API)
State       →  In-memory (Python dict, session-scoped)
Deployment  →  Vercel (frontend) + Render (backend)
```

---

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- Anthropic API key

### 1. Clone the repository

```bash
git clone https://github.com/your-username/rasoi.git
cd rasoi
```

### 2. Set up the backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
uvicorn main:app --reload --port 8000
```

### 3. Set up the frontend

```bash
cd frontend
npm install
cp .env.example .env.local
# Set VITE_API_URL=http://localhost:8000
npm run dev
```

### 4. Open in browser

```
http://localhost:5173
```

---

## 📁 Project Structure

```
rasoi/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chammach.jsx        # Talking spoon mascot
│   │   │   ├── PantryBoard.jsx     # Ingredient grid with expiry indicators
│   │   │   ├── MealCards.jsx       # Meal recommendation cards
│   │   │   ├── RecipeView.jsx      # Step-by-step recipe with timer
│   │   │   └── ScanUpload.jsx      # Image/receipt upload component
│   │   ├── pages/
│   │   │   └── App.jsx
│   │   └── main.jsx
│   └── package.json
│
├── backend/
│   ├── main.py                     # FastAPI app
│   ├── routes/
│   │   ├── scan.py                 # POST /api/scan — ingredient extraction
│   │   ├── recommend.py            # GET /api/recommend — meal suggestions
│   │   ├── substitute.py           # POST /api/substitute — ingredient swap
│   │   └── recipe.py               # GET /api/recipe/{id}
│   ├── services/
│   │   └── claude_service.py       # Anthropic API calls
│   ├── state/
│   │   └── pantry_store.py         # In-memory pantry state
│   └── requirements.txt
│
├── docs/
│   └── RasOI_PRD.docx              # Full Product Requirements Document
│
└── README.md
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/scan` | Upload image → extract ingredients |
| `GET` | `/api/recommend` | Get meal suggestions (expiry-first) |
| `POST` | `/api/substitute` | Get ingredient substitution |
| `GET` | `/api/recipe/{id}` | Full recipe with steps |
| `PUT` | `/api/pantry/add` | Add ingredient manually |
| `DELETE` | `/api/pantry/{id}` | Remove ingredient |
| `POST` | `/api/pantry/cooked` | Mark recipe cooked, update pantry |

---

## 🎯 Demo Flow

1. **Open app** → Chammach greets you
2. **Click "Scan My Fridge"** → Upload a fridge photo live
3. **Pantry populates** → Expiring items highlighted in red/amber
4. **Click "What Can I Cook?"** → Expiry-prioritized meal cards appear
5. **Select a meal** → Missing ingredient triggers substitution offer
6. **Cook mode** → Step-by-step with timer
7. **Mark as cooked** → Pantry auto-updates

---

## 🌱 Why RasOI?

> One-third of all food produced globally is wasted.  
> Most of it happens at home — forgotten ingredients, no visibility, no plan.

RasOI's **Organic Intelligence** doesn't just suggest recipes. It understands your kitchen, respects what you have, and helps you use it wisely — one meal at a time.

---

## 🗺️ Roadmap (Post-Hackathon)

- [ ] Voice assistant mode (full Chammach conversation)
- [ ] Weekly meal planner with nutritional summary
- [ ] Multi-user household support
- [ ] Grocery delivery integration (Blinkit / Zepto API)
- [ ] Regional cuisine profiles (South Indian, Bengali, Punjabi)
- [ ] Offline mode with local model (Ollama)

---

## 👥 Team

| Name | Role |
|---|---|
| [Team Member 1] | Full Stack + AI Integration |
| [Team Member 2] | Frontend + Chammach Design |
| [Team Member 3] | Backend + Prompt Engineering |
| [Team Member 4] | UI/UX + Demo |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <strong>🥄 RasOI — Powered by Organic Intelligence</strong><br>
  <em>Colruyt Group India Hackathon 2025</em>
</div>
