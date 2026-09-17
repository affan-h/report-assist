import os, json, sys, io, logging
from dataclasses import dataclass
from pathlib import Path
from core.config import default_config
from .schemas import GlobalAgentState

logger = logging.getLogger(default_config.SESS_LOG_NAME)

from pathlib import Path
from core.config import default_config

class SessionWorkspace:
    """
    Encapsulates all file system operations for a specific run.
    No other class should import 'config' for path manipulation.
    """
    def __init__(self, sess_id: str, run_id: str):
        self.sess_id = sess_id
        self.run_id = run_id

        # stored at session/{sess_id}
        self.session_base = Path(default_config.SESSION_FILEPATH) / sess_id
        self.data_dir = self.session_base / default_config.DATA_FILEPATH
        
        # stored at session/{sess_id}/{run_id}
        self.run_base = self.session_base / run_id
        self.figure_dir = self.run_base / default_config.FIGURE_FILEPATH
        self.model_dir = self.run_base / default_config.MODEL_FILEPATH
        
        # Ensure directories exist
        for d in [self.session_base, self.data_dir, self.figure_dir, self.model_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def get_log_path(self) -> Path:
        """Return the path to the session-scoped log file."""
        return self.run_base / default_config.SESS_LOG_FILENAME

    def save_json(self, data: dict, filename: str = default_config.FILENAME_AGENT_STATE):
        """Persist a JSON-serializable dict under the current run directory."""
        sess_log = logging.getLogger(default_config.SESS_LOG_NAME)

        filepath = os.path.join(self.run_base, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=True, default=str)
            sess_log.info(f"Agent State stored in {filepath}")
        except Exception as e:
            sess_log.error(f"Failed to save agent state: {e}")

    def list_figures(self) -> list[str]:
        """
        Returns a sorted list of string paths for all images 
        generated in the current run's figure directory.
        """
        import glob

        print(f"DEBUG: Looking for figures in: {self.figure_dir.resolve()}")
        
        if not self.figure_dir.exists():
            print("DEBUG: Directory does not exist.")
            return []
        
        all_files = list(self.figure_dir.glob("*"))
        print(f"DEBUG: Total {len(all_files)} files found in dir: {[f.name for f in all_files]}")
    
        image_paths = []
        for ext in default_config.VISUAL_ALLOWED_EXTENSIONS:
            pattern = os.path.join(self.figure_dir, ext)
            image_paths.extend(glob.glob(pattern))
        
        return [str(p) for p in image_paths]
    
    @property
    def graph_state_path(self) -> Path:
        """Path to the persistent JSON representation of the TaskGraph."""
        return self.session_base / default_config.FILENAME_TASK_GRAPH_STATE

    def save_graph_state(self, graph_dict: dict):
        """Persist the serialized task graph state to disk."""
        import json
        with open(self.graph_state_path, 'w', encoding='utf-8') as f:
            json.dump(graph_dict, f, indent=2, ensure_ascii=False)

    def load_graph_state(self) -> dict | None:
        """Load the persisted task graph state if it exists."""
        import json
        if not self.graph_state_path.exists():
            return None
        try:
            with open(self.graph_state_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
        
def load_prompt(agent_name: str, key: str=default_config.PROMPT_KEY_UNIVERSAL_SYSTEM) -> str:
    """Load a prompt string for the given agent and key from the prompt file."""
    file_path = default_config.FILENAME_SETTINGS
    try:
        with open(file_path, 'r') as f:
            prompt_data = json.load(f)
        result = prompt_data["prompts"][agent_name][key]
        return result
    except FileNotFoundError:
        logger.error(f"Error: The file was not found at {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error: Could not decode JSON from {file_path}. Check for syntax...")
        raise
    except KeyError as e:
        logger.error(f"Error: Missing key {e} in your JSON file.")
        raise

def increase_num_steps(state: GlobalAgentState):
    """Increment the tracked step counter in agent state if present."""
    try:
      state['num_steps'] += 1
    except Exception as e:
      pass

@dataclass
class ExecuteResult:
    """Structured result for code execution with success flag, message, and namespace."""
    success: bool
    message: str | None
    namespace: dict

class CodeExecutor:
    """A class to execute code and capture printed output."""
    def __init__(self, namespace: dict):
        """Create an executor with an isolated namespace for code execution."""
        self.namespace = namespace

    def execute(self, code: str) -> tuple[bool, str]:
        """Run arbitrary code in the executor namespace and capture stdout/stderr."""
        old_stdout = sys.stdout
        old_stderr = sys.stderr  
        redirected_output = io.StringIO()
        redirected_errors = io.StringIO()

        sys.stdout = redirected_output
        sys.stderr = redirected_errors

        exec_globals = self.namespace

        try:
            exec(code, exec_globals)

            stdout_content = redirected_output.getvalue()
            stderr_content = redirected_errors.getvalue()
            combined_output = stdout_content
            if stderr_content:
                combined_output += "\n--- Warnings/Errors ---\n" + stderr_content
            return True, combined_output 
        
        except Exception as e:
            stdout_content = redirected_output.getvalue()
            stderr_content = redirected_errors.getvalue()
            
            error_message = f"{type(e).__name__}: {e}"
            
            # Combine all captured info for the debug prompt
            combined_output = "--- Captured Stdout ---\n" + stdout_content
            combined_output += "\n--- Captured Stderr ---\n" + stderr_content
            combined_output += "\n--- Exception ---\n" + error_message
            
            return False, combined_output
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            if '__builtins__' in exec_globals:
                exec_globals.pop('__builtins__')

def write_response_txt(response: str, sess_id: str, run_id: str, filename: str = "response.txt", ensure_dir: bool = True) -> str:
    """
    Save `response` as a text file under {config.DATA_FILEPATH}{sess_id}/{run_id}/filename.
    """
    dest_dir = Path(os.path.join(default_config.SESSION_FILEPATH,sess_id,run_id))
    if ensure_dir:
        dest_dir.mkdir(parents=True, exist_ok=True)
    filepath = dest_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(response)
    logger.info(f"Saved response to {filepath}")
    return str(filepath)

def comment_block(text: str, prefix: str = "# ") -> str:
    """Prefix each line of text with the given comment marker."""
    lines = text.splitlines()
    out_lines = [(prefix + line) if line.strip() else prefix.rstrip() for line in lines]
    return "\n".join(out_lines)

def write_with_commented_instructions(path: str, instructions: str, marker: str = "# --- INSTRUCTIONS ---"):
    """Append instructions to a file with comment markers and delimiters."""
    commented = comment_block(instructions)
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + marker + "\n")
        f.write(commented + "\n")
        f.write(marker.replace("INSTRUCTIONS", "END_INSTRUCTIONS") + "\n")