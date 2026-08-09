# routers/users.py
from fastapi import APIRouter, Depends, Response, status, HTTPException, Query, UploadFile, Form, File
from sqlalchemy.orm import Session
from .. import schemas, models, utils, oauth2
from ..database import get_db
from typing import List, Optional
from sqlalchemy.sql import func

import cloudinary.uploader
router = APIRouter(
    prefix="/api/v1/users",
    tags=["User Management"]
)

@router.get("/me", response_model=schemas.UserOut) # Assuming you have a UserOut schema
def get_current_user(current_user: models.Users = Depends(oauth2.get_current_user)):
    """
    Returns the profile of the currently logged-in admin.
    oauth2.get_current_user will automatically verify the token.
    """
    return current_user