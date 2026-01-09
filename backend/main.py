"""
RoleBridge Backend - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径，以便导入 config 模块
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import CORS_ORIGINS

# Initialize FastAPI app
app = FastAPI(
    title="RoleBridge API",
    description="跨职能沟通翻译助手 API",
    version="1.0.0"
)

# CORS Configuration
cors_origins = CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from api.translate import router as translate_router
from api.websocket import router as websocket_router

# Register routers
app.include_router(translate_router, prefix="/api", tags=["translate"])
app.include_router(websocket_router, prefix="/api", tags=["websocket"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "RoleBridge Backend"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RoleBridge API",
        "version": "1.0.0",
        "docs": "/docs"
    }

