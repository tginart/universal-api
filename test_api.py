"""
Test script for the Universal API server.

This script demonstrates how to use the Universal API server
by making various API calls and showing the responses.
"""

import argparse
import asyncio
import json
import httpx
import sys

BASE_URL = "http://localhost:8000"

async def test_api_call(client, tool_name, tool_args, tool_description=None, instance_id=None, config=None):
    """Make a test API call."""
    payload = {
        "tool_name": tool_name,
        "tool_args": tool_args,
        "tool_description": tool_description,
        "instance_id": instance_id,
        "config": config
    }
    
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}
    
    try:
        response = await client.post(f"{BASE_URL}/api/call", json=payload)
        response.raise_for_status()
        response_data = response.json()
        
        print(f"\n=== API Call: {tool_name} ===")
        print(f"Instance ID: {response_data['instance_id']}")
        print(f"Success: {response_data['success']}")
        print(f"Metrics: {json.dumps(response_data['metrics'], indent=2)}")
        print(f"Response: {json.dumps(response_data['response'], indent=2)}")
        
        return response_data["instance_id"]
    except httpx.HTTPStatusError as e:
        print(f"Error calling API: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

async def list_instances(client):
    """List all API instances."""
    try:
        response = await client.get(f"{BASE_URL}/api/instances")
        response.raise_for_status()
        instances = response.json()["instances"]
        
        print("\n=== API Instances ===")
        for instance in instances:
            print(f"ID: {instance['instance_id']}")
            print(f"  Created: {instance['created_at']}")
            print(f"  Last Used: {instance['last_used']}")
            print(f"  Message Count: {instance['message_count']}")
            print(f"  History Size: {instance['history_size_chars']} chars")
            print(f"  Tool Names: {instance['tool_names']}")
        
        return instances
    except httpx.HTTPStatusError as e:
        print(f"Error listing instances: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

async def delete_instance(client, instance_id):
    """Delete an API instance."""
    try:
        response = await client.delete(f"{BASE_URL}/api/instances/{instance_id}")
        response.raise_for_status()
        result = response.json()
        
        print(f"\n=== Deleted Instance: {instance_id} ===")
        print(f"Status: {result['status']}")
        
        return result
    except httpx.HTTPStatusError as e:
        print(f"Error deleting instance: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

async def run_basic_test(client):
    """Run a basic test of API functionality."""
    print("\n=== Running Basic Test ===")
    
    # Test 1: Make a weather API call
    instance_id = await test_api_call(
        client,
        "weather_api",
        {"location": "New York"},
        "API that returns current weather for a location"
    )
    
    if not instance_id:
        return
    
    # Test 2: Make another call to the same instance
    await test_api_call(
        client,
        "weather_forecast_api",
        {"location": "New York", "days": 3},
        "API that returns weather forecast for a location",
        instance_id
    )
    
    # Test 3: List all instances
    instances = await list_instances(client)
    
    # Test 4: Delete an instance
    if instances:
        await delete_instance(client, instances[0]["instance_id"])
        
        # List instances again to verify deletion
        await list_instances(client)

async def run_custom_config_test(client):
    """Run a test with custom configuration."""
    print("\n=== Running Custom Config Test ===")
    
    # Create a new instance with custom configuration
    instance_id = await test_api_call(
        client,
        "custom_api",
        {"param": "value"},
        "API with custom configuration",
        config={
            "model": "gpt-4-turbo",
            "temperature": 0.7,
            "max_tokens": 1024
        }
    )
    
    if not instance_id:
        return
    
    # Make another call to the same instance
    await test_api_call(
        client,
        "another_custom_api",
        {"another_param": "another_value"},
        "Another API with custom configuration",
        instance_id
    )
    
    # List instances to verify
    await list_instances(client)

async def run_bulk_test(client, count=5):
    """Run a bulk test with multiple instances."""
    print(f"\n=== Running Bulk Test ({count} instances) ===")
    
    for i in range(count):
        await test_api_call(
            client,
            f"bulk_api_{i}",
            {"id": i, "data": f"test data {i}"},
            f"Bulk API test {i}"
        )
    
    # List all instances
    await list_instances(client)

async def run_validation_test(client):
    """Run a test for tool description validation."""
    print("\n=== Running Tool Description Validation Test ===")
    
    # Step 1: Create a new instance with a specific tool description
    original_description = "API that returns current weather for a location"
    instance_id = await test_api_call(
        client,
        "weather_api",
        {"location": "New York"},
        original_description
    )
    
    if not instance_id:
        return
    
    print("\n--- Testing with matching description ---")
    # Step 2: Make another call with the same description (should succeed)
    await test_api_call(
        client,
        "weather_api",
        {"location": "Boston"},
        original_description,
        instance_id
    )
    
    print("\n--- Testing with mismatched description ---")
    # Step 3: Make a call with a different description (should fail)
    different_description = "API that returns weather data for cities"
    await test_api_call(
        client,
        "weather_api",
        {"location": "Chicago"},
        different_description,
        instance_id
    )
    
    print("\n--- Testing with no description ---")
    # Step 4: Make a call with no description (should succeed)
    await test_api_call(
        client,
        "weather_api",
        {"location": "Seattle"},
        None,
        instance_id
    )

async def main():
    """Run the test script."""
    parser = argparse.ArgumentParser(description="Test the Universal API server")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the server")
    parser.add_argument("--test", choices=["basic", "custom", "bulk", "validation", "all"], default="basic", 
                       help="Test to run: basic, custom, bulk, validation, or all")
    parser.add_argument("--count", type=int, default=5, help="Number of instances for bulk test")
    args = parser.parse_args()
    
    global BASE_URL
    BASE_URL = args.url
    
    try:
        async with httpx.AsyncClient() as client:
            # Test connectivity
            try:
                response = await client.get(f"{BASE_URL}/api/instances")
                response.raise_for_status()
                print(f"Connected to server at {BASE_URL}")
            except Exception as e:
                print(f"Error connecting to server at {BASE_URL}: {e}")
                sys.exit(1)
            
            # Run selected tests
            if args.test == "basic" or args.test == "all":
                await run_basic_test(client)
            
            if args.test == "custom" or args.test == "all":
                await run_custom_config_test(client)
            
            if args.test == "bulk" or args.test == "all":
                await run_bulk_test(client, args.count)
                
            if args.test == "validation" or args.test == "all":
                await run_validation_test(client)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 