#!/bin/bash

# Start backend and frontend services

echo "🚀 Starting SuperInsight Services..."
echo ""

# Start backend in background
echo "📡 Starting Backend Service (Port 8000)..."
source venv/bin/activate
python3 -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# Wait for backend to start
sleep 3

# Start frontend in background
echo ""
echo "🎨 Starting Frontend Service (Port 5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ All services started successfully!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📍 Access URLs:"
echo "   Frontend:  http://localhost:5173"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "👤 Test Accounts:"
echo "   Admin:     admin@superinsight.com / Admin@123456"
echo "   Analyst:   analyst@superinsight.com / Analyst@123456"
echo ""
echo "Press Ctrl+C to stop all services"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Wait for both processes
wait
