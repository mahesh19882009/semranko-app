# RankCare - Next.js Frontend

## Project Setup
- Next.js 16 (Canary) with App Router
- Tailwind CSS v4
- React 19, Redux Toolkit, React-Redux
- API proxy to backend: http://localhost:4000

## Commands
- `npm run dev` — Start dev server on port 3000
- `npm run build` — Production build
- `npm run lint` — Run ESLint

## Structure
- `app/` — Next.js App Router pages and layouts
  - `app/app/` — Protected routes (auth guard + AppLayout)
  - `/dashboard`, `/projects`, `/keywords`, `/competitors` — Legacy redirects
- `src/` — Shared source code
  - `src/views/` — View components (migrated from react-router pages)
  - `src/components/` — UI components and layouts
  - `src/features/` — Redux Toolkit slices (6 domains)
  - `src/lib/` — API client and navigation compat layer
  - `src/utils/` — Utility functions (auth, date)
  - `src/config/` — Configuration files
  - `src/app/store.js` — Redux store configuration

## Navigation
- `src/lib/navigation.jsx` — React Router API compat layer for Next.js
  - `Link`, `Navigate`, `NavLink`, `useNavigate`, `useLocation`, `useSearchParams`

## Environment
- `.env.local`: `NEXT_PUBLIC_API_BASE_URL=http://localhost:4000/api`
