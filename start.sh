#!/bin/bash
cd "$(dirname "$0")"

if [ ! -f ".venv/bin/python" ]; then
    echo "Run setup first: ./setup.sh"
    exit 1
fi

echo "Starting Aurine at http://localhost:8000"
echo "Keep this terminal open. Press Ctrl+C to stop."
echo "For mobile access: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):8000"
echo ""
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
