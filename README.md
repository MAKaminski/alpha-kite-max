# Alpha Kite Max

Trading dashboard with real-time equity data visualization featuring SMA9 and Session VWAP indicators.

## Features

- Real-time equity data display (default: QQQ)
- 9-period Simple Moving Average (SMA9)
- Session Volume Weighted Average Price (VWAP)
- Minute-level granularity
- Modern, responsive UI

## Tech Stack

- **Frontend**: Next.js 15 with TypeScript, Tailwind CSS, Recharts
- **Backend**: Supabase
- **Deployment**: Vercel

## Getting Started

### Prerequisites

- Node.js 18+
- Supabase account
- Vercel account (for deployment)

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/MAKaminski/alpha-kite-max.git
cd alpha-kite-max
```

2. Install dependencies:
```bash
cd frontend
npm install
```

3. Configure environment variables:
```bash
cp ../env.example frontend/.env.local
```

Edit `frontend/.env.local` and add your Supabase credentials:
```
NEXT_PUBLIC_SUPABASE_URL=your-supabase-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

4. Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Supabase Setup

### Applying Migrations

The database schema is managed through Supabase migrations.

**Option 1: Using Supabase CLI** (Recommended)
```bash
# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref xwcauibwyxhsifnotnzz

# Apply migrations
supabase db push
```

**Option 2: Manual via SQL Editor**

In your Supabase dashboard → SQL Editor, run the migration file:
```bash
supabase/migrations/20251015151016_create_equity_and_indicators_tables.sql
```

This creates:
- `equity_data` table with ticker, timestamp, price, volume
- `indicators` table with ticker, timestamp, sma9, vwap
- Indexes on (ticker, timestamp) for performance
- Row-Level Security (RLS) policies

## Deployment

### Vercel

1. Push your code to GitHub
2. Import the project in Vercel
3. Configure environment variables in Vercel dashboard
4. Deploy

The project is configured to automatically deploy the `frontend` directory.

## Backend Services

The Python backend downloads equity data from Schwab and loads it into Supabase.

### Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Usage
```bash
# Test connections
python main.py --test-connections

# Download data for QQQ (5 days)
python main.py --ticker QQQ --days 5
```

See `backend/README.md` for detailed documentation.

## Project Structure

```
alpha-kite-max/
├── frontend/          # Next.js application
│   ├── src/
│   │   ├── app/       # App router pages
│   │   ├── components/# React components
│   │   └── lib/       # Utilities and configs
├── backend/           # Python services
│   ├── schwab/       # Schwab API integration
│   ├── tests/        # Test suites
│   └── main.py       # CLI entry point
├── supabase/         # Database migrations
│   └── migrations/   # SQL migration files
├── shared/           # Shared types and configs
├── context/          # Project documentation
└── vercel.json       # Vercel configuration
```

## License

MIT

