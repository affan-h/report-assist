# report-assist Frontend

The interactive user interface for **report-assist**, built with **Next.js 16 (App Router)**, **React 19**, **Tailwind CSS**, and **React Flow (@xyflow/react)**.

## Features

- **Interactive TaskGraph Visualizer**: Real-time DAG workflow visualization powered by React Flow and Dagre layout, displaying live node states (`pending`, `running`, `success`, `failed`).
- **Multi-Persona Perspective Grid**: Card grid displaying contrasting viewpoints from **The Optimistic**, **The Pessimistic**, and **The Skeptic**, complete with the calculated Neutrality Index.
- **Bias Spectrum Bar**: Visual vector projection bar illustrating the degree of optimism vs. pessimism on a continuous scale.
- **Artifact Viewer HUD**: Zoomable diagram inspection with AI-generated visual insight callouts.
- **Live Configuration Modal**: On-the-fly tuning of prompts, Gemini model parameters, and persona definitions.

## Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment
Copy `.env.example` to `.env.local`:
```bash
cp .env.example .env.local
```

### 3. Start Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.
