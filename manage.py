#!/usr/bin/env python
"""
Management script for the Universal API server.

This script provides utilities for managing the Universal API server,
such as clearing the database, resetting instances, etc.
"""

import argparse
import json
import os
import sqlite3
import sys

def clear_database(db_path):
    """Clear the instances table in the database."""
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM instances")
        conn.commit()
        
        count = cursor.rowcount
        print(f"Deleted {count} instances from the database")
        conn.close()
        return True
    except Exception as e:
        print(f"Error clearing database: {e}")
        return False

def reset_instances(instance_file):
    """Reset the saved instances file."""
    if not os.path.exists(instance_file):
        print(f"Instance file {instance_file} does not exist")
        return False
    
    try:
        # Just create an empty file
        with open(instance_file, "w") as f:
            f.write("{}")
        
        print(f"Reset instances file {instance_file}")
        return True
    except Exception as e:
        print(f"Error resetting instances: {e}")
        return False

def list_instances_from_db(db_path):
    """List instances from the database."""
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM instances ORDER BY last_used DESC")
        
        instances = cursor.fetchall()
        
        if not instances:
            print("No instances found in the database")
            return True
        
        print(f"Found {len(instances)} instances:")
        for instance in instances:
            print(f"ID: {instance['id']}")
            print(f"  Created: {instance['created_at']}")
            print(f"  Last Used: {instance['last_used']}")
            print(f"  Message Count: {instance['message_count']}")
            print(f"  History Size: {instance['history_size']} chars")
            print(f"  Tool Names: {instance['tool_names']}")
            print()
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error listing instances: {e}")
        return False

def list_instances_from_file(instance_file):
    """List instances from the saved instances file."""
    if not os.path.exists(instance_file):
        print(f"Instance file {instance_file} does not exist")
        return False
    
    try:
        with open(instance_file, "r") as f:
            instances = json.load(f)
        
        if not instances:
            print("No instances found in the file")
            return True
        
        print(f"Found {len(instances)} instances:")
        for instance_id, data in instances.items():
            print(f"ID: {instance_id}")
            print(f"  Model: {data.get('model', 'unknown')}")
            print(f"  Temperature: {data.get('temperature', 'unknown')}")
            print(f"  Max Tokens: {data.get('max_tokens', 'unknown')}")
            
            messages = data.get("messages", {})
            tool_names = list(messages.keys())
            total_messages = sum(len(msgs) for msgs in messages.values())
            
            print(f"  Tool Names: {tool_names}")
            print(f"  Message Count: {total_messages}")
            print()
        
        return True
    except Exception as e:
        print(f"Error listing instances from file: {e}")
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Management script for Universal API server")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Clear database command
    clear_parser = subparsers.add_parser("clear-db", help="Clear the database")
    clear_parser.add_argument("--db", default="universal_api.db", help="Path to SQLite database file")
    
    # Reset instances command
    reset_parser = subparsers.add_parser("reset-instances", help="Reset the saved instances file")
    reset_parser.add_argument("--file", default="api_instances.json", help="Path to instance persistence file")
    
    # List instances from database command
    list_db_parser = subparsers.add_parser("list-db", help="List instances from the database")
    list_db_parser.add_argument("--db", default="universal_api.db", help="Path to SQLite database file")
    
    # List instances from file command
    list_file_parser = subparsers.add_parser("list-file", help="List instances from the saved instances file")
    list_file_parser.add_argument("--file", default="api_instances.json", help="Path to instance persistence file")
    
    # Reset all command
    reset_all_parser = subparsers.add_parser("reset-all", help="Reset both database and instances file")
    reset_all_parser.add_argument("--db", default="universal_api.db", help="Path to SQLite database file")
    reset_all_parser.add_argument("--file", default="api_instances.json", help="Path to instance persistence file")
    
    args = parser.parse_args()
    
    if args.command == "clear-db":
        if not clear_database(args.db):
            sys.exit(1)
    elif args.command == "reset-instances":
        if not reset_instances(args.file):
            sys.exit(1)
    elif args.command == "list-db":
        if not list_instances_from_db(args.db):
            sys.exit(1)
    elif args.command == "list-file":
        if not list_instances_from_file(args.file):
            sys.exit(1)
    elif args.command == "reset-all":
        db_success = clear_database(args.db)
        file_success = reset_instances(args.file)
        
        if not (db_success and file_success):
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main() 