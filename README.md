# Universal API Server

A FastAPI-based server that wraps the Universal API simulator, allowing you to simulate API calls using LLMs when the actual tool implementation is not available.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python server.py --host 0.0.0.0 --port 8000 --db ./universal_api.db --instance-file ./api_instances.json
```

Command-line options:
- `--host`: Host to bind the server to (default: 0.0.0.0)
- `--port`: Port to bind the server to (default: 8000)
- `--db`: Path to SQLite database file (default: universal_api.db)
- `--instance-file`: Path to instance persistence file (default: api_instances.json)

## API Endpoints

### 1. Send API Request

```
POST /api/call
```

There are two main ways to use this endpoint:

#### A. Creating a new API instance

When creating a new instance, provide:
- `tool_name`: Name of the API/tool to simulate (required)
- `tool_args`: Arguments to pass to the API (required)
- `tool_description`: Description of the API (optional but recommended)
- `config`: Configuration for the UniversalAPI instance (optional)

Leave `instance_id` blank to generate a new one automatically.

Request body example:
```json
{
  "tool_name": "weather_api",
  "tool_args": {"location": "New York"},
  "tool_description": "API that returns current weather for a location",
  "config": {
    "model": "gpt-4o",
    "temperature": 0.0,
    "max_tokens": 2048
  }
}
```

#### B. Using an existing API instance

When using an existing instance, provide:
- `tool_name`: Name of the API/tool to simulate (required)
- `tool_args`: Arguments to pass to the API (required)
- `instance_id`: ID of an existing API instance (required)
- `tool_description`: Description of the API (optional)

**Important**: If you provide a tool description for an existing instance, it must match what was used when creating the instance, or the request will be rejected.

Request body example:
```json
{
  "tool_name": "weather_forecast_api",
  "tool_args": {"location": "New York", "days": 3},
  "instance_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Response

```json
{
  "success": true,
  "response": {},
  "instance_id": "550e8400-e29b-41d4-a716-446655440000",
  "metrics": {
    "instance_id": "550e8400-e29b-41d4-a716-446655440000",
    "message_count": 2,
    "history_size_chars": 512,
    "tool_names": ["weather_api", "weather_forecast_api"]
  }
}
```

### 2. List API Instances

```
GET /api/instances
```

Response:
```json
{
  "instances": [
    {
      "instance_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2023-01-01T12:00:00.000Z",
      "last_used": "2023-01-01T12:05:00.000Z",
      "message_count": 2,
      "history_size_chars": 512,
      "tool_names": ["weather_api", "weather_forecast_api"]
    }
  ]
}
```

### 3. Delete API Instance

```
DELETE /api/instances/{instance_id}
```

Response:
```json
{
  "status": "deleted",
  "instance_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Examples

### Example: Simulate a weather API call (new instance)

```bash
curl -X POST http://localhost:8000/api/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "weather_api", "tool_args": {"location": "New York"}, "tool_description": "API that returns current weather for a location"}'
```

### Example: Simulate a forecast API call (using existing instance)

```bash
curl -X POST http://localhost:8000/api/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "weather_forecast_api", "tool_args": {"location": "New York", "days": 3}, "instance_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

### Example: List all active instances

```bash
curl http://localhost:8000/api/instances
```

### Example: Delete an instance

```bash
curl -X DELETE http://localhost:8000/api/instances/550e8400-e29b-41d4-a716-446655440000
```

## Testing

The repository includes a test script (`test_api.py`) that demonstrates how to use the API:

```bash
python test_api.py --url http://localhost:8000 --test all
```

Test options:
- `--url`: Base URL of the server (default: http://localhost:8000)
- `--test`: Test to run: basic, custom, bulk, validation, or all (default: basic)
- `--count`: Number of instances for bulk test (default: 5)

## Management

The repository includes a management script (`manage.py`) for administrative tasks:

```bash
python manage.py [command]
```

Available commands:

### Clear Database

Removes all instances from the SQLite database:

```bash
python manage.py clear-db --db ./universal_api.db
```

### Reset Instances File

Resets the instance persistence file:

```bash
python manage.py reset-instances --file ./api_instances.json
```

### List Instances from Database

Lists all instances stored in the SQLite database:

```bash
python manage.py list-db --db ./universal_api.db
```

### List Instances from File

Lists all instances stored in the persistence file:

```bash
python manage.py list-file --file ./api_instances.json
```

### Reset All

Resets both the database and the persistence file:

```bash
python manage.py reset-all --db ./universal_api.db --file ./api_instances.json
``` 