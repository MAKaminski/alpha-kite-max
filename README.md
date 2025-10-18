# Alpha Kite Max

Trading dashboard with real-time equity data visualization featuring SMA9 and Session VWAP indicators.

## License

This project is licensed under the MIT License with commercial use restrictions. See [LICENSE](LICENSE) for details.

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
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

**Note**: This project uses `uv` for faster Python package management. If you don't have `uv` installed, run:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
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
├── frontend/               # Next.js application
│   ├── src/
│   │   ├── app/           # App router pages
│   │   ├── components/    # React components
│   │   ├── contexts/      # React contexts
│   │   └── lib/           # Utilities and configs
├── backend/               # Python services
│   ├── schwab_integration/# Schwab API integration
│   │   ├── client.py     # API client wrapper
│   │   ├── downloader.py # Data downloader
│   │   └── streaming.py  # Real-time streaming
│   ├── models/           # Pydantic data models
│   ├── tests/            # Test suites
│   │   ├── integration/  # Integration tests
│   │   ├── test_schwab/  # Schwab API tests
│   │   └── test_supabase/# Database tests
│   ├── sys_testing/      # System testing & utilities
│   │   ├── OAuth scripts # Authentication helpers
│   │   └── Diagnostic tools
│   ├── lambda/           # AWS Lambda deployment
│   ├── main.py           # CLI entry point
│   └── etl_pipeline.py   # ETL orchestration
├── infrastructure/        # Terraform IaC
│   ├── lambda.tf         # Lambda function config
│   ├── cloudwatch_alarms.tf
│   └── secrets.tf        # AWS Secrets Manager
├── supabase/             # Database migrations
│   └── migrations/       # SQL migration files
├── shared/               # Shared TypeScript types
├── context/              # Project documentation
│   └── docs/            # Detailed guides
├── SECURITY.md          # Security policy
└── vercel.json          # Vercel configuration
```

## Documentation

### Core Documentation
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Complete system architecture and technical specifications
- **[SECURITY.md](./SECURITY.md)** - Security policy and credential management best practices

### Setup & Deployment
- **[Quick Start Guide](./context/docs/QUICKSTART_AWS.md)** - Get up and running in 15 minutes
- **[Deployment Guide](./context/docs/DEPLOYMENT.md)** - Production deployment instructions
- **[AWS Deployment](./context/docs/DEPLOYMENT_AWS.md)** - Detailed AWS Lambda setup
- **[Vercel Deployment](./context/docs/VERCEL_DEPLOYMENT.md)** - Frontend deployment guide

### Development Guides
- **[Backend README](./backend/README.md)** - Python backend setup and usage
- **[Frontend README](./frontend/README.md)** - Next.js frontend development
- **[Infrastructure README](./infrastructure/README.md)** - Terraform configuration

### Status & Progress
- **[Implementation Status](./context/docs/IMPLEMENTATION_STATUS.md)** - Current feature status
- **[Progress Summary](./context/docs/PROGRESS_SUMMARY.md)** - Latest development progress
- **[Supabase Migrations](./context/docs/SUPABASE_MIGRATIONS.md)** - Database schema history

## License

MIT

