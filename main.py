from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from database import client
from routes.auth import router as auth_router
from routes.emails import router as emails_router
from middleware.session_tracker import SessionTrackerMiddleware
from config import settings
from routes.google_auth import router as google_auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    yield
    # Shutdown
    print("Shutting down...")
    client.close()

app = FastAPI(title="Email Scanner API", lifespan=lifespan)

# Add middleware
app.add_middleware(SessionTrackerMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Mount static files - FIXED: Removed leading slash
static_dir = os.path.join(current_dir, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Setup templates
templates_dir = os.path.join(current_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

# Include routers
app.include_router(auth_router)
app.include_router(emails_router)
app.include_router(google_auth_router)

# Serve favicon - ADDED
@app.get("/favicon.ico")
async def favicon():
    favicon_path = os.path.join(static_dir, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    else:
        raise HTTPException(status_code=404, detail="Favicon not found")

# Serve main pages - without .html extension
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/index")
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Redirect .html requests to non-.html routes - IMPLEMENTED
@app.get("/index.html")
async def redirect_index():
    return RedirectResponse(url="/index", status_code=301)

@app.get("/login.html")
async def redirect_login():
    return RedirectResponse(url="/login", status_code=301)

@app.get("/register.html")
async def redirect_register():
    return RedirectResponse(url="/register", status_code=301)

@app.get("/Register.html")  # Handle capitalized version
async def redirect_register_cap():
    return RedirectResponse(url="/register", status_code=301)

# Cache control middleware
@app.middleware("http")
async def add_cache_control(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
