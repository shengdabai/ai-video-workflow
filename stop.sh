#!/bin/bash
pkill -f "orchestrator.worker" 2>/dev/null
pkill -f "uvicorn api.app:app" 2>/dev/null
pkill -f "next dev" 2>/dev/null
echo "✓ 所有服务已停止"
