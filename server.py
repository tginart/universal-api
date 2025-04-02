"""
FastAPI server that wraps the UniversalAPI.

This server provides endpoints to:
1. Send requests to the UniversalAPI
2. List active API instances
"""

import argparse
import asyncio
import json
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from universal_api import UniversalAPI, UniversalAPIConfig
from database import init_db, get_db, Database
from instance_manager import init_instance_manager, get_instance_manager, InstanceManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("universal-api-server")

# Models for request/response
class APIRequest(BaseModel):
    tool_name: str
    tool_args: Dict[str, Any]
    tool_description: Optional[str] = None
    instance_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "tool_name": "weather_api",
                "tool_args": {"location": "New York"},
                "tool_description": "API that returns current weather for a location",
                "instance_id": None,
                "config": {"model": "gpt-4o", "temperature": 0.0}
            },
            "description": """
            When creating a new instance:
            - Provide tool_name, tool_args, and optionally tool_description and config
            - Leave instance_id blank to generate a new one
            
            When using an existing instance:
            - Provide tool_name, tool_args, and instance_id
            - If tool_description is provided, it must match what was used when creating the instance
            """
        }

class APIResponse(BaseModel):
    success: bool
    response: Any
    instance_id: str
    metrics: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "response": {"temperature": 72, "conditions": "partly cloudy"},
                "instance_id": "550e8400-e29b-41d4-a716-446655440000",
                "metrics": {
                    "message_count": 2,
                    "history_size_chars": 512,
                    "tool_names": ["weather_api"]
                }
            }
        }

class InstanceListResponse(BaseModel):
    instances: List[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "instances": [
                    {
                        "instance_id": "550e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2023-01-01T12:00:00.000Z",
                        "last_used": "2023-01-01T12:05:00.000Z",
                        "message_count": 2,
                        "history_size_chars": 512,
                        "tool_names": ["weather_api"]
                    }
                ]
            }
        }

# Initialize FastAPI app
app = FastAPI(title="Universal API Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize resources on server startup."""
    logger.info("Server starting up")
    
    # Get configuration values from environment variables or command line args
    db_path = os.environ.get("UNIVERSAL_API_DB", "universal_api.db")
    instance_file = os.environ.get("UNIVERSAL_API_INSTANCE_FILE", "api_instances.json")
    
    # Initialize database and instance manager
    try:
        logger.info(f"Initializing database at {db_path}")
        init_db(db_path)
        
        logger.info(f"Initializing instance manager with persistence at {instance_file}")
        init_instance_manager(instance_file)
        
        logger.info("Initialization complete")
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        # Don't raise here - we'll use in-memory fallbacks if necessary

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on server shutdown."""
    logger.info("Server shutting down")
    
    try:
        # Save instances to disk
        instance_manager = get_instance_manager()
        instance_manager.save_to_disk()
        
        # Close database connection
        db = get_db()
        db.close()
        
        logger.info("Cleanup complete")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

def get_instance_metrics(instance_id: str) -> Dict[str, Any]:
    """Calculate metrics for a given API instance."""
    instance_manager = get_instance_manager()
    instance = instance_manager.get_instance(instance_id)
    if not instance:
        return {}
    
    total_messages = 0
    total_chars = 0
    tool_names = set()
    
    for tool_name, messages in instance.messages.items():
        tool_names.add(tool_name)
        total_messages += len(messages)
        total_chars += sum(len(m.get("content", "")) for m in messages)
    
    return {
        "instance_id": instance_id,
        "message_count": total_messages,
        "history_size_chars": total_chars,
        "tool_names": list(tool_names)
    }

def save_instance_to_db(instance_id: str, db: Database = Depends(get_db)):
    """Save instance metrics to the database."""
    metrics = get_instance_metrics(instance_id)
    
    now = datetime.now().isoformat()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if instance exists
            cursor.execute("SELECT id FROM instances WHERE id = ?", (instance_id,))
            exists = cursor.fetchone()
            
            history_size = metrics.get("history_size_chars", 0)
            tool_names_json = json.dumps(list(metrics.get("tool_names", [])))
            
            if exists:
                cursor.execute('''
                UPDATE instances 
                SET last_used = ?, message_count = ?, history_size = ?, tool_names = ?
                WHERE id = ?
                ''', (
                    now,
                    metrics.get("message_count", 0),
                    history_size,
                    tool_names_json,
                    instance_id
                ))
            else:
                cursor.execute('''
                INSERT INTO instances (id, created_at, last_used, message_count, history_size, tool_names)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    instance_id,
                    now,
                    now,
                    metrics.get("message_count", 0),
                    history_size,
                    tool_names_json
                ))
            
            conn.commit()
    except Exception as e:
        logger.error(f"Error saving instance to database: {str(e)}")
        # Don't raise - this shouldn't block the API response

@app.post("/api/call", response_model=APIResponse)
async def api_call(request: APIRequest, db: Database = Depends(get_db)):
    """Send a request to the UniversalAPI."""
    try:
        instance_id = request.instance_id or str(uuid.uuid4())
        instance_manager = get_instance_manager()
        
        # Check if this is an existing instance
        instance = instance_manager.get_instance(instance_id)
        is_new_instance = instance is None
        
        # If this is an existing instance and tool description is provided, validate it
        if not is_new_instance and request.tool_description:
            # Get the tool info from the instance's message history
            tool_info_mismatch = False
            if request.tool_name in instance.messages:
                # Extract tool description from the first user message for this tool
                for message in instance.messages.get(request.tool_name, []):
                    if message.get("role") == "user":
                        content = message.get("content", "")
                        # Check if the current tool description is consistent with previous usage
                        if request.tool_description not in content:
                            tool_info_mismatch = True
                        break
                
                if tool_info_mismatch:
                    logger.warning(f"Tool description mismatch for instance {instance_id}")
                    return APIResponse(
                        success=False,
                        response="Tool description does not match the one used when creating this instance",
                        instance_id=instance_id,
                        metrics=get_instance_metrics(instance_id)
                    )
        
        # Create new instance if needed
        if is_new_instance:
            logger.info(f"Creating new API instance: {instance_id}")
            config = UniversalAPIConfig()
            if request.config:
                for key, value in request.config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            instance = UniversalAPI(config)
            instance_manager.add_instance(instance_id, instance)
        
        # Call the API
        logger.info(f"Calling API '{request.tool_name}' with instance {instance_id}")
        success, response = await instance.simulate_api_call(
            request.tool_name,
            request.tool_args,
            request.tool_description
        )
        
        # Get metrics and save to DB
        metrics = get_instance_metrics(instance_id)
        save_instance_to_db(instance_id, db)
        
        logger.info(f"API call completed: {request.tool_name}, success={success}")
        
        return APIResponse(
            success=success,
            response=response,
            instance_id=instance_id,
            metrics=metrics
        )
    except Exception as e:
        logger.error(f"Error in API call: {str(e)}")
        return APIResponse(
            success=False,
            response=f"Internal server error: {str(e)}",
            instance_id=request.instance_id or "error",
            metrics={}
        )

@app.get("/api/instances", response_model=InstanceListResponse)
async def list_instances(db: Database = Depends(get_db)):
    """List all active API instances with their metrics."""
    try:
        logger.info("Listing API instances")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM instances ORDER BY last_used DESC")
            
            instances = []
            for row in cursor.fetchall():
                instances.append({
                    "instance_id": row["id"],
                    "created_at": row["created_at"],
                    "last_used": row["last_used"],
                    "message_count": row["message_count"],
                    "history_size_chars": row["history_size"],
                    "tool_names": json.loads(row["tool_names"])
                })
            
            logger.info(f"Found {len(instances)} instances")
            return InstanceListResponse(instances=instances)
    except Exception as e:
        logger.error(f"Error listing instances: {str(e)}")
        # Return empty list on error
        return InstanceListResponse(instances=[])

@app.delete("/api/instances/{instance_id}")
async def delete_instance(instance_id: str, db: Database = Depends(get_db)):
    """Delete an API instance."""
    try:
        logger.info(f"Deleting API instance: {instance_id}")
        instance_manager = get_instance_manager()
        instance_manager.remove_instance(instance_id)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM instances WHERE id = ?", (instance_id,))
            conn.commit()
        
        return {"status": "deleted", "instance_id": instance_id}
    except Exception as e:
        logger.error(f"Error deleting instance {instance_id}: {str(e)}")
        return {"status": "error", "instance_id": instance_id, "error": str(e)}

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Universal API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--db", default="universal_api.db", help="Path to SQLite database file")
    parser.add_argument("--instance-file", default="api_instances.json", help="Path to instance persistence file")
    return parser.parse_args()

def main():
    """Main entry point for the server."""
    args = parse_args()
    
    # Store paths in environment variables for the startup event
    os.environ["UNIVERSAL_API_DB"] = args.db
    os.environ["UNIVERSAL_API_INSTANCE_FILE"] = args.instance_file
    
    # Start the server
    logger.info(f"Starting server on {args.host}:{args.port}")
    uvicorn.run("server:app", host=args.host, port=args.port, reload=True)

if __name__ == "__main__":
    main() 