# AI Lost & Found Assistant

AI Lost & Found Assistant is a FastAPI + React web application for reporting lost and found items, matching them with text and image embeddings, and notifying the owner when a confident match is found.

## Project Structure

```text
AI-Lost-Found-Assistant/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   ├── uploads/
│   ├── requirements.txt
│   ├── .env.example
│   └── seed.py
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── .env.example
└── README.md
```

## Backend Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Copy `backend/.env.example` to `backend/.env` and update the values.
4. Run the API:

```powershell
uvicorn backend.main:app --reload
```

5. Optional: seed demo data.

```powershell
python backend/seed.py
```

The API creates the SQLite schema on startup.

## Frontend Setup

1. Install dependencies:

```powershell
cd frontend
npm install
```

2. Copy `frontend/.env.example` to `frontend/.env` if you want a custom API URL.
3. Run the app:

```powershell
npm run dev
```

The frontend expects the API at `http://localhost:8000` by default.

## AI Matching Pipeline

The backend stores item reports in SQLite and stores embeddings as JSON in the database. FAISS indexes are rebuilt at startup from those stored embeddings.

On each new report:

1. The text payload is composed from the item fields and encoded with `sentence-transformers/all-MiniLM-L6-v2`.
2. If an image is present, the image is preprocessed with OpenCV/Pillow and encoded with OpenCLIP.
3. The new embedding is compared against the opposite report type using FAISS and cosine similarity.
4. A weighted final score is computed from text and image scores.
5. If the score is above `MATCH_THRESHOLD`, a match row is created and an email notification is attempted.

If SMTP is not configured, the email step is logged and skipped.

## Email Configuration

Update `backend/.env` with your SMTP settings. Gmail or Mailtrap both work.

Useful values:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-user
SMTP_PASSWORD=your-password
SMTP_SENDER=noreply@lostfound.app
COLLECTION_POINT_INFO="Security Office, Block A, 9am-5pm"
```

The email contains item details, image links, collection instructions, and a link to the match detail page.

## Known Limitations

1. The app is optimized for local/demo use, not high-scale production.
2. FAISS indexes are rebuilt in memory on startup instead of being persisted separately.
3. Email sending is best-effort and will not fail the request if SMTP is unavailable.
4. There is no admin moderation dashboard yet.

## Manual Test Checklist

1. Register a new user.
2. Log in and confirm the dashboard loads.
3. Submit a lost item report with and without an image.
4. Submit a found item report that should match the lost report.
5. Confirm that a match record appears in the dashboard.
6. Open the match detail page and confirm or reject the match.
7. Verify the item statuses update accordingly.

## API Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `GET /users/me`
- `POST /lost-items`
- `GET /lost-items`
- `POST /found-items`
- `GET /found-items`
- `GET /matches`
- `GET /matches/{id}`
- `POST /matches/{id}/confirm`
- `POST /matches/{id}/reject`
