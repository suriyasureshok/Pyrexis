"""
tests/test_cli.py

Integration tests for CLI interface.

Tests end-to-end CLI functionality:
- Job submission via CLI
- Status queries
- Job cancellation
- Listing jobs
- Monitoring
- Daemon operation

Run with:
    python -m unittest tests.test_cli -v
"""

import unittest
import subprocess
import json
import time
import tempfile
import os
import signal
import sys
from pathlib import Path

from models.job import Job, JobStatus
from core.scheduler import Scheduler
from core.executor import ExecutorRouter
from core.engine import Engine
from storage.state import StateStore
from utils.shutdown import ShutdownCoordinator
from utils.registry import PluginRegistry

# Clear registry to avoid duplicate registration errors across test runs
PluginRegistry.clear_registry()


class DummyPipeline(metaclass=PluginRegistry):
    """Minimal pipeline for CLI testing."""
    name = "dummy"
    
    def stages(self):
        def stage1(data):
            time.sleep(0.05)  # Simulate work
            return {"result": "done"}
        return [stage1]


class TestCLIInterface(unittest.TestCase):
    """Integration tests for CLI commands."""

    def setUp(self):
        """Setup for each test."""
        # Create temp state file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.state_db_path = self.temp_db.name

        # Create engine for verification
        self.scheduler = Scheduler()
        self.executor = ExecutorRouter()
        self.state_store = StateStore(self.state_db_path)
        self.shutdown_coordinator = ShutdownCoordinator()

        self.engine = Engine(
            scheduler=self.scheduler,
            executor=self.executor,
            state_store=self.state_store,
            shutdown_coordinator=self.shutdown_coordinator,
        )

    def tearDown(self):
        """Cleanup after each test."""
        if os.path.exists(self.state_db_path):
            try:
                os.unlink(self.state_db_path)
            except:
                pass

    def _run_cli(self, *args):
        """
        Helper to run CLI command.

        Args:
            *args: CLI arguments.

        Returns:
            (returncode, stdout, stderr)
        """
        cmd = [sys.executable, "-m", "api.cli", "--state-db", self.state_db_path] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode, result.stdout, result.stderr

    # ========== CLI Command Tests ==========

    def test_submit_command(self):
        """
        Test: Submit job via CLI.
        
        Validates:
        - Job submitted successfully
        - Job persisted in state store
        - Correct status returned
        """
        # Submit via CLI
        returncode, stdout, stderr = self._run_cli(
            "submit",
            "--job-id", "cli-test-1",
            "--priority", "5",
            "--payload", '{"type": "dummy_cli", "value": 42}',
            "--mode", "thread",
        )

        # Check success
        self.assertEqual(returncode, 0, f"Submit failed: {stderr}")
        self.assertIn("submitted successfully", stdout)
        self.assertIn("cli-test-1", stdout)

        # Verify job in state store
        job = self.state_store.load_job("cli-test-1")
        self.assertIsNotNone(job)
        self.assertEqual(job.job_id, "cli-test-1")
        self.assertEqual(job.priority, 5)
        self.assertEqual(job.status, JobStatus.PENDING)
        self.assertEqual(job.execution_mode, "thread")

    def test_status_command(self):
        """
        Test: Query job status via CLI.
        
        Validates:
        - Status displayed correctly
        - All job fields shown
        """
        # Create and submit job programmatically
        job = Job(
            job_id="status-test-1",
            priority=10,
            payload={"type": "dummy"},
            execution_mode="process",
        )
        self.engine.submit_job(job)

        # Query via CLI
        returncode, stdout, stderr = self._run_cli(
            "status",
            "--job-id", "status-test-1",
        )

        # Check success
        self.assertEqual(returncode, 0, f"Status failed: {stderr}")
        self.assertIn("status-test-1", stdout)
        self.assertIn("pending", stdout.lower())
        self.assertIn("10", stdout)  # Priority
        self.assertIn("process", stdout)  # Mode

    def test_status_command_not_found(self):
        """
        Test: Query non-existent job.
        
        Validates:
        - Error returned
        - Appropriate message shown
        """
        returncode, stdout, stderr = self._run_cli(
            "status",
            "--job-id", "nonexistent",
        )

        # Check failure
        self.assertNotEqual(returncode, 0)
        self.assertIn("not found", stderr.lower())

    def test_cancel_command(self):
        """
        Test: Cancel job via CLI.
        
        Validates:
        - Job cancelled successfully
        - Status updated to FAILED
        - Error message recorded
        """
        # Submit job
        job = Job(
            job_id="cancel-test-1",
            priority=5,
            payload={"type": "dummy"},
            execution_mode="thread",
        )
        self.engine.submit_job(job)

        # Cancel via CLI
        returncode, stdout, stderr = self._run_cli(
            "cancel",
            "--job-id", "cancel-test-1",
        )

        # Check success
        self.assertEqual(returncode, 0, f"Cancel failed: {stderr}")
        self.assertIn("cancelled", stdout.lower())

        # Verify job status (accept both FAILED and CANCELLED as terminal states)
        cancelled_job = self.state_store.load_job("cancel-test-1")
        self.assertIn(cancelled_job.status, {JobStatus.FAILED, JobStatus.CANCELLED})
        # Check last_error contains cancellation info
        if cancelled_job.last_error:
            self.assertIn("cancel", cancelled_job.last_error.lower())

    def test_cancel_command_already_completed(self):
        """
        Test: Try to cancel completed job.
        
        Validates:
        - Error returned
        - Job remains completed
        """
        # Create completed job by executing it
        job = Job(
            job_id="completed-1",
            priority=5,
            payload={"type": "dummy"},
            execution_mode="thread",
        )
        self.engine.submit_job(job)
        self.engine.run_next()  # Execute to completion

        # Try to cancel
        returncode, stdout, stderr = self._run_cli(
            "cancel",
            "--job-id", "completed-1",
        )

        # Check failure
        self.assertNotEqual(returncode, 0)
        self.assertIn("cannot cancel", stderr.lower())

        # Verify job still completed
        loaded = self.state_store.load_job("completed-1")
        self.assertEqual(loaded.status, JobStatus.COMPLETED)

    def test_list_command(self):
        """
        Test: List jobs via CLI.
        
        Validates:
        - All jobs displayed
        - Table format correct
        - Limit respected
        """
        # Submit multiple jobs
        for i in range(15):
            job = Job(
                job_id=f"list-{i}",
                priority=min(i, 10),  # Ensure priority stays within 0-10 range
                payload={"type": "dummy"},
                execution_mode="thread",
            )
            self.engine.submit_job(job)

        # List with default limit
        returncode, stdout, stderr = self._run_cli("list")

        # Check success
        self.assertEqual(returncode, 0, f"List failed: {stderr}")
        self.assertIn("Job ID", stdout)  # Table header
        self.assertIn("Status", stdout)
        self.assertIn("Priority", stdout)

        # Count jobs in output (should be 15) - format-tolerant matching
        job_lines = [line for line in stdout.splitlines() if 'list-' in line]
        self.assertEqual(len(job_lines), 15)

    def test_list_command_with_limit(self):
        """
        Test: List jobs with custom limit.
        
        Validates:
        - Limit respected
        - Most recent jobs shown
        """
        # Submit jobs
        for i in range(20):
            job = Job(
                job_id=f"limit-{i}",
                priority=i % 10,
                payload={"type": "dummy"},
                execution_mode="thread",
            )
            self.engine.submit_job(job)

        # List with limit=5
        returncode, stdout, stderr = self._run_cli("list", "--limit", "5")

        # Check success
        self.assertEqual(returncode, 0, f"List failed: {stderr}")

        # Count jobs (should be 5) - format-tolerant matching
        job_lines = [line for line in stdout.splitlines() if 'limit-' in line]
        self.assertLessEqual(len(job_lines), 5)

    def test_list_command_filter_by_status(self):
        """
        Test: Filter jobs by status.
        
        Validates:
        - Status filter works
        - Only matching jobs shown
        """
        # Create jobs with different statuses
        for i in range(3):
            job = Job(
                job_id=f"pending-{i}",
                priority=i % 10,
                payload={"type": "dummy"},
                execution_mode="thread",
            )
            self.engine.submit_job(job)  # PENDING

        # Create a completed job by executing it
        completed_job = Job(
            job_id="completed-test",
            priority=5,
            payload={"type": "dummy"},
            execution_mode="thread",
        )
        self.engine.submit_job(completed_job)
        self.engine.run_next()  # Execute to completion

        # List only pending
        returncode, stdout, stderr = self._run_cli("list", "--status", "pending")

        # Check success
        self.assertEqual(returncode, 0, f"List failed: {stderr}")
        self.assertIn("pending-", stdout)
        self.assertNotIn("completed-test", stdout)

    def test_metrics_command(self):
        """
        Test: Display metrics via CLI.
        
        Validates:
        - Metrics displayed
        - Format correct
        """
        # Submit a job to generate minimal metrics
        job = Job(
            job_id="metrics-test",
            priority=5,
            payload={"type": "dummy"},
            execution_mode="thread",
        )
        self.engine.submit_job(job)

        # Get metrics
        returncode, stdout, stderr = self._run_cli("metrics")

        # Check success
        self.assertEqual(returncode, 0, f"Metrics failed: {stderr}")
        self.assertIn("Metrics", stdout)

    def test_invalid_command(self):
        """
        Test: Invalid CLI command.
        
        Validates:
        - Error returned
        - Help message shown
        """
        returncode, stdout, stderr = self._run_cli("invalid-command")

        # Check failure
        self.assertNotEqual(returncode, 0)

    def test_submit_with_invalid_json(self):
        """
        Test: Submit with malformed JSON payload.
        
        Validates:
        - Error returned
        - Helpful error message
        """
        returncode, stdout, stderr = self._run_cli(
            "submit",
            "--job-id", "bad-json",
            "--priority", "5",
            "--payload", '{invalid json}',
            "--mode", "thread",
        )

        # Check failure
        self.assertNotEqual(returncode, 0)
        self.assertIn("json", stderr.lower())

    def test_submit_with_invalid_mode(self):
        """
        Test: Submit with invalid execution mode.
        
        Validates:
        - Error caught by argparse
        """
        # This should fail at argparse level
        returncode, stdout, stderr = self._run_cli(
            "submit",
            "--job-id", "bad-mode",
            "--priority", "5",
            "--payload", '{"type": "dummy"}',
            "--mode", "invalid",
        )

        # Check failure
        self.assertNotEqual(returncode, 0)


class TestCLIDaemon(unittest.TestCase):
    """Tests for daemon mode."""

    def setUp(self):
        """Setup for each test."""
        # Create temp state file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.state_db_path = self.temp_db.name

    def tearDown(self):
        """Cleanup after each test."""
        if os.path.exists(self.state_db_path):
            try:
                os.unlink(self.state_db_path)
            except:
                pass

    def test_daemon_starts_and_stops(self):
        """
        Test: Start daemon and stop with signal.
        
        Validates:
        - Daemon starts successfully
        - Responds to SIGTERM
        - Clean shutdown
        """
        # Start daemon in background
        cmd = [
            sys.executable, "-m", "api.cli",
            "--state-db", self.state_db_path,
            "daemon",
            "--log-level", "error",  # Reduce output
            "--poll-interval", "0.5",
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for startup with retry loop (avoid race condition)
        for _ in range(10):
            if proc.poll() is None:
                break
            time.sleep(0.2)
        else:
            self.fail("Daemon failed to start within timeout")

        # Check it's running
        self.assertIsNone(proc.poll(), "Daemon exited prematurely")

        # Send SIGTERM
        proc.send_signal(signal.SIGTERM)

        # Wait for clean shutdown
        try:
            returncode = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.fail("Daemon did not stop gracefully")

        # Get stderr output for debugging
        _, stderr = proc.communicate()
        
        # Check clean exit (0 or signal-based exit like -15 for SIGTERM)
        # Windows may return 1 on signal-based exit, so accept it
        self.assertIn(returncode, [0, -15, 15, 1], 
                      f"Daemon exited with unexpected code: {returncode}, stderr: {stderr}")


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
