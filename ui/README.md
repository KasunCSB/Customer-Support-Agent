# Customer Support Agent UI

A production-ready React UI for the RAG-based AI customer support agent, built with Next.js 14+ and TypeScript.

## Features

- **Chat Interface**: Full-featured chat with conversation history, streaming responses, and source citations
- **Voice Interface**: Speech-to-text and text-to-speech powered by Web Speech API
- **Tools Panel**: System testing, document ingestion, and knowledge base management
- **Settings Page**: Configure LLM parameters, retrieval settings, and API keys
- **Dark Mode**: Full theme support with system preference detection
- **Session Management**: Persistent chat sessions with search and organization

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS with custom design system
- **Validation**: Zod for runtime type safety
- **Storage**: IndexedDB for client-side persistence
- **Icons**: Lucide React
- **Notifications**: Sonner

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API server running on port 8000

### Installation

```bash
# Navigate to UI directory
cd ui

# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

### Running the Backend

The UI requires the Python backend API server to be running:

```bash
# From project root
pip install fastapi uvicorn

# Start API server
python api_server.py
```

The backend will be available at `http://localhost:8000`.

## Project Structure

```
ui/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── api/               # API route handlers
│   │   ├── settings/          # Settings page
│   │   ├── tools/             # Tools page
│   │   ├── voice/             # Voice page
│   │   └── page.tsx           # Main chat page
│   ├── components/
│   │   ├── chat/              # Chat interface components
│   │   ├── layout/            # Navigation, Logo
│   │   ├── session/           # Session management
│   │   ├── ui/                # Reusable UI primitives
│   │   ├── voice/             # Voice interface components
│   │   └── providers/         # Context providers
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Utilities and API client
│   └── types/                 # TypeScript types and Zod schemas
├── public/                    # Static assets
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

## Design System

### Colors

- **Primary**: Blue (`#2563eb` - Blue 600)
- **Secondary**: Teal (`#0d9488` - Teal 600)
- **Accent**: Violet (`#7c3aed` - Violet 600)
- **Semantic**: Success (Green), Warning (Amber), Error (Red)

### Typography

- **Font**: Inter (Google Fonts)
- **Monospace**: JetBrains Mono for code blocks

### Components

All UI components are built with accessibility in mind:

- Full keyboard navigation
- ARIA labels and roles
- Focus management
- Screen reader support

## API Integration

The UI communicates with the backend through API routes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send chat message (streaming) |
| `/api/query` | POST | Single query without context |
| `/api/stats` | GET | Get system statistics |
| `/api/ingest` | POST | Ingest documents |
| `/api/clear` | POST | Clear vector store |
| `/api/test` | POST | Run system tests |

## Configuration

### Environment Variables

Create a `.env.local` file:

```env
# Backend API URL
BACKEND_URL=http://localhost:8000
```

### Tailwind

The design system is configured in `tailwind.config.ts` with custom:
- Colors
- Animations
- Box shadows
- Typography

## Scripts

```bash
npm run dev       # Start development server
npm run build     # Build for production
npm run start     # Start production server
npm run lint      # Run ESLint
npm run format    # Format with Prettier
```

## Browser Support

- Chrome 90+
- Firefox 90+
- Safari 14+
- Edge 90+

Voice features require Web Speech API support.

## License

MIT
