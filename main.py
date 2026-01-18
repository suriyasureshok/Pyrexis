import signal
from utils.shutdown import ShutdownCoordinator

shutdown = ShutdownCoordinator()

signal.signal(signal.SIGINT, shutdown.initiate_shutdown)
signal.signal(signal.SIGTERM, shutdown.initiate_shutdown)