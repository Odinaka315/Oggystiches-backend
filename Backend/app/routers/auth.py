from fastapi import APIRouter, Depends, status, HTTPException, Query, Response, Cookie
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import schemas, models, utils, oauth2
from ..database import get_db
import secrets
from google.oauth2 import id_token
from google.auth.transport import requests
from ..tasks import  send_password_reset_email
from ..config import settings
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

@router.post("/login", response_model=schemas.Token)
def login(
    response: Response, # 👇 Inject Response to set cookies
    user_credentials: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = db.query(models.Users).filter(models.Users.email == user_credentials.username).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    if not utils.verify(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    access_token = oauth2.create_access_token(data={"user_id": user.id})
    refresh_token = oauth2.create_refresh_token(data={"user_id": user.id}) # 👇 Generate refresh token

    # 👇 Attach the refresh token as an HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True, # Ensure this is True in production with HTTPS
        samesite="lax",
        max_age=7 * 24 * 60 * 60 # 7 days in seconds
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=schemas.Token)
def refresh_token(
    refresh_token: str = Cookie(None), # Auto-extracts the cookie named "refresh_token"
    db: Session = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Refresh token missing. Please log in again."
        )

    # Verify the refresh token (Requires a verify_refresh_token function in oauth2.py)
    user_id = oauth2.verify_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or expired refresh token. Please log in again."
        )

    # Generate a fresh 1-hour access token
    new_access_token = oauth2.create_access_token(data={"user_id": user_id})

    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    payload: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Accepts an email address and triggers a password reset email if the account exists.
    Always returns a generic success message to prevent email enumeration attacks.
    """
    user = db.query(models.Users).filter(models.Users.email == payload.email).first()

    # If user exists, generate the 15-minute token and fire the Celery task!
    if user:
        token = oauth2.create_password_reset_token(user.id)
        send_password_reset_email.delay(user.id, token)

    # ANTI-ENUMERATION: Always return this exact message regardless of whether user exists!
    return {
        "status": "success",
        "message": "✉️ If an account with that email exists, a password reset link has been sent to your inbox."
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def execute_password_reset(
    payload: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Validates the 15-minute reset token and hashes/saves the new password.
    """
    # 1. Decode and validate the token
    user_id = oauth2.verify_password_reset_token(payload.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="❌ The password reset link is invalid or has expired (links expire after 15 minutes)."
        )

    # 2. Fetch the target user
    user = db.query(models.Users).filter(models.Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # 3. Hash the new password and overwrite the old one
    hashed_new_password = utils.hash(payload.new_password)
    user.password = hashed_new_password

    # 4. Save changes to database
    db.commit()

    return {
        "status": "success",
        "message": "✅ Your password has been successfully reset! You can now log in with your new credentials."
    }

@router.patch("/me/change-password", status_code=status.HTTP_200_OK)
def change_user_password(
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(oauth2.get_current_user) # <-- 1. Identity comes ONLY from JWT!
):
    """
    Authenticated endpoint for logged-in users to update their password from profile settings.
    Strictly requires verification of their old password to prevent session hijacking.
    """
    # 2. Verify that the provided old_password matches the hash in the database
    if not utils.verify(payload.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="❌ Incorrect current password. Please try again or use the 'Forgot Password' link if you are locked out."
        )

    # 3. Prevent reusing the exact same password
    if utils.verify(payload.new_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="❌ Your new password cannot be the same as your old password."
        )

    # 4. Hash and save the new password
    current_user.password = utils.hash(payload.new_password)
    db.commit()

    # PRO-TIP: Send a security alert email via Celery here!
    # "Hi Odinaka, your Ticketing Platform password was just changed. If this wasn't you, click here immediately!"

    return {"status": "success", "message": "✅ Password updated successfully!"}