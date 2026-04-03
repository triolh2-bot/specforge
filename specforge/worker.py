from . import create_app
from .services.job_queue import worker_loop


def main():
    app = create_app()
    with app.app_context():
        worker_loop()


if __name__ == "__main__":
    main()
