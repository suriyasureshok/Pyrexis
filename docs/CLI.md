# PYREXIS CLI Reference

> Complete command-line interface documentation for PYREXIS job execution engine.

---

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [submit](#submit)
  - [status](#status)
  - [cancel](#cancel)
  - [list](#list)
  - [monitor](#monitor)
  - [daemon](#daemon)
  - [metrics](#metrics)
- [Examples](#examples)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Installation

No installation needed - PYREXIS is a pure Python project:

```bash
# Clone repository
git clone https://github.com/yourusername/pyrexis.git
cd pyrexis

# Install dependencies
pip install pydantic

# Run CLI
python main.py --help
```

---

## Quick Start

```bash
# 1. Submit a job
python main.py submit \
  --job-id my-task \
  --priority 5 \
  --payload '{"type": "example", "data": "process_this"}' \
  --mode thread

# 2. Check status
python main.py status --job-id my-task

# 3. Start daemon to process jobs
python main.py daemon

# 4. Monitor in real-time (separate terminal)
python main.py monitor
```

---

## Commands

### submit

Submit a new job to the execution engine.

**Usage:**
```bash
python main.py submit --job-id <ID> --priority <NUM> --payload <JSON> [OPTIONS]
```

**Required Arguments:**
- `--job-id ID` - Unique identifier for the job
- `--payload JSON` - Job payload as JSON string (must contain `"type"` field matching registered pipeline)

**Optional Arguments:**
- `--priority NUM` - Job priority (default: 0, higher = more priority)
- `--mode MODE` - Execution mode: `thread`, `process`, `async` (default: `thread`)
- `--max-retries NUM` - Maximum retry attempts on failure (default: 3)
- `--state-db PATH` - Path to state database (default: `./pyrexis_state.db`)

**Examples:**
```bash
# Basic job submission
python main.py submit \
  --job-id task-001 \
  --priority 5 \
  --payload '{"type": "example", "input": "data.csv"}'

# High-priority CPU-intensive job
python main.py submit \
  --job-id compute-heavy-1 \
  --priority 10 \
  --mode process \
  --payload '{"type": "matrix_multiply", "size": 1000}'

# I/O-bound job with retry limit
python main.py submit \
  --job-id api-call-1 \
  --priority 3 \
  --mode thread \
  --max-retries 5 \
  --payload '{"type": "fetch_data", "url": "https://api.example.com/data"}'
```

**Output:**
```
✅ Job 'task-001' submitted successfully
   Priority: 5
   Mode: thread
   Status: pending
```

---

### status

Get detailed status of a specific job.

**Usage:**
```bash
python main.py status --job-id <ID>
```

**Arguments:**
- `--job-id ID` - Job identifier to query
- `--state-db PATH` - Path to state database (default: `./pyrexis_state.db`)

**Examples:**
```bash
# Check job status
python main.py status --job-id task-001

# Use custom state database
python main.py status --job-id task-001 --state-db /path/to/custom.db
```

**Output:**
```
Job: task-001
Status: running
Priority: 5
Mode: thread
Attempts: 1/3
Created: 2026-01-18 14:32:15
Updated: 2026-01-18 14:32:20

# If job has errors:
Errors (2):
  1. Connection timeout after 30s
  2. HTTP 503 Service Unavailable
```

---

### cancel

Cancel a pending or running job.

**Usage:**
```bash
python main.py cancel --job-id <ID>
```

**Arguments:**
- `--job-id ID` - Job identifier to cancel
- `--state-db PATH` - Path to state database (default: `./pyrexis_state.db`)

**Examples:**
```bash
# Cancel a job
python main.py cancel --job-id task-001
```

**Output:**
```
✅ Job 'task-001' cancelled
```

**Notes:**
- Can only cancel jobs in `pending` or `running` state
- Completed or failed jobs cannot be cancelled
- Cancelled jobs transition to `failed` status with error message "Job cancelled by user"

---

### list

List recent jobs with optional filtering.

**Usage:**
```bash
python main.py list [OPTIONS]
```

**Optional Arguments:**
- `--limit NUM` - Maximum number of jobs to display (default: 20)
- `--status STATUS` - Filter by status: `pending`, `running`, `completed`, `failed`, `retrying`
- `--state-db PATH` - Path to state database (default: `./pyrexis_state.db`)

**Examples:**
```bash
# List 20 most recent jobs
python main.py list

# List last 50 jobs
python main.py list --limit 50

# List only pending jobs
python main.py list --status pending

# List failed jobs
python main.py list --status failed
```

**Output:**
```
Job ID               Status       Priority   Mode       Attempts  
======================================================================
task-003             running      10         process    1/3       
task-002             completed    5          thread     1/3       
task-001             failed       3          thread     3/3       
api-call-1           pending      8          thread     0/5       

Total: 4 jobs
```

---

### monitor

Real-time job monitoring dashboard.

**Usage:**
```bash
python main.py monitor [OPTIONS]
```

**Optional Arguments:**
- `--interval SECONDS` - Refresh interval in seconds (default: 2)
- `--state-db PATH` - Path to state database (default: `./pyrexis_state.db`)

**Examples:**
```bash
# Monitor with default 2-second refresh
python main.py monitor

# Monitor with 5-second refresh
python main.py monitor --interval 5
```

**Output:**
```
🔍 Monitoring jobs (Ctrl+C to exit)...

==================================================
📊 Job Status Summary (refreshed every 2s)
==================================================
⏳ Pending:   15   
▶️  Running:   3    
🔄 Retrying:  1    
✅ Completed: 42   
❌ Failed:    2    
==================================================

Currently Running:
  • compute-heavy-1 (priority=10, attempts=1)
  • api-call-1 (priority=8, attempts=2)
  • task-003 (priority=5, attempts=1)
```

**Notes:**
- Press `Ctrl+C` to stop monitoring
- Refreshes automatically at specified interval
- Shows max 5 currently running jobs

---

### daemon

Start the PYREXIS engine daemon to process jobs.

**Usage:**
```bash
python main.py daemon [OPTIONS]
```

**Optional Arguments:**
- `--log-level LEVEL` - Logging level: `debug`, `info`, `warning`, `error` (default: `info`)
- `--log-file PATH` - Log file path (optional, logs to console if not specified)
- `--poll-interval SECONDS` - Polling interval when no jobs available (default: 0.1)
- `--verbose` - Verbose output (shows each job processed)
- `--state-db PATH` - Path to state database (default: `./pyrexis_state.db`)

**Examples:**
```bash
# Start daemon with default settings
python main.py daemon

# Start with debug logging to file
python main.py daemon --log-level debug --log-file pyrexis.log

# Start with verbose output
python main.py daemon --verbose

# Start with longer polling interval (reduce CPU usage)
python main.py daemon --poll-interval 1.0
```

**Output:**
```
🚀 Starting PYREXIS daemon...
   State DB: ./pyrexis_state.db
   Log level: INFO

✅ Daemon started. Press Ctrl+C to stop.
==================================================

# With --verbose:
Processed job (total: 1)
Processed job (total: 2)
...

# On shutdown (Ctrl+C or SIGTERM):
🛑 Received SIGINT, initiating graceful shutdown...

✅ Daemon stopped gracefully. Jobs processed: 42
```

**Notes:**
- Daemon runs until `Ctrl+C` (SIGINT) or `SIGTERM` received
- Graceful shutdown: stops accepting new jobs, completes current jobs
- State persisted continuously - safe to restart after crash

---

### metrics

Display engine performance metrics.

**Usage:**
```bash
python main.py metrics
```

**Arguments:**
- `--state-db PATH` - Path to state database (default: `./pyrexis_state.db`)

**Examples:**
```bash
# Display metrics
python main.py metrics
```

**Output:**
```
📊 PYREXIS Metrics
==================================================

📈 Counters:
  job.retries                           3
  job.success                          42
  job.failure                           2

⏱️  Timings:
  job.execution                 
    Count:         42
    Avg:        0.150s
    Max:        0.420s
  pipeline.run                  
    Count:         42
    Avg:        0.120s
    Max:        0.380s
```

---

## Examples

### Example 1: Batch Processing Pipeline

```bash
# Submit 10 data processing jobs
for i in {1..10}; do
  python main.py submit \
    --job-id "batch-$i" \
    --priority $i \
    --payload "{\"type\": \"process\", \"file\": \"data_$i.csv\"}"
done

# Start daemon to process
python main.py daemon --log-level info --log-file processing.log

# Monitor progress (separate terminal)
python main.py monitor --interval 1
```

### Example 2: High-Priority Urgent Task

```bash
# Submit urgent job with high priority
python main.py submit \
  --job-id urgent-report \
  --priority 100 \
  --mode process \
  --payload '{"type": "generate_report", "deadline": "2026-01-18 18:00"}'

# Check status
python main.py status --job-id urgent-report

# If needed, cancel other jobs to free resources
python main.py list --status pending | grep -v urgent | while read -r line; do
  job_id=$(echo $line | awk '{print $1}')
  python main.py cancel --job-id "$job_id"
done
```

### Example 3: API Rate-Limited Jobs

```bash
# Submit API call jobs with retry logic
python main.py submit \
  --job-id api-fetch-1 \
  --priority 5 \
  --mode thread \
  --max-retries 10 \
  --payload '{"type": "api_call", "url": "https://api.example.com/data", "retry_delay": 60}'

# List all failed jobs (likely rate-limited)
python main.py list --status failed

# Get metrics to see retry count
python main.py metrics
```

### Example 4: CPU-Intensive Computation

```bash
# Submit compute-heavy job using processes
python main.py submit \
  --job-id matrix-compute \
  --priority 10 \
  --mode process \
  --max-retries 1 \
  --payload '{"type": "matrix_multiply", "size": 5000, "iterations": 100}'

# Start daemon with verbose output
python main.py daemon --verbose --log-level debug
```

---

## Configuration

### State Database Location

Default: `./pyrexis_state.db`

Change with `--state-db` flag:
```bash
python main.py --state-db /data/pyrexis.db submit --job-id task-1 ...
```

### Environment Variables

PYREXIS respects the following environment variables:

- `PYREXIS_STATE_DB` - Default state database path
- `PYREXIS_LOG_LEVEL` - Default logging level
- `PYREXIS_LOG_FILE` - Default log file path

Example:
```bash
export PYREXIS_STATE_DB=/data/production/pyrexis.db
export PYREXIS_LOG_LEVEL=INFO
export PYREXIS_LOG_FILE=/var/log/pyrexis.log

python main.py daemon
```

### Logging Configuration

Logging supports:
- **Console output**: Colored, human-readable
- **File output**: Rotating file handler (10MB max, 5 backups)
- **JSON format**: For structured logging systems

```bash
# JSON logging for production
python main.py daemon \
  --log-level info \
  --log-file pyrexis.json \
  --format json
```

---

## Troubleshooting

### Job Not Found

```
❌ Job 'task-1' not found
```

**Solutions:**
- Check job ID spelling
- Verify using correct `--state-db` path
- List all jobs: `python main.py list`

### Cannot Cancel Job

```
❌ Cannot cancel job 'task-1' (not found or already completed)
```

**Reasons:**
- Job already completed or failed
- Job doesn't exist
- Wrong state database

**Solutions:**
- Check status: `python main.py status --job-id task-1`
- Verify job state before cancelling

### Daemon Won't Start

```
❌ Daemon failed: [Errno 13] Permission denied: './pyrexis_state.db'
```

**Solutions:**
- Check file permissions: `ls -l pyrexis_state.db`
- Use different location: `--state-db /tmp/pyrexis.db`
- Verify write access to directory

### Invalid JSON Payload

```
❌ Invalid JSON payload: Expecting property name enclosed in double quotes
```

**Solutions:**
- Use single quotes around JSON: `'{"type": "example"}'`
- Escape double quotes in shell: `"{\"type\": \"example\"}"`
- Validate JSON: `echo '{"type": "example"}' | python -m json.tool`

### No Jobs Processing

**Checklist:**
1. Is daemon running? `ps aux | grep pyrexis`
2. Are jobs submitted? `python main.py list`
3. Are pipelines registered? Check `utils/registry.py`
4. Check logs: `python main.py daemon --log-level debug`

---

## Advanced Usage

### Programmatic API

Use Python API instead of CLI:

```python
from main import create_engine
from models import Job

# Create engine
engine = create_engine(state_db_path="./pyrexis.db", log_level="INFO")

# Submit job
job = Job(
    job_id="programmatic-1",
    priority=5,
    payload={"type": "example", "data": "process"},
    execution_mode="thread",
)
engine.submit_job(job)

# Process jobs
engine.run_loop()
```

### Custom Pipelines

Register custom pipelines:

```python
from utils import PluginRegistry

class MyPipeline:
    def stages(self):
        def stage1(data):
            # Your logic
            yield {"result": "processed"}
        return [stage1]

# Register
PluginRegistry.register_plugin("my_pipeline", MyPipeline)

# Use via CLI
python main.py submit --job-id custom-1 --payload '{"type": "my_pipeline"}'
```

### Monitoring Integration

Export metrics to monitoring systems:

```python
from main import create_engine

engine = create_engine()
metrics = engine.get_metrics()

# Export to Prometheus, Datadog, etc.
counters = metrics.get_counters()
timings = metrics.get_timings()
```

---

## See Also

- [README.md](../README.md) - Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [TESTING.md](TESTING.md) - Testing philosophy
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development guidelines

---

**Need help? Open an issue on GitHub!**
