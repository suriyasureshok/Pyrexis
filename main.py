"""
main.py

Entry point for PYREXIS job execution engine.

This module provides a convenient entry point for running PYREXIS:
- CLI mode: Run commands via api.cli
- Daemon mode: Start background engine daemon
- Signal handling: Graceful shutdown on SIGINT/SIGTERM

Usage:
    # Run CLI commands
    python main.py submit --job-id task-1 --priority 5 --payload '{"type": "example"}'
    python main.py status --job-id task-1
    python main.py list
    python main.py daemon

    # Or import programmatically
    from main import create_engine
    engine = create_engine()
    engine.submit_job(job)
"""

import sys
import signal
from typing import Optional

from api.cli import main as cli_main
from core.engine import Engine
from core.scheduler import Scheduler
from core.executor import ExecutorRouter
from storage.state import StateStore
from utils.shutdown import ShutdownCoordinator
from utils.logging import setup_logging


def create_engine(
    state_db_path: str = "./pyrexis_state.db",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
) -> Engine:
    """
    Factory function to create a configured Engine instance.

    Args:
        state_db_path: Path to state database file.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional log file path.

    Returns:
        Configured Engine instance.

    Example:
        >>> engine = create_engine()
        >>> job = Job(job_id="test-1", priority=5, payload={"type": "example"})
        >>> engine.submit_job(job)
        >>> engine.run_loop()
    """
    # Setup logging
    setup_logging(level=log_level, log_file=log_file)

    # Create components
    scheduler = Scheduler()
    executor = ExecutorRouter()
    state_store = StateStore(state_db_path)
    shutdown_coordinator = ShutdownCoordinator()

    # Create engine
    engine = Engine(
        scheduler=scheduler,
        executor=executor,
        state_store=state_store,
        shutdown_coordinator=shutdown_coordinator,
    )

    return engine


def run_daemon(
    state_db_path: str = "./pyrexis_state.db",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    poll_interval: float = 0.1,
) -> int:
    """
    Run PYREXIS as a daemon with signal handling.

    Args:
        state_db_path: Path to state database file.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional log file path.
        poll_interval: Polling interval in seconds when no jobs available.

    Returns:
        Exit code (0 for success, 1 for failure).

    Example:
        >>> run_daemon(log_level="DEBUG", log_file="pyrexis.log")
    """
    import time

    try:
        print("🚀 Starting PYREXIS daemon...")
        
        # Create engine
        engine = create_engine(
            state_db_path=state_db_path,
            log_level=log_level,
            log_file=log_file,
        )

        # Setup signal handlers
        shutdown_coordinator = engine._shutdown

        def signal_handler(signum, frame):
            sig_name = signal.Signals(signum).name
            print(f"\n🛑 Received {sig_name}, initiating graceful shutdown...")
            shutdown_coordinator.initiate_shutdown()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run main loop
        print("✅ Daemon started. Press Ctrl+C to stop.\n")
        
        jobs_processed = 0
        while not shutdown_coordinator.should_shutdown():
            result = engine.run_next()
            if result:
                jobs_processed += 1
            else:
                time.sleep(poll_interval)

        print(f"\n✅ Daemon stopped gracefully. Jobs processed: {jobs_processed}")
        return 0

    except Exception as e:
        print(f"❌ Daemon failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def main():
    """
    Main entry point.

    Routes to CLI if arguments provided, otherwise prints help.
    """
    if len(sys.argv) == 1:
        # No arguments - print help
        print("PYREXIS - Concurrent Job Execution Engine")
        print("\nUsage:")
        print("  python main.py <command> [options]")
        print("\nCommands:")
        print("  submit    Submit a new job")
        print("  status    Get job status")
        print("  cancel    Cancel a job")
        print("  list      List recent jobs")
        print("  monitor   Real-time monitoring")
        print("  daemon    Start engine daemon")
        print("  metrics   Display metrics")
        print("\nFor detailed help:")
        print("  python main.py --help")
        return 0

    # Delegate to CLI
    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
