import signal
import sys

from . import create_app
from .services.job_queue import worker_loop

_shutdown_requested = False


def _handle_signal(signum, frame):
    """Signal handler for graceful shutdown."""
    global _shutdown_requested
    _shutdown_requested = True
    print(f"\nShutdown signal received ({signal.Signals(signum).name}). "
          "Finishing current job and exiting...")


def main():
    # Register signal handlers before entering the loop
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    app = create_app()
    with app.app_context():
        print("SpecForge worker started. Press Ctrl+C to stop gracefully.")
        worker_loop(shutdown_flag=lambda: _shutdown_requested)


if __name__ == "__main__":
    main()
