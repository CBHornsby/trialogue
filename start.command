#!/bin/bash
# Trialogue Launcher - macOS / Linux
# Starts backend and frontend, opens browser.

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo
echo " Starting Trialogue..."
echo

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed. Install from https://python.org or use Homebrew."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed. Install from https://nodejs.org or use Homebrew."
    exit 1
fi

# First-time backend setup
if [ ! -d "backend/venv" ]; then
    echo " First-time setup: creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    echo " Installing Python dependencies..."
    pip install -q -r requirements.txt
    cd ..
fi

# First-time frontend setup
if [ ! -d "frontend/node_modules" ]; then
    echo " First-time setup: installing frontend dependencies (this takes a minute)..."
    cd frontend
    npm install
    cd ..
fi

# Trap to clean up child processes on exit
cleanup() {
    echo
    echo " Shutting down..."
    [ ! -z "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ ! -z "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

# Start backend
echo " Starting backend on port 8000..."
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

sleep 3

# Start frontend
echo " Starting frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

sleep 5

# Open browser (macOS uses 'open', Linux uses 'xdg-open')
if command -v open &> /dev/null; then
    open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:3000
fi

echo
echo " Trialogue is running. Press Ctrl+C to stop."
echo

wait
