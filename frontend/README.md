# Alpha Kite Max - Frontend

Real-time trading dashboard built with Next.js 15, displaying equity data with technical indicators (SMA9, Session VWAP).

## Features

- **Real-time Data Visualization**: Interactive charts with minute-level granularity
- **Technical Indicators**: 
  - 9-period Simple Moving Average (SMA9)
  - Session Volume Weighted Average Price (VWAP)
- **Cross Detection**: Automatic detection and display of SMA9/VWAP crossover signals
- **Date Navigation**: Browse historical data with previous/next day navigation
- **Market Hours Highlighting**: Visual distinction between market hours and pre/post-market
- **EST Clock**: Real-time clock showing current EST time with millisecond precision
- **Responsive Design**: Modern UI with Tailwind CSS, optimized for desktop and mobile

## Tech Stack

- **Framework**: [Next.js 15.0](https://nextjs.org) (App Router)
- **Language**: [TypeScript 5.x](https://www.typescriptlang.org)
- **Styling**: [Tailwind CSS 3.x](https://tailwindcss.com)
- **Charts**: [Recharts 2.x](https://recharts.org) (React wrapper for D3.js)
- **Database**: [Supabase](https://supabase.com) (PostgreSQL)
- **State Management**: React Hooks (useState, useEffect)
- **Date Handling**: [date-fns](https://date-fns.org), [date-fns-tz](https://github.com/marnusw/date-fns-tz)
- **Date Picker**: [react-datepicker](https://reactdatepicker.com)

## Getting Started

### Prerequisites

- Node.js 18.x or higher
- npm or yarn
- Supabase account and project

### Installation

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   # or
   yarn install
   ```

3. **Configure environment variables:**
   ```bash
   cp ../.env.example .env.local
   ```

   Edit `.env.local` with your Supabase credentials:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
   ```

   **Note**: The `NEXT_PUBLIC_` prefix makes these variables available in the browser. The Anon Key is safe to expose publicly (read-only access enforced by Row-Level Security).

4. **Run the development server:**
   ```bash
   npm run dev
   ```

5. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── page.tsx           # Home page (dashboard)
│   │   ├── layout.tsx         # Root layout
│   │   ├── globals.css        # Global styles
│   │   └── favicon.ico
│   ├── components/            # React components
│   │   ├── Dashboard.tsx      # Main dashboard container
│   │   ├── EquityChart.tsx    # Line chart with price/indicators
│   │   ├── SignalsDashboard.tsx # Cross signals table
│   │   ├── ESTClock.tsx       # Real-time EST clock
│   │   ├── DateNavigator.tsx  # Date navigation controls
│   │   └── ...
│   ├── contexts/              # React contexts
│   │   └── SupabaseContext.tsx # Supabase client provider
│   └── lib/                   # Utilities and configs
│       ├── supabase.ts        # Supabase client initialization
│       ├── utils.ts           # Helper functions
│       └── ...
├── public/                    # Static assets
│   └── *.svg
├── package.json              # Dependencies and scripts
├── tsconfig.json             # TypeScript configuration
├── tailwind.config.ts        # Tailwind CSS configuration
├── next.config.ts            # Next.js configuration
└── eslint.config.mjs         # ESLint configuration
```

## Key Components

### Dashboard (`src/components/Dashboard.tsx`)

Main container component that:
- Fetches equity data and indicators from Supabase
- Implements pagination (1000 rows per request)
- Provides date navigation (previous/next day, date picker)
- Polls for new data every 60 seconds during market hours
- Detects SMA9/VWAP crossovers

**Props**: None (manages its own state)

### EquityChart (`src/components/EquityChart.tsx`)

Interactive line chart displaying:
- Price (close)
- SMA9 indicator
- VWAP indicator
- Cross markers at intersection points
- Market hours highlighting (9:30 AM - 4:00 PM ET)

**Props**:
- `data`: Array of data points with timestamp, price, sma9, vwap
- `crosses`: Array of detected cross events

### SignalsDashboard (`src/components/SignalsDashboard.tsx`)

Table of SMA9/VWAP cross signals with:
- Time (formatted in 12-hour AM/PM)
- Value (price at cross)
- Direction (up/down)

**Props**:
- `crosses`: Array of cross events

### ESTClock (`src/components/ESTClock.tsx`)

Real-time clock showing current EST time with millisecond precision.

**Format**: `HH:MM:SS:MS` (12-hour with AM/PM)

**Update Frequency**: 100ms

## Data Flow

```
1. User loads dashboard
   ↓
2. Dashboard component mounts
   ↓
3. Fetch initial data from Supabase (equity_data + indicators)
   ↓
4. Join tables on (ticker, timestamp)
   ↓
5. Detect SMA9/VWAP crosses
   ↓
6. Render EquityChart + SignalsDashboard
   ↓
7. Set interval: Poll for new data every 60 seconds
   ↓
8. On new data: Update chart and signals
```

## Supabase Integration

### Tables Queried

**`equity_data`**:
- Columns: `ticker`, `timestamp`, `price`, `volume`
- Index: `(ticker, timestamp)` for fast queries

**`indicators`**:
- Columns: `ticker`, `timestamp`, `sma9`, `vwap`
- Index: `(ticker, timestamp)` for fast queries

### Query Example

```typescript
const { data, error } = await supabase
  .from('equity_data')
  .select('timestamp, price, volume')
  .eq('ticker', 'QQQ')
  .gte('timestamp', startDate)
  .lte('timestamp', endDate)
  .order('timestamp', { ascending: true });
```

### Row-Level Security (RLS)

- All tables have RLS enabled
- Anon Key has read-only access (SELECT only)
- No authentication required for viewing data

## Development

### Available Scripts

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint

# Run linter and auto-fix issues
npm run lint:fix
```

### TypeScript

This project uses strict TypeScript:
- All components are type-safe
- Interfaces for data models
- No `any` types (enforced by ESLint)

### ESLint Configuration

Configured with:
- `next/core-web-vitals` (Next.js recommended rules)
- TypeScript ESLint rules
- React Hooks rules

### Styling with Tailwind

Tailwind CSS is configured with custom colors and utilities. See `tailwind.config.ts` for customizations.

**Common patterns:**
```tsx
// Responsive layout
<div className="flex flex-col md:flex-row gap-4">

// Dark mode support (if enabled)
<div className="bg-white dark:bg-gray-800">

// Custom colors (if defined)
<button className="bg-primary text-white hover:bg-primary-dark">
```

## Deployment

### Vercel (Recommended)

1. **Push to GitHub:**
   ```bash
   git push origin main
   ```

2. **Import project in Vercel:**
   - Connect your GitHub repository
   - Select `frontend` as the root directory
   - Vercel will auto-detect Next.js configuration

3. **Configure environment variables:**
   In Vercel dashboard → Settings → Environment Variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

4. **Deploy:**
   Vercel will automatically build and deploy on every push to `main`.

**Build Settings:**
- Framework Preset: Next.js
- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: `.next`

### Other Platforms

This Next.js app can also be deployed to:
- **Netlify**: Use Next.js plugin
- **AWS Amplify**: Select Next.js framework
- **Cloudflare Pages**: Supports Next.js
- **Self-hosted**: Use `npm start` after `npm run build`

## Performance Optimizations

### Implemented

- **Static generation** for layout components
- **Client-side data fetching** for dynamic content (real-time data)
- **Memoized calculations** for chart data processing
- **Debounced navigation** to prevent excessive re-renders
- **Paginated queries** (1000 rows at a time) to reduce bandwidth

### Future Improvements

- **Incremental Static Regeneration (ISR)** for historical data pages
- **React Query** for better data caching and invalidation
- **Virtual scrolling** for large datasets (10,000+ data points)
- **WebSocket subscriptions** for real-time updates (Supabase Realtime)
- **Service Worker** for offline support

## Troubleshooting

### Data not loading

1. Check Supabase connection in browser console
2. Verify `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set
3. Ensure RLS policies allow read access with Anon Key
4. Check backend is running and populating data

### Chart not rendering

1. Ensure data has `timestamp`, `price`, `sma9`, `vwap` fields
2. Check for JavaScript errors in browser console
3. Verify Recharts is installed: `npm list recharts`

### Slow performance

1. Reduce query date range (fewer data points)
2. Check network tab for slow API calls
3. Consider implementing pagination or virtual scrolling
4. Verify Supabase indexes exist on `(ticker, timestamp)`

## Security

⚠️ **Never commit** `.env.local` to Git!

See [SECURITY.md](../SECURITY.md) for:
- Environment variable setup
- Supabase security best practices
- RLS configuration
- Credential management

**Frontend Security Checklist:**
- [ ] `.env.local` is in `.gitignore`
- [ ] Only `NEXT_PUBLIC_*` variables are exposed to browser
- [ ] Service Role Key is NEVER used in frontend
- [ ] RLS policies are enabled on all tables
- [ ] Anon Key has read-only access

## Learn More

### Next.js Resources

- [Next.js Documentation](https://nextjs.org/docs) - Learn about Next.js features and API
- [Learn Next.js](https://nextjs.org/learn) - Interactive Next.js tutorial
- [Next.js GitHub Repository](https://github.com/vercel/next.js)

### Supabase Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase JavaScript Client](https://supabase.com/docs/reference/javascript)
- [Row-Level Security](https://supabase.com/docs/guides/auth/row-level-security)

### Other Resources

- [Recharts Documentation](https://recharts.org/en-US/api)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## License

MIT - See [LICENSE](../LICENSE) for details.
