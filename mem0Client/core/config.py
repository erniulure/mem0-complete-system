"""Configuration management for Mem0 Client."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class Config:
    """Configuration manager for Mem0 Client."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager."""
        # Load environment variables
        load_dotenv()
        
        # Load config file
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    @property
    def mem0_api_key(self) -> str:
        """Get Mem0 API key from environment or config."""
        return os.getenv('MEM0_API_KEY') or self.config.get('mem0', {}).get('api_key', '')
    
    @property
    def default_user_id(self) -> str:
        """Get default user ID."""
        return os.getenv('DEFAULT_USER_ID') or self.config.get('defaults', {}).get('user_id', 'default_user')
    
    @property
    def default_extract_mode(self) -> str:
        """Get default extract mode."""
        return self.config.get('defaults', {}).get('extract_mode', 'auto')
    
    @property
    def batch_size(self) -> int:
        """Get batch processing size."""
        return self.config.get('defaults', {}).get('batch_size', 10)
    
    @property
    def supported_formats(self) -> list:
        """Get supported file formats."""
        return self.config.get('file_processing', {}).get('supported_formats', ['.md', '.txt'])
    
    @property
    def max_file_size_mb(self) -> int:
        """Get maximum file size in MB."""
        return self.config.get('file_processing', {}).get('max_file_size_mb', 10)
    
    @property
    def search_default_limit(self) -> int:
        """Get default search limit."""
        return self.config.get('search', {}).get('default_limit', 10)
    
    @property
    def search_max_limit(self) -> int:
        """Get maximum search limit."""
        return self.config.get('search', {}).get('max_limit', 100)
    
    @property
    def debug_logging(self) -> bool:
        """Get debug logging setting."""
        return self.config.get('debug', {}).get('enable_api_logging', True)
    
    @property
    def message_batch_threshold(self) -> int:
        """Get message batch threshold."""
        return self.config.get('message_processing', {}).get('batch_threshold', 10)
    
    @property 
    def message_batch_size(self) -> int:
        """Get message batch size."""
        return self.config.get('message_processing', {}).get('batch_size', 8)
    
    @property
    def enable_message_batching(self) -> bool:
        """Get whether message batching is enabled."""
        return self.config.get('message_processing', {}).get('enable_batching', True)
    
    # Advanced settings properties
    @property
    def advanced_custom_instructions(self) -> str:
        """Get persistent custom instructions."""
        return self.config.get('advanced_settings', {}).get('custom_instructions', '')
    
    @property
    def advanced_includes(self) -> str:
        """Get persistent includes."""
        return self.config.get('advanced_settings', {}).get('includes', '')
    
    @property
    def advanced_excludes(self) -> str:
        """Get persistent excludes."""
        return self.config.get('advanced_settings', {}).get('excludes', '')
    
    @property
    def advanced_exclude_presets(self) -> list:
        """Get persistent exclude presets."""
        return self.config.get('advanced_settings', {}).get('exclude_presets', [])
    
    @property
    def advanced_infer(self) -> bool:
        """Get persistent infer setting."""
        return self.config.get('advanced_settings', {}).get('infer', True)
    
    # File processing properties
    @property
    def concurrent_upload(self) -> bool:
        """Get whether concurrent file uploads are enabled."""
        return self.config.get('file_processing', {}).get('concurrent_upload', True)
    
    @property
    def max_concurrent_files(self) -> int:
        """Get maximum number of concurrent file uploads."""
        return self.config.get('file_processing', {}).get('max_concurrent_files', 3)
    
    def get_time_preset(self, preset_name: str) -> Optional[int]:
        """Get time preset value in days."""
        return self.config.get('time_presets', {}).get(preset_name)
    
    def update_advanced_settings(self, **settings):
        """Update advanced settings and save to config file."""
        if 'advanced_settings' not in self.config:
            self.config['advanced_settings'] = {}
        
        # Update the settings
        for key, value in settings.items():
            if key in ['custom_instructions', 'includes', 'excludes', 'exclude_presets', 'infer']:
                self.config['advanced_settings'][key] = value
        
        # Save to file
        self._save_config()
    
    def _save_config(self):
        """Save current config to file."""
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
    
    def validate(self) -> bool:
        """Validate configuration."""
        if not self.mem0_api_key:
            print("❌ MEM0_API_KEY not found in environment variables or config")
            return False
        return True 