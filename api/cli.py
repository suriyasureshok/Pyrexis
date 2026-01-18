"""
api/cli.py

Command-line interface for PYREXIS job execution engine.

Provides commands for:
- submit: Submit new jobs
- status: Check job status
- cancel: Cancel pending/running jobs
- list: List all jobs
- metrics: Display engine metrics
- daemon: Run continuous job execution
"""

import argparse
import json
import sys
import time
import signal
from pathlib import Path

from models.job import Job, JobStatus
from core.scheduler import Scheduler
from core.executor import ExecutorRouter
from core.engine import Engine
from storage.state import StateStore
from utils.shutdown import ShutdownCoordinator


def create_engine(state_db_path: str) -> Engine:
    """Create engine instance with components."""
    scheduler = Scheduler()
    executor = ExecutorRouter()
    state_store = StateStore(state_db_path)
    shutdown_coordinator = ShutdownCoordinator()
    
    engine = Engine(
        scheduler=scheduler,
        executor=executor,
        state_store=state_store,
        shutdown_coordinator=shutdown_coordinator,
    )
    
    return engine


def cmd_submit(args, engine: Engine):
    """Handle submit command."""
    try:
        # Parse payload
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON payload: {e}", file=sys.stderr)
            return 1
        
        # Create job
        try:
            job = Job(
                job_id=args.job_id,
                priority=args.priority,
                payload=payload,
                execution_mode=args.mode,
            )
        except Exception as e:
            print(f"[ERROR] Invalid job configuration: {e}", file=sys.stderr)
            return 1
        
        # Submit job
        try:
            engine.submit_job(job)
            print(f"Job '{args.job_id}' submitted successfully")
            return 0
        except Exception as e:
            print(f"[ERROR] Failed to submit job: {e}", file=sys.stderr)
            return 1
            
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_status(args, engine: Engine):
    """Handle status command."""
    try:
        job = engine.get_job(args.job_id)
        
        if job is None:
            print(f"[ERROR] Job '{args.job_id}' not found", file=sys.stderr)
            return 1
        
        # Display job information
        print(f"Job ID: {job.job_id}")
        print(f"Status: {job.status.value}")
        print(f"Priority: {job.priority}")
        print(f"Mode: {job.execution_mode}")
        print(f"Attempts: {job.attempts}/{job.max_entries}")
        
        if job.last_error:
            print(f"Last Error: {job.last_error}")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Failed to get status: {e}", file=sys.stderr)
        return 1


def cmd_cancel(args, engine: Engine):
    """Handle cancel command."""
    try:
        success = engine.cancel_job(args.job_id)
        
        if success:
            print(f"Job '{args.job_id}' cancelled")
            return 0
        else:
            print(f"[ERROR] Cannot cancel job '{args.job_id}' (not found or already completed)", file=sys.stderr)
            return 1
            
    except Exception as e:
        print(f"[ERROR] Failed to cancel job: {e}", file=sys.stderr)
        return 1


def cmd_list(args, engine: Engine):
    """Handle list command."""
    try:
        # Get jobs
        if args.status:
            try:
                status_filter = JobStatus(args.status.lower())
                jobs = engine.get_all_jobs(status=status_filter)
            except ValueError:
                print(f"[ERROR] Invalid status: {args.status}", file=sys.stderr)
                return 1
        else:
            jobs = engine.list_jobs(limit=args.limit)
        
        if not jobs:
            print("No jobs found")
            return 0
        
        # Display jobs
        print(f"{'Job ID':<25} {'Status':<12} {'Priority':<10} {'Mode':<10}")
        print("-" * 60)
        
        for job in jobs:
            print(f"{job.job_id:<25} {job.status.value:<12} {job.priority:<10} {job.execution_mode:<10}")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Failed to list jobs: {e}", file=sys.stderr)
        return 1


def cmd_daemon(args, engine: Engine):
    """Handle daemon command."""
    try:
        # Setup signal handler
        shutdown_flag = False
        
        def signal_handler(sig, frame):
            nonlocal shutdown_flag
            shutdown_flag = True
            engine._shutdown.initiate()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        print("Daemon started. Press Ctrl+C to stop.")
        
        jobs_processed = 0
        
        # Main loop
        while not shutdown_flag:
            result = engine.run_next()
            
            if result:
                jobs_processed += 1
            else:
                # No jobs, sleep briefly
                time.sleep(args.poll_interval)
        
        print(f"\nDaemon stopped gracefully. Jobs processed: {jobs_processed}")
        return 0
        
    except Exception as e:
        print(f"[ERROR] Daemon failed: {e}", file=sys.stderr)
        return 1


def cmd_metrics(args, engine: Engine):
    """Handle metrics command."""
    try:
        metrics = engine.get_metrics()
        
        print("PYREXIS Metrics")
        print("=" * 40)
        
        # Display all metrics
        if hasattr(metrics, '_metrics'):
            for key, value in metrics._metrics.items():
                print(f"{key}: {value}")
        else:
            print("No metrics data available")
        
        # Display job counts by status
        print("\nJob Status Counts:")
        all_jobs = engine.get_all_jobs()
        
        status_counts = {}
        for job in all_jobs:
            status_counts[job.status.value] = status_counts.get(job.status.value, 0) + 1
        
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Failed to get metrics: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PYREXIS Job Execution Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--state-db",
        required=True,
        help="Path to state database file",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit a new job")
    submit_parser.add_argument("--job-id", required=True, help="Unique job identifier")
    submit_parser.add_argument("--priority", type=int, required=True, help="Job priority (0-10)")
    submit_parser.add_argument("--payload", required=True, help="Job payload as JSON string")
    submit_parser.add_argument("--mode", required=True, choices=["thread", "process", "async"], help="Execution mode")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check job status")
    status_parser.add_argument("--job-id", required=True, help="Job identifier")
    
    # Cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a job")
    cancel_parser.add_argument("--job-id", required=True, help="Job identifier")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List jobs")
    list_parser.add_argument("--limit", type=int, default=100, help="Maximum number of jobs to list")
    list_parser.add_argument("--status", help="Filter by status")
    
    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Run daemon mode")
    daemon_parser.add_argument("--poll-interval", type=float, default=0.1, help="Polling interval in seconds")
    daemon_parser.add_argument("--log-level", default="info", help="Logging level")
    
    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Display metrics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create engine
    engine = create_engine(args.state_db)
    
    # Route to command handler
    if args.command == "submit":
        return cmd_submit(args, engine)
    elif args.command == "status":
        return cmd_status(args, engine)
    elif args.command == "cancel":
        return cmd_cancel(args, engine)
    elif args.command == "list":
        return cmd_list(args, engine)
    elif args.command == "daemon":
        return cmd_daemon(args, engine)
    elif args.command == "metrics":
        return cmd_metrics(args, engine)
    else:
        print(f"[ERROR] Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
