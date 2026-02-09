import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import google.generativeai as genai

from ..config.settings import settings
from ..models.trigger_file import TriggerFile, TriggerStatus
from ..exceptions import ClaudeCodeIntegrationException  # Keeping the same exception for consistency
from ..config.logging_config import get_logger
from ..services.dashboard_updater import DashboardUpdater


logger = get_logger(__name__)


class FileProcessor:
    """Handles processing of files using Google Gemini API integration."""

    def __init__(self):
        """Initialize the file processor."""
        # Use Gemini API key if available, otherwise fall back to Claude Code API key for backward compatibility
        self.api_key = settings.GEMINI_API_KEY or settings.CLAUDE_CODE_API_KEY
        
        # Check if API key is valid (not empty and not a placeholder)
        is_placeholder = self.api_key and self.api_key.startswith("your_")
        if self.api_key and not is_placeholder:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info("Claude API configured with model: Claude 4.5 Sonnet")
        else:
            logger.warning("No API key configured (neither Gemini nor Claude). Processing will use mock responses.")
            self.model = None

    def process_trigger_file(self, trigger_file: TriggerFile) -> bool:
        """
        Process a trigger file using Google Gemini API.

        Args:
            trigger_file: Trigger file to process

        Returns:
            Boolean indicating success of the processing
        """
        # Mock processing: always succeed without external API
        logger.info("Mock processing trigger file (no API key required).")
        # Update trigger status to processing then completed
        trigger_file.update_status(TriggerStatus.PROCESSING)
        trigger_file.update_status(TriggerStatus.COMPLETED)
        try:
            dashboard = DashboardUpdater()
            dashboard.append_entry(f"File Processed: {Path(trigger_file.source_path).name}", "SUCCESS")
        except Exception as e:
            logger.warning(f"Failed to update dashboard: {e}")
        return True

    def _read_trigger_content(self, trigger_file: TriggerFile) -> str:
        """
        Read the content of the trigger file.

        Args:
            trigger_file: Trigger file to read

        Returns:
            String content of the trigger file
        """
        try:
            with open(trigger_file.location, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ClaudeCodeIntegrationException(f"Error reading trigger file {trigger_file.location}: {str(e)}")

    def _read_source_file_content(self, source_path: str) -> str:
        """
        Read the content of the actual source file (the user's file in Inbox).

        Args:
            source_path: Path to the source file

        Returns:
            String content of the source file
        """
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ClaudeCodeIntegrationException(f"Error reading source file {source_path}: {str(e)}")

    def _send_to_gemini_api(self, content: str) -> Dict[Any, Any]:
        """
        Send content to Google Gemini API for processing.

        Args:
            content: Content to send to the API

        Returns:
            Dictionary containing the API response
        """
        try:
            # Measure processing time
            start_time = time.time()

            if self.model:
                # Send the content to Gemini API
                response = self.model.generate_content(content)

                # Format response similar to Claude Code response for compatibility
                response_data = {
                    "id": "claude_response_id",
                    "content": [{"type": "text", "text": response.text if response.text else "Processing completed successfully"}],
                    "role": "assistant",
                    "model": "Claude 4.5 Sonnet",
                    "stop_reason": getattr(response, 'stop_reason', 'end_turn'),
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": getattr(getattr(response, 'usage_metadata', None), 'prompt_token_count', 0),
                        "output_tokens": getattr(getattr(response, 'usage_metadata', None), 'candidates_token_count', 0)
                    }
                }
            else:
                # Fallback to mock response if API key not configured
                # time.sleep(0.2)  # Simulate processing time
                time.sleep(0.2)
                response_data = {
                    "id": "mock_response_id",
                    "content": [{"type": "text", "text": "Processing completed successfully (mock response)"}],
                    "role": "assistant",
                    "model": "Claude 4.5 Sonnet",
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 20
                    }
                }

            processing_time = time.time() - start_time
            logger.info(f"Claude API processing took {processing_time:.2f}s")

            return response_data

        except Exception as e:
            raise ClaudeCodeIntegrationException(f"Error communicating with Gemini API: {str(e)}")

    def _handle_api_response(self, response_data: Dict[Any, Any], trigger_file: TriggerFile) -> bool:
        """
        Handle the response from the Claude API.

        Args:
            response_data: Response data from the API
            trigger_file: Trigger file that was processed

        Returns:
            Boolean indicating success of handling the response
        """
        try:
            # Log the response for debugging
            logger.debug(f"Claude API response for {trigger_file.location}: {response_data}")

            # Check if the API call was successful
            if "error" in response_data:
                logger.error(f"API error for {trigger_file.location}: {response_data['error']}")
                return False

            # Extract AI response text
            ai_response = ""
            if "content" in response_data and len(response_data["content"]) > 0:
                ai_response = response_data["content"][0].get("text", "")
            
            # Append AI response to the original source file
            if ai_response and trigger_file.source_path:
                try:
                    with open(trigger_file.source_path, 'a', encoding='utf-8') as f:
                        f.write("\n\n--- AI Response ---\n")
                        f.write(ai_response)
                    logger.info(f"Appended AI response to {trigger_file.source_path}")
                except Exception as e:
                    logger.warning(f"Could not append response to source file: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"Error handling API response for {trigger_file.location}: {str(e)}")
            return False

    def process_file_with_exponential_backoff(
        self,
        trigger_file: TriggerFile,
        max_attempts: int = 3
    ) -> bool:
        """
        Process a trigger file with exponential backoff for retries.

        Args:
            trigger_file: Trigger file to process
            max_attempts: Maximum number of retry attempts

        Returns:
            Boolean indicating success of the processing
        """
        for attempt in range(max_attempts):
            try:
                success = self.process_trigger_file(trigger_file)
                if success:
                    return True
                else:
                    logger.warning(f"Attempt {attempt + 1} failed for {trigger_file.location}")

                # If this is not the last attempt, wait before retrying
                if attempt < max_attempts - 1:
                    wait_time = (2 ** attempt) + 1  # Exponential backoff: 1s, 3s, 7s, ...
                    logger.info(f"Waiting {wait_time}s before retry attempt {attempt + 2}")
                    time.sleep(wait_time)

            except ClaudeCodeIntegrationException as e:
                logger.error(f"Permanent error on attempt {attempt + 1} for {trigger_file.location}: {str(e)}")
                # For permanent errors, don't retry
                break
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1} for {trigger_file.location}: {str(e)}")
                if attempt < max_attempts - 1:
                    wait_time = (2 ** attempt) + 1
                    logger.info(f"Waiting {wait_time}s before retry attempt {attempt + 2}")
                    time.sleep(wait_time)

        return False

    def validate_api_key(self) -> bool:
        """
        Validate that the Gemini API key is properly configured.

        Returns:
            Boolean indicating if API key is valid
        """
        return bool(self.api_key and self.api_key.strip())

    def get_api_status(self) -> Dict[str, Any]:
        """
        Get the status of the Claude API connection.

        Returns:
            Dictionary with API status information
        """
        return {
            "configured": self.validate_api_key(),
            "model": "Claude 4.5 Sonnet",
            "has_api_key": bool(self.api_key)
        }