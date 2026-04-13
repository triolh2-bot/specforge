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
    if app.config.get("SECRET_KEY") == "your-secret-key-here":
        print("   [WARNING] SECRET_KEY is the default placeholder — set a real key before deploying!")

    app.run(debug=debug, port=port, host="0.0.0.0")  # nosec B104 — required for Docker
