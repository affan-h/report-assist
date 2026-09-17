# LangGraph Data Analysis Runner

What it does

- Runs the LangGraph code to generate code and insights for data analysis workflows aimed at data scientists.

Required packages

- python3.10
- ipykernel

Getting started (macOS)

Copy and run these commands in your terminal:

```sh
# Create and activate virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# Install pip-tools and sync development requirements
pip install pip-tools
pip-sync dev-requirements.txt

# (Optional) If dev-requirements.txt is missing, install ipykernel directly
# pip install ipykernel

# (Optional) Set your OpenAI API key in the environment (replace with your key)
# export OPENAI_API_KEY="your_openai_api_key_here"
```

Quick usage

- Open and run the notebook: `langgraph.ipynb`.
- The notebook may prompt for your OPENAI_API_KEY (set as environment variable or enter when prompted).

Notes

- Ensure Python 3.10 is installed on your system.
- dev-requirements.txt should list development dependencies (e.g., ipykernel). If missing, create it or install ipykernel directly: `pip install ipykernel`.

Dependencies
[pip-tools](https://github.com/jazzband/pip-tools)
