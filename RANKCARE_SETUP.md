# RankCare - Production Ready Setup Guide

## Zero-Cost Development Mode (Current)

RankCare abhi zero-cost development mode mein hai. Ye bina kisi paid API ke chalta hai:

### Features Implemented ✅

1. **Mock Rank Checking**
   - `fake_rank_lookup()` function realistic dummy data generate karta hai
   - Consistent results using keyword-based seeding
   - 10% chance of "not ranking" simulation

2. **Razorpay Mock Payments**
   - Bina Razorpay keys ke bhi payment flow test kar sakte hain
   - Mock orders create hote hain database mein
   - Frontend integration complete hai

3. **SERP API Ready Structure**
   - `serp_api_rank_lookup()` function placeholder ready hai
   - Future mein SERP_API_KEY set karne se real API calls enable ho jayengi

### Setup Steps

#### 1. Environment Variables (.env file already created)

```bash
cd /workspace/api
# .env file already configured for zero-cost mode
# RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET empty hain (mock mode)
# SERP_API_KEY empty hai (mock rank data)
```

#### 2. Backend Start Karein

```bash
cd /workspace/api

# Virtual environment create karein (agar nahi hai)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependencies install karein
pip install -r requirements.txt

# Database setup (PostgreSQL chalu hona chahiye)
# PostgreSQL running check karein

# Server start karein
python run.py
```

API ab `http://127.0.0.1:4000` par chalegi

#### 3. RQ Worker Start Karein (Rank Checking ke liye)

```bash
cd /workspace/api
source venv/bin/activate

# Redis server chalu hona chahiye
redis-server

# Alag terminal mein worker start karein
rq worker rank_check_queue --url redis://localhost:6379
```

#### 4. Frontend Start Karein

```bash
cd /workspace/web

# Dependencies install karein
npm install

# Development server start karein
npm run dev
```

Frontend ab `http://localhost:5173` par chalega

### Testing Payment Flow (Zero-Cost)

1. Login/Register karein
2. Pricing page par jayein
3. Koi plan select karein (Pro/Agency)
4. "Upgrade" button click karein
5. Razorpay checkout mock mode mein khulega
6. Payment complete karne par subscription activate ho jayega

### Production Mode Mein Kab Jayein?

Jab aap ready hon actual APIs use karne ke liye:

1. **SerpAPI Key** (Rank checking ke liye)
   - https://serpapi.com/ se key lein
   - `.env` file mein `SERP_API_KEY` set karein

2. **Razorpay Keys** (Payments ke liye)
   - https://dashboard.razorpay.com/ se keys lein
   - `.env` file mein `RAZORPAY_KEY_ID` aur `RAZORPAY_KEY_SECRET` set karein

Code automatically detect kar lega aur real APIs use karna shuru kar dega!

## File Changes Summary

### Backend Changes:
- `/workspace/api/.env` - Created with zero-cost config
- `/workspace/api/fastapi_app/app/workers/tasks.py` - Enhanced mock rank generation + SERP API placeholder
- Payment service already has mock mode support

### Frontend Changes:
- `/workspace/web/src/lib/api.js` - Added Razorpay checkout integration
- `/workspace/web/src/pages/PricingPage.jsx` - Added payment UI with billing cycle toggle

## Next Steps

1. Abhi ke liye: Test karein with mock data
2. Jab ready hon: Add real API keys
3. Deploy to production (Render, Railway, etc.)

