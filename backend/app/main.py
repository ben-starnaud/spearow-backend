from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import login_routes, report_routes, upload_routes, home_routes, admin_routes
from app.db import connect_to_mongo, close_mongo_connection
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)

# Get the absolute path to the 'backend' directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define the path to the 'uploaded_ids' directory inside 'backend'
uploaded_ids_dir = os.path.join(backend_dir, "uploaded_ids")

# Check if the 'uploaded_ids' directory exists, and create it if it doesn't
if not os.path.isdir(uploaded_ids_dir):
    try:
        os.makedirs(uploaded_ids_dir)
        print(f"The 'uploaded_ids' directory has been created at: {uploaded_ids_dir}")
    except OSError as e:
        print(f"Error creating 'uploaded_ids' directory: {e}")
else:
    print(f"The 'uploaded_ids' directory already exists at: {uploaded_ids_dir}")

# Mount the directory to serve the files under the /uploaded_ids endpoint
app.mount("/uploaded_ids", StaticFiles(directory=uploaded_ids_dir), name="uploaded_ids")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your routes
app.include_router(login_routes.router)
app.include_router(report_routes.router)
app.include_router(upload_routes.router)
app.include_router(home_routes.router)
app.include_router(admin_routes.router)
