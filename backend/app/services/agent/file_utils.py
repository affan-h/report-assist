import io
import base64
import logging
import mimetypes
import pandas as pd
from pathlib import Path
from typing import List, Dict, Union, Any

logger = logging.getLogger(__name__)

class FileUtils:
    """
    Utilities for reading, summarizing, and formatting files for LLM consumption.
    Decoupled from session logic and configuration.
    """

    @staticmethod
    def _read_text_safe(file_path: Path) -> str:
        """Reads text file with error handling."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return f"Error reading file: {str(e)}"

    @staticmethod
    def _summarize_csv(file_path: Path) -> str:
        """Returns the df.info() summary instead of raw rows to save tokens."""
        try:
            df = pd.read_csv(file_path)
            buffer = io.StringIO()
            df.info(buf=buffer)
            return buffer.getvalue()
        except Exception as e:
            logger.warning(f"Failed to generate CSV summary for {file_path}. Fallback to text read.")
            # Fallback: Read first 1000 chars if pandas fails
            content = FileUtils._read_text_safe(file_path)
            return f"Error reading CSV structure. Raw content preview:\n{content[:1000]}"

    @staticmethod
    def _encode_image(file_path: Path) -> str:
        """Encodes an image to base64 string."""
        try:
            with open(file_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image {file_path}: {e}")
            return ""

    @staticmethod
    def format_files_for_llm(file_names: List[str], base_dir: Path) -> List[Dict[str, Any]]:
        """
        Iterates through filenames, detects types, and formats them for the LLM.
        
        Args:
            file_names: List of filenames (e.g., ['data.csv', 'chart.png'])
            base_dir: The directory path object where files reside (from Workspace)
        
        Returns:
            A list of message parts compatible with LangChain/OpenAI content blocks.
        """
        message_parts = []

        for filename in file_names:
            file_path = base_dir / filename
            
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue

            try:
                # Guess mime type
                mime_type, _ = mimetypes.guess_type(file_path)
                
                # Case 1: Images
                if mime_type and mime_type.startswith('image'):
                    encoded_img = FileUtils._encode_image(file_path)
                    if encoded_img:
                        message_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded_img}"
                            }
                        })

                # Case 2: CSV Data
                elif mime_type == 'text/csv' or filename.endswith('.csv'):
                    dataset_info = FileUtils._summarize_csv(file_path)
                    message_parts.append({
                        "type": "text",
                        "text": f"Dataset Info ({filename}):\n{dataset_info}"
                    })

                # Case 3: Text / Code / JSON
                else:
                    # Default handling for text-based files
                    content = FileUtils._read_text_safe(file_path)
                    formatted_content = (
                        f"\n---\n"
                        f"File Name: {filename}\n"
                        f"Content:\n{content}\n"
                        f"---\n"
                    )
                    message_parts.append({
                        "type": "text",
                        "text": formatted_content
                    })

            except Exception as e:
                logger.error(f"Error processing {filename} in FileUtils: {e}")

        return message_parts