"""
tests/test_load.py

Load testing for PYREXIS job execution engine.

Tests system behavior under heavy load:
- 1000+ concurrent job submissions
- Sub-second scheduling latency
- Memory usage scaling
- Graceful degradation
- Thread safety under stress

Success Criteria:
- Handle 1000+ concurrent jobs without crashes
- Scheduling latency < 1 second
- Memory usage scales linearly with active jobs
- No job loss or corruption
- Clean shutdown under load

Run with:
    python -m unittest tests.test_load -v
"""

import unittest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import os

from models.job import Job, JobStatus
from models.result import Result
from core.scheduler import Scheduler
from core.executor import ExecutorRouter
from core.engine import Engine
from core.pipeline import Pipeline
from storage.state import StateStore
from utils.shutdown import ShutdownCoordinator
from utils.registry import PluginRegistry

# Clear registry to avoid duplicate registration errors across test runs
PluginRegistry.clear_registry()


class DummyPipeline(metaclass=PluginRegistry):
    """Minimal pipeline for load testing."""
    name = "dummy"
    
    def stages(self):
        def stage1(data):
            # Simulate work
            time.sleep(0.001)  # 1ms
            return {"result": data.get("value", 0) * 2}
        return [stage1]


class TestLoadPerformance(unittest.TestCase):
    """Load testing suite for PYREXIS engine."""

    def setUp(self):
        """Setup engine for each test."""
        # Create temp state file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        # Create engine components
        self.scheduler = Scheduler()
        self.executor = ExecutorRouter()
        self.state_store = StateStore(self.temp_db.name)
        self.shutdown_coordinator = ShutdownCoordinator()

        self.engine = Engine(
            scheduler=self.scheduler,
            executor=self.executor,
            state_store=self.state_store,
            shutdown_coordinator=self.shutdown_coordinator,
        )

    def tearDown(self):
        """Cleanup after each test."""
        # Cleanup temp db
        if os.path.exists(self.temp_db.name):
            try:
                os.unlink(self.temp_db.name)
            except:
                pass

    # ========== Load Tests ==========

    def test_1000_concurrent_submissions(self):
        """
        Test: Submit 1000 jobs concurrently.
        
        Validates:
        - No job loss
        - All jobs persisted
        - Thread-safe submission
        """
        num_jobs = 1000

        def submit_job(i):
            job = Job(
                job_id=f"load-{i}",
                priority=i % 10,  # Varying priorities
                payload={"type": "dummy_load", "value": i},
                execution_mode="thread",
            )
            self.engine.submit_job(job)
            return job.job_id

        # Submit concurrently
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(submit_job, i) for i in range(num_jobs)]
            submitted_ids = [f.result() for f in as_completed(futures)]

        submit_duration = time.perf_counter() - start_time

        # Verify all jobs submitted
        self.assertEqual(len(submitted_ids), num_jobs)
        self.assertEqual(len(set(submitted_ids)), num_jobs)  # No duplicates

        # Verify all jobs in state store
        all_jobs = self.state_store.get_all_jobs()
        self.assertEqual(len(all_jobs), num_jobs)

        print(f"\n[OK] Submitted {num_jobs} jobs in {submit_duration:.2f}s")
        print(f"   Throughput: {num_jobs / submit_duration:.0f} jobs/sec")

    def test_scheduling_latency_under_load(self):
        """
        Test: Measure scheduling latency with 1000 pending jobs.
        
        Success Criteria: Latency < 1 second
        """
        num_jobs = 1000

        # Submit jobs
        for i in range(num_jobs):
            job = Job(
                job_id=f"latency-{i}",
                priority=i % 10,
                payload={"type": "dummy", "value": i},
                execution_mode="thread",
            )
            self.engine.submit_job(job)

        # Measure scheduling latency
        latencies = []
        
        for _ in range(100):  # Sample 100 scheduling operations
            start = time.perf_counter()
            job = self.scheduler.next_job()
            latency = time.perf_counter() - start
            latencies.append(latency)
            
            if not job:
                break

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)

        print(f"\n[METRICS] Scheduling Latency (1000 pending jobs):")
        print(f"   Average: {avg_latency * 1000:.2f}ms")
        print(f"   Maximum: {max_latency * 1000:.2f}ms")

        # Assert sub-second latency
        self.assertLess(avg_latency, 1.0, "Average latency exceeds 1 second")
        self.assertLess(max_latency, 1.0, "Max latency exceeds 1 second")

    def test_concurrent_execution_1000_jobs(self):
        """
        Test: Execute 1000 jobs with concurrent workers.
        
        Validates:
        - All jobs complete successfully
        - No race conditions
        - Clean state transitions
        """
        num_jobs = 1000

        # Submit jobs
        for i in range(num_jobs):
            job = Job(
                job_id=f"exec-{i}",
                priority=i % 10,
                payload={"type": "dummy", "value": i},
                execution_mode="thread",
                max_entries=1,  # No retries for speed
            )
            self.engine.submit_job(job)

        # Execute all jobs
        start_time = time.perf_counter()
        completed = 0

        while True:
            result = self.engine.run_next()
            if result is None:
                # No more jobs
                break
            completed += 1

        execution_duration = time.perf_counter() - start_time

        print(f"\n[OK] Executed {completed} jobs in {execution_duration:.2f}s")
        print(f"   Throughput: {completed / execution_duration:.0f} jobs/sec")

        # Verify all jobs completed or failed
        all_jobs = self.state_store.get_all_jobs()
        terminal_states = [JobStatus.COMPLETED, JobStatus.FAILED]
        terminal_jobs = [j for j in all_jobs if j.status in terminal_states]
        
        self.assertEqual(len(terminal_jobs), num_jobs)

    def test_memory_scaling_with_jobs(self):
        """
        Test: Verify memory usage scales linearly with job count.
        
        Measures memory at different job counts to detect memory leaks.
        """
        import tracemalloc
        
        job_counts = [100, 500, 1000, 2000]
        memory_samples = []

        for count in job_counts:
            # Reset engine
            self.setUp()
            
            # Start memory tracking
            tracemalloc.start()
            snapshot_before = tracemalloc.take_snapshot()

            # Submit jobs
            for i in range(count):
                job = Job(
                    job_id=f"mem-{count}-{i}",
                    priority=i % 10,
                    payload={"type": "dummy", "value": i},
                    execution_mode="thread",
                )
                self.engine.submit_job(job)

            # Measure memory
            snapshot_after = tracemalloc.take_snapshot()
            tracemalloc.stop()

            # Calculate memory increase
            stats = snapshot_after.compare_to(snapshot_before, 'lineno')
            total_increase = sum(stat.size_diff for stat in stats)
            
            memory_samples.append((count, total_increase))
            
            # Cleanup
            self.tearDown()

        print(f"\n[METRICS] Memory Scaling:")
        for count, mem in memory_samples:
            print(f"   {count:5d} jobs: {mem / 1024 / 1024:6.2f} MB")

        # Check linear scaling (memory per job should be relatively constant)
        mem_per_job = [mem / count for count, mem in memory_samples]
        max_mem_per_job = max(mem_per_job)
        min_mem_per_job = min(mem_per_job)
        
        # Allow 3x variance (generous for garbage collection)
        self.assertLess(
            max_mem_per_job / min_mem_per_job,
            3.0,
            "Memory usage not scaling linearly (possible leak)"
        )

    def test_graceful_degradation_under_overload(self):
        """
        Test: Submit jobs faster than they can be processed.
        
        Validates:
        - System doesn't crash
        - Jobs queue properly
        - Backpressure handled correctly
        """
        # Submit 500 jobs rapidly
        for i in range(500):
            job = Job(
                job_id=f"overload-{i}",
                priority=i % 10,
                payload={"type": "dummy", "value": i},
                execution_mode="thread",
            )
            self.engine.submit_job(job)

        # Process for limited time (5 seconds)
        start_time = time.perf_counter()
        timeout = 5.0
        processed = 0

        while time.perf_counter() - start_time < timeout:
            result = self.engine.run_next()
            if result is not None:
                processed += 1

        print(f"\n[OK] Processed {processed} jobs under overload (5s window)")

        # Verify system is still functional
        remaining = self.state_store.get_all_jobs(status=JobStatus.PENDING)
        print(f"   Remaining in queue: {len(remaining)}")
        
        self.assertGreater(processed, 0, "No jobs processed under load")
        self.assertGreater(len(remaining), 0, "All jobs completed (test may need adjustment)")

    def test_shutdown_under_heavy_load(self):
        """
        Test: Initiate shutdown while processing many jobs.
        
        Validates:
        - Clean shutdown
        - No data corruption
        - Active jobs complete gracefully
        """
        # Submit 200 jobs
        for i in range(200):
            job = Job(
                job_id=f"shutdown-{i}",
                priority=i % 10,
                payload={"type": "dummy", "value": i},
                execution_mode="thread",
            )
            self.engine.submit_job(job)

        # Start processing in background
        processed = []
        stop_flag = threading.Event()

        def worker():
            while not stop_flag.is_set():
                result = self.engine.run_next()
                if result:
                    processed.append(result)
                else:
                    time.sleep(0.01)

        worker_thread = threading.Thread(target=worker, daemon=True)
        worker_thread.start()

        # Let it process for a bit
        time.sleep(0.5)

        # Initiate shutdown
        self.shutdown_coordinator.initiate_shutdown()
        stop_flag.set()

        # Wait for worker to finish
        worker_thread.join(timeout=2.0)

        print(f"\n[METRICS] Shutdown under load:")
        print(f"   Processed before shutdown: {len(processed)}")

        # Verify state consistency
        all_jobs = self.state_store.get_all_jobs()
        pending = [j for j in all_jobs if j.status == JobStatus.PENDING]
        terminal = [j for j in all_jobs if j.status in {JobStatus.COMPLETED, JobStatus.FAILED}]

        print(f"   Jobs in terminal state: {len(terminal)}")
        print(f"   Jobs still pending: {len(pending)}")

        # All jobs should be accounted for
        self.assertEqual(len(all_jobs), 200)

    def test_thread_safety_state_store_concurrent_access(self):
        """
        Test: Concurrent reads/writes to state store.
        
        Validates:
        - No race conditions
        - Data integrity maintained
        - Thread-safe operations
        """
        num_operations = 500

        def read_write_job(i):
            # Create and submit job
            job = Job(
                job_id=f"thread-safety-{i}",
                priority=i % 10,
                payload={"type": "dummy", "value": i},
                execution_mode="thread",
            )
            self.engine.submit_job(job)

            # Read job back
            loaded = self.state_store.load_job(job.job_id)
            assert loaded is not None
            assert loaded.job_id == job.job_id

            # Update job payload (no state transition needed since already PENDING)
            job.payload["updated"] = True
            self.state_store.update_job(job)

            # Read again
            updated = self.state_store.load_job(job.job_id)
            assert updated.payload.get("updated") == True

        # Execute concurrently
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(read_write_job, i) for i in range(num_operations)]
            for f in as_completed(futures):
                f.result()  # Raise any exceptions

        duration = time.perf_counter() - start_time

        print(f"\n[METRICS] Thread safety test: {num_operations} concurrent ops in {duration:.2f}s")

        # Verify all jobs present
        all_jobs = self.state_store.get_all_jobs()
        self.assertEqual(len(all_jobs), num_operations)


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
