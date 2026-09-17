# report-assist Backend

The core agentic server powering **report-assist**. Built with **FastAPI**, **LangChain**, **LangGraph**, and **Google Gemini**, this service automates data science workflows and synthesizes objective, unbiased reports.

## Features

- **LangGraph StateGraph Engine**: Multi-agent workflow orchestrating planning, code generation, execution, visual curation, persona debate, bias evaluation, and neutral synthesis.
- **Self-Healing Code Execution**: Automatically inspects execution tracebacks (`stderr`) and loops back to regenerate corrected code snippets.
- **Multimodal Visual Analysis (Gemini Vision)**: Directly examines rendered charts and plots through distinct cognitive perspectives (**The Optimistic**, **The Pessimistic**, and **The Skeptic**).
- **Semantic Bias Quantification**: Employs SentenceTransformer vector embeddings and cosine distance to quantify subjective bias and compute an empirical Neutrality Index.
- **Live SSE Streaming**: Streams real-time DAG state, execution progress, and synthesized responses to the frontend.

## Quickstart

### 1. Prerequisites
- Python 3.11 (recommended)
- A Google Gemini API Key (free tier available at [Google AI Studio](https://aistudio.google.com/))

### 2. Setup Virtual Environment & Dependencies
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

*(Alternatively, if using Poetry: `poetry install`)*

### 3. Configure Environment
Copy `.env.example` to `.env` and insert your Gemini API key:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
GEMINI_API_KEY="your_api_key_here"
```

### 4. Run the Server
```bash
python3 main.py --env local --debug
```
The server will start at `http://0.0.0.0:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.
