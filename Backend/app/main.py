from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from .celery_worker import celery_app
from .config import setup_cloudinary

setup_cloudinary()
app = FastAPI(title="TixODI backend API")

from .routers import auth, contacts, products, users, admin
app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(admin.router)

origins = [
    "https://oggystiches.vercel.app", # Explicitly add your frontend URL
    # "https://your-production-domain.com" 
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
async def root():
    return {"message": "Hello World"}