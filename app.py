import os

from specforge import create_app

app = create_app()


if __name__ == "__main__":
    port = app.config["PORT"]
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    print(f"SpecForge running on http://localhost:{port}")
    print(f"   OpenRouter API:  {'[OK]' if app.config['OPENROUTER_API_KEY'] else '[MISSING]'}")
    print(f"   Quota Mode:      {app.config.get('QUOTA_ENFORCEMENT', 'strict')}")
    print(f"   Debug Mode:      {debug}")

    if app.config.get("QUOTA_ENFORCEMENT") == "off":
        print("   [WARNING] Quota enforcement is OFF — do not use in production!")
    if not os.environ.get("SECRET_KEY"):
        print("   [WARNING] SECRET_KEY is not set in the environment. A random key is being used — sessions will not survive restarts.")

    app.run(debug=debug, port=port, host="0.0.0.0")  # nosec B104 — required for Docker
