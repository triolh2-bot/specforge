from specforge import create_app

app = create_app()


if __name__ == "__main__":
    port = app.config["PORT"]
    print(f"🔓 SpecForge running on http://localhost:{port}")
    print(f"   MiniMax OAuth: {'✓' if app.config['MINIMAX_CLIENT_ID'] else '✗'}")
    print(f"   MiniMax API Key: {'✓' if app.config['MINIMAX_API_KEY'] else '✗'}")
    app.run(debug=False, port=port, host="0.0.0.0")
