# Sentinel DB &middot; React 18 + TypeScript + Tailwind CSS Frontend

Modern, high-performance React application for **Sentinel DB / Query Trap**, providing:
1. **SOC Analyst Operations Portal** (`/` or `?view=dashboard`): Live authenticated Socket.IO telemetry stream, interactive AST query analyzer, SVG risk score sparklines, and **DOM Virtualization** for handling high-volume traffic without browser lag.
2. **Customer Storefront** (`?view=storefront`): Vibrant *Harbor & Pine* artisanal goods e-commerce storefront with modular `<ProductCard />`, `<SearchBar />`, and `<HeroBanner />` components. Implements the **OpSec rule** that transparently diverts attackers to the honeypot without warning alerts.
3. **Internal Corporate Honeypot** (`?view=honeypot` or `?handoff=<token>`): Authentic *Northstar Enterprise Data Systems* internal data explorer with confidential dataset tabs, realistic metadata, and zero giveaway banners.

---

## Architecture & Tech Stack

- **Framework**: React 18.3+ with [Vite](https://vitejs.dev/)
- **Language**: TypeScript (Strict Mode) with 100% typed Flask API contracts
- **Styling**: Tailwind CSS 3.4
- **Real-Time Telemetry**: `socket.io-client` with token-based authorization
- **Performance Optimization**: Dedicated `useVirtualList` hook for constant O(1) DOM footprint during DDoS / high-volume attacks
- **Icons**: `lucide-react`

---

## Quickstart

### 1. Start the Python Backend Demo Services
From the repository root (`d:\Projects\Query_Trap`):
```powershell
python run.py
```
This boots the 3 Flask services on ports `5100` (SOC), `5200` (Storefront), and `5300` (Honeypot).

### 2. Run the React Development Server
In another terminal:
```powershell
cd frontend-react
npm run dev
```
Open **`http://localhost:3000/`** in your browser.

### 3. Production Build
```powershell
cd frontend-react
npm run build
```
Generates an optimized, tree-shaken static production bundle in `dist/`.

---

## API Adaptability (Frozen Backend Contracts)

The React frontend communicates directly with the existing, immutable Flask REST endpoints:
- `POST /api/query`: Real-time query inspection & threat routing
- `GET /api/events`: Persistent audit telemetry history from SQLite
- `GET /api/handoff/:token`: Single-use decoy handoff consumption
- `GET /api/decoy/records`: Dynamic honeytokens and decoy database records
- `GET /api/health`: Service health checks
