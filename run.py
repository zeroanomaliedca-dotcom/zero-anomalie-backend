import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Sur Railway, le port est fourni par la variable d'environnement PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False  # On désactive le debug en production
    )