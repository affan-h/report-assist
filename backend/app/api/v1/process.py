import json, logging, os
import asyncio
from asyncio import Queue
from typing import Dict, Union, Optional, List
from core.config import default_config, AppSettings
# from core.config_user import
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, HTTPException,  UploadFile, File, Form, Request, Body
from app.services.agent import get_master_agent
from app.services.agent.utils import SessionWorkspace
from app.services.agent.schemas import MultiPersonaResponse
from functools import lru_cache

process_router = APIRouter()

SESSION_QUEUES: Dict[str, Queue] = {}

logger = logging.getLogger(__name__)

DEBUGGING = False

@lru_cache()
def get_settings():
    return AppSettings()

def generate_id(prefix: str | None = None) -> str:
    import uuid
    """
    Generate a shorter run ID using first 8 characters of UUID.
    
    Args:
        prefix: Prefix for the run ID
        
    Returns:
        Generated run ID string
        
    Example:
        - generate_run_id_short(prefix='run') -> "run_a1b2c3d4"
    """
    if not prefix:
        return uuid.uuid4().hex[:default_config.UUID_LEN]
    return f"{prefix}_{uuid.uuid4().hex[:default_config.UUID_LEN]}"

async def run_agent_work(
        master_agent, 
        human_input: str, 
        file_names: List[str],
        workspace: SessionWorkspace,
        analyze_only: bool,
        q: Queue
    ):
    loop = asyncio.get_running_loop()

    def send_sse(payload: any, event_type: str="progress"):
        data = json.dumps({"type": event_type, "message": payload})
        loop.call_soon_threadsafe(q.put_nowait, data)

    async def heartbeat(queue: Queue):
        """Sends a ping every config.KEEPALIVE_INTERVAL seconds to keep the connection alive."""
        try:
            while True:
                await asyncio.sleep(default_config.KEEPALIVE_INTERVAL)
                ping_data = json.dumps({"type": "ping", "message": "still-processing"})
                loop.call_soon_threadsafe(queue.put_nowait, ping_data)
        except asyncio.CancelledError:
            # Task was explicitly cancelled, exit gracefully
            pass
        except Exception as e:
            print(f"Heartbeat stopping: {e}")
            
    heartbeat_task = asyncio.create_task(heartbeat(q))
            
    try:
        if DEBUGGING:
            result: MultiPersonaResponse = await asyncio.to_thread(
                master_agent.run_request_demo,
                human_input,
                file_names,
                workspace,
                send_sse
            )
        else:
            result: MultiPersonaResponse = await asyncio.to_thread(
                master_agent.run_request,
                human_input,
                file_names,
                workspace,
                analyze_only,
                send_sse
            )
            
        serializable_result = jsonable_encoder(result)
        
        final_data = json.dumps({"type": "response", "message": serializable_result})
        await q.put(final_data)

    except Exception as e:
        error_data = json.dumps({"type": "error", "message": str(e)})
        await q.put(error_data)
    
    finally:
        heartbeat_task.cancel() # Stop the heartbeat task
        try:
            # Wait for heartbeat to fully cancel
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        await q.put("[DONE]")

@process_router.post("")
async def start_processing(
        request: Request,
        prompt: str = Form(...),
        analyze_only: bool = False,
        session_id: Optional[str] = Form(None),
        files: List[UploadFile] = File(default=[])
    ):
    from pathlib import Path

    if not DEBUGGING and session_id:
        potential_path = Path(default_config.SESSION_FILEPATH) / session_id
        if not potential_path.exists():
            logger.warning(f"Session {session_id} not found, creating new.")
            session_id = generate_id(prefix='sess')
    else:
        session_id = generate_id(prefix='sess')
    
    if DEBUGGING:
        session_id = "sess_1c14d158"
        run_id = "run_da02597c"
    else:
        run_id = generate_id(prefix='run')
    
    q = Queue()
    SESSION_QUEUES[session_id] = q

    workspace = SessionWorkspace(session_id, run_id)
    file_names: List[str] = []

    # Save new files (if any)
    if not DEBUGGING and files:
        try:
            for file in files:
                if not file.filename: continue
                
                file_path = workspace.figure_dir / Path(file.filename).name if analyze_only else workspace.data_dir / Path(file.filename).name
                
                # Async read/write
                content = await file.read()
                with open(file_path, "wb") as f:
                    f.write(content)
                file_names.append(file.filename)
        except Exception as e:
            SESSION_QUEUES.pop(session_id, None)
            raise HTTPException(status_code=500, detail=f"File save failed: {e}")
        
    master_agent = get_master_agent(get_settings())
    asyncio.create_task(
        run_agent_work(
            master_agent,
            prompt,
            file_names,
            workspace,
            analyze_only,
            q
        )
    )

    # Return the session_id
    return JSONResponse({"status": "success", "session_id": session_id})


@process_router.get("/events/{session_id}")
async def stream_progress(request: Request, session_id: str):
    async def event_generator():
        q = SESSION_QUEUES.get(session_id)
        
        if not q:
            # Send an error event then close
            err = json.dumps({"type": "error", "message": "Session expired or invalid"})
            yield f"data: {err}\n\n"
            yield f"data: [DONE]\n\n"
            return
        
        yield f": connected\n\n"
        
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info(f"Client {session_id} disconnected")
                    break
                
                try:
                    # Wait for message with timeout to allow checking disconnect status
                    msg = await asyncio.wait_for(q.get(), timeout=1.0)
                    
                    if msg == "[DONE]":
                        yield f"data: [DONE]\n\n"
                        break
                    
                    yield f"data: {msg}\n\n"
                    q.task_done()
                
                except asyncio.TimeoutError:
                    # Just loop back to check connection status
                    continue
                    
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for {session_id}")
        
        finally:
            # Cleanup: Remove the queue to free memory
            # In a chat app, we remove it because the response is done.
            # The next POST /start will create a NEW queue.
            SESSION_QUEUES.pop(session_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

from pathlib import Path

CONFIG_PATH = Path(default_config.FILENAME_SETTINGS)
DEFAULT_PERSONAS = [
    {"role": "The Optimistic", "icon": "📈", "bias_instruction": "Focus strictly on growth metrics, upside potential, and opportunities. Highlight positive momentum and ignore risks."},
    {"role": "The Pessimistic", "icon": "📉", "bias_instruction": "Focus strictly on liabilities, downside risks, cost pressures, and volatility. Be skeptical of growth metrics."},
    {"role": "The Skeptic", "icon": "🕵️", "bias_instruction": "Doubt data integrity and methodology. Look for anomalies, small sample sizes, and spurious correlations."}
]

# Default config to fall back on if file doesn't exist
DEFAULT_PROMPTS = {
  "analysis": {
    "system_prompt": "You are an expert Data Scientist. Analyze the provided diagrams through your assigned persona lens.\nSupport your specific interpretation using the visual evidence provided. When discussing a specific insight that is visualized in a chart or diagram, insert the chart/diagram immediately after the explanation using the format <<<filename>>>. Example: Here is the Q1 performance breakdown.\n <<<sales_q1.png>>>\n\nTask:\n1. 'narrative': Write a persuasive argument from your persona's perspective based on these diagrams.\n2. 'evidence': Select the diagrams that support your argument and explain WHY.",
    "prompt_user_instruction": "Task:\n1. 'narrative': Write a persuasive argument based on these diagrams.\n2. 'evidence': Select the diagrams that support your argument and explain WHY.",
    "system_prompt_forecast": "You are given a role. Provide a forward-looking forecast of future trends based on the diagram evidence through your persona lens."
  },
  "code": {
    "system_prompt": "You are an expert data science code generator. Given a task instruction, generate clean, executable Python code snippets. Always import required packages using conventions for standard libraries like pandas, matplotlib, seaborn, scikit-learn, and scipy. Save all intermediate datasets to {data_dir}, save all visualizations and charts to {figure_dir}, and save trained models to {model_dir}. Do not attempt to install packages using pip. Stored information in 'agent_state' should only include filepaths, metrics, and short summaries—never large in-memory dataframes.",
    "system_prompt_replan": "The previous code plan failed. Review the execution error in the human message, identify the root cause, and generate a corrected executable plan to complete the goal."
  },
  "master": {
    "system_prompt": "You are an expert data science workflow planner. Given a user goal and uploaded datasets, decompose the project into a structured sequence of data science tasks (such as Data Loading, Cleaning/EDA, Modeling, and Visualization). Keep the task graph focused, with a maximum of 5 TaskNodes.",
    "system_prompt_refine": "Update the existing workflow graph to address new requirements or resolve execution failures. You can add, modify, or remove nodes.",
    "system_prompt_ans": "You are the Lead Data Scientist and Neutral Arbitrator. You receive analysis insights and generated figures from your team. Synthesize these inputs into a balanced, clear, and comprehensive answer in plain English. Reference charts using <<<filename>>> when discussing corresponding insights.",
    "system_prompt_user_req": "You are a technical product owner. Summarize the user data analysis request into clear, actionable analytical requirements."
  }
}

@process_router.get("/config/settings")
def get_config_prompts():
    """
    Reads the agent configuration from disk. 
    If file is missing, creates it with defaults.
    """
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Create full default structure
        default_data = {
            "prompts": DEFAULT_PROMPTS,
            "personas": DEFAULT_PERSONAS,
            "llm_config": {
                "LLM_PROVIDER": "gemini",
                "GEMINI_MODEL": "gemini-2.5-flash",
                "TIMEOUT": 300,
                "TEMPERATURE": 0.3,
                "MAX_RETRIES": 2
            },
            "graph_config": {
                "ACTION_GRAPH_MAX_RETRIES": 5,
                "TASK_GRAPH_MAX_RETRIES": 3
            }
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2)
        return default_data

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
    
@process_router.post("/config/settings")
def update_config_prompts(config: dict = Body(...)):
    """
    Overwrites the JSON file with the new configuration from the frontend.
    """
    try:
        # Ensure directory exists
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            
        return {"status": "success", "message": "Configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")
    
STORAGE_BASE_PATH = "session"
@process_router.get("/storage/{session_id}/{run_id}/{filename}")
async def get_diagram(session_id: str, run_id: str, filename: str):
    # Construct the path safely
    file_path = os.path.join(STORAGE_BASE_PATH, session_id, run_id, "figures", filename)
    
    # 1. Security Check: Prevent directory traversal (optional but recommended)
    if not os.path.abspath(file_path).startswith(os.path.abspath(STORAGE_BASE_PATH)):
        raise HTTPException(status_code=400, detail="Invalid path")

    # 2. Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Diagram not found")

    return FileResponse(
        file_path
    )