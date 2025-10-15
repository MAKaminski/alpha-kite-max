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

## Supabase Schema

The application expects the following tables:

### equity_data
```sql
CREATE TABLE equity_data (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR(10) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  price DECIMAL(10, 2) NOT NULL,
  volume BIGINT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_equity_ticker_timestamp ON equity_data(ticker, timestamp);
```

### indicators
```sql
CREATE TABLE indicators (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR(10) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  sma9 DECIMAL(10, 2),
  vwap DECIMAL(10, 2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_indicators_ticker_timestamp ON indicators(ticker, timestamp);
```

## Deployment

### Vercel

1. Push your code to GitHub
2. Import the project in Vercel
3. Configure environment variables in Vercel dashboard
4. Deploy

The project is configured to automatically deploy the `frontend` directory.

## Project Structure

```
alpha-kite-max/
├── frontend/          # Next.js application
│   ├── src/
│   │   ├── app/       # App router pages
│   │   ├── components/# React components
│   │   └── lib/       # Utilities and configs
├── backend/           # Python services (future)
├── shared/            # Shared types and configs
├── context/           # Project documentation
└── vercel.json        # Vercel configuration
```

## License

MIT

