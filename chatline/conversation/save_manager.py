# save_manager.py

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple


class ConversationSaveManager:
    """Handles saving conversation snapshots to JSON files."""
    
    def __init__(self, save_directory: str = "./saved_conversations/"):
        """
        Initialize the save manager.
        
        Args:
            save_directory: Directory where conversation files will be saved
        """
        self.save_directory = Path(save_directory)
        
    def save_conversation(self, filename: str, conversation_state: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Save a conversation to a JSON file.
        
        Args:
            filename: Desired filename (without extension)
            conversation_state: The conversation state dictionary to save
            
        Returns:
            Tuple of (file_path, error_message). file_path is None if failed, error_message is None if successful
        """
        try:
            # Ensure save directory exists
            self._ensure_save_directory()
            
            # Use conversation state directly without extra metadata
            save_data = conversation_state
            
            # Create full filename with extension
            if not filename.endswith('.json'):
                filename = f"{filename}.json"
                
            # Get unique filename to prevent overwrites
            unique_filename = self._get_unique_filename(filename)
            
            # Write to file
            file_path = self.save_directory / unique_filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
                
            return str(file_path), None
            
        except Exception as e:
            # Return the error message instead of None
            return None, str(e)
    
    def _ensure_save_directory(self) -> None:
        """Create the save directory if it doesn't exist."""
        try:
            self.save_directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise IOError(f"Failed to create save directory: {e}")
    
    def _get_unique_filename(self, filename: str) -> str:
        """
        Get a unique filename by adding a counter if the file already exists.
        
        Args:
            filename: Desired filename
            
        Returns:
            Unique filename that doesn't exist in the save directory
        """
        file_path = self.save_directory / filename
        
        # If file doesn't exist, return as-is
        if not file_path.exists():
            return filename
            
        # Extract name and extension
        name_part = filename.rsplit('.', 1)[0] if '.' in filename else filename
        ext_part = '.' + filename.rsplit('.', 1)[1] if '.' in filename else ''
        
        # Try numbered versions
        counter = 1
        while True:
            numbered_filename = f"{name_part}_{counter:03d}{ext_part}"
            numbered_path = self.save_directory / numbered_filename
            
            if not numbered_path.exists():
                return numbered_filename
                
            counter += 1
            
            # Safety check to prevent infinite loops
            if counter > 999:
                # Fall back to timestamp-based naming
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                return f"{name_part}_{timestamp}{ext_part}"
    
    def generate_default_filename(self) -> str:
        """
        Generate a default filename with timestamp.
        
        Returns:
            Default filename in format: conversation_YYYY-MM-DD_HH-MM-SS
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"conversation_{timestamp}"