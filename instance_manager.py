"""
Instance manager for Universal API.

This module provides functionality to persist and restore API instances.
"""

import json
import os
import logging
from typing import Dict, Any, Optional

from universal_api import UniversalAPI, UniversalAPIConfig

logger = logging.getLogger("universal-api-server")

class InstanceManager:
    """Manages UniversalAPI instances."""
    
    def __init__(self, persistence_path: Optional[str] = None):
        """Initialize instance manager."""
        self.instances: Dict[str, UniversalAPI] = {}
        self.persistence_path = persistence_path or "api_instances.json"
        
        # Ensure directory exists
        persistence_dir = os.path.dirname(self.persistence_path)
        if persistence_dir and not os.path.exists(persistence_dir):
            os.makedirs(persistence_dir)
            
        # Try to load instances right away
        self.load_from_disk()
    
    def get_instance(self, instance_id: str) -> Optional[UniversalAPI]:
        """Get an API instance by ID."""
        return self.instances.get(instance_id)
    
    def add_instance(self, instance_id: str, instance: UniversalAPI) -> None:
        """Add an API instance."""
        self.instances[instance_id] = instance
    
    def remove_instance(self, instance_id: str) -> bool:
        """Remove an API instance."""
        if instance_id in self.instances:
            del self.instances[instance_id]
            return True
        return False
    
    def get_all_instances(self) -> Dict[str, UniversalAPI]:
        """Get all API instances."""
        return self.instances
    
    def save_to_disk(self) -> None:
        """Save instances to disk."""
        try:
            serialized_instances = {}
            for instance_id, instance in self.instances.items():
                serialized_instances[instance_id] = {
                    "model": instance.model,
                    "prompt": instance.prompt,
                    "temperature": instance.temperature,
                    "max_tokens": instance.max_tokens,
                    "messages": instance.messages
                }
            
            with open(self.persistence_path, "w") as f:
                json.dump(serialized_instances, f)
            
            logger.info(f"Saved {len(serialized_instances)} instances to {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to save instances: {str(e)}")
    
    def load_from_disk(self) -> None:
        """Load instances from disk."""
        if not os.path.exists(self.persistence_path):
            logger.info(f"Persistence file {self.persistence_path} does not exist")
            return
        
        try:
            with open(self.persistence_path, "r") as f:
                serialized_instances = json.load(f)
            
            for instance_id, data in serialized_instances.items():
                config = UniversalAPIConfig(
                    model=data.get("model", "gpt-4o"),
                    prompt=data.get("prompt", ""),
                    temperature=data.get("temperature", 0.0),
                    max_tokens=data.get("max_tokens", 2048)
                )
                instance = UniversalAPI(config)
                instance.messages = data.get("messages", {})
                self.instances[instance_id] = instance
            
            logger.info(f"Loaded {len(self.instances)} instances from {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load instances: {str(e)}")

# Global instance manager
_manager = None

def init_instance_manager(persistence_path: Optional[str] = None) -> InstanceManager:
    """Initialize the instance manager."""
    global _manager
    if _manager is None:
        _manager = InstanceManager(persistence_path)
    return _manager

def get_instance_manager() -> InstanceManager:
    """Get the instance manager."""
    global _manager
    if _manager is None:
        _manager = InstanceManager()
    return _manager 