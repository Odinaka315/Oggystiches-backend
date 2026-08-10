from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr
from ..database import get_db
from .. import models, schemas, oauth2
from ..tasks import  send_admin_email

router = APIRouter(
    prefix="/api/v1/contact-messages", 
    tags=["Contact Messages"]
)

# --- The Endpoint ---
@router.get("/", response_model=List[schemas.ContactMessageOut])
def get_contact_messages(
    inquiry_type: Optional[models.InquiryType] = Query(None, description="Filter by general or bespoke_dress"),
    specific_date: Optional[date] = Query(None, description="Fetch messages for an exact date (YYYY-MM-DD)"),
    start_date: Optional[datetime] = Query(None, description="Fetch messages starting from this date/time"),
    end_date: Optional[datetime] = Query(None, description="Fetch messages up to this date/time"),
    db: Session = Depends(get_db),
    current_user: Optional[models.Users] = Depends(oauth2.get_current_user)
):
    """
    Fetch contact messages with optional filters.
    If no filters are provided, fetches all messages.
    """
    # 1. Start with a base query
    query = db.query(models.ContactMessage)

    # 2. Filter by Inquiry Type if provided
    if inquiry_type:
        query = query.filter(models.ContactMessage.inquiry_type == inquiry_type)

    # 3. Handle Date/Time Filtering
    if specific_date:
        # If specific_date is provided, we cast the TIMESTAMP to a date and match it
        query = query.filter(func.date(models.ContactMessage.created_at) == specific_date)
    else:
        # Otherwise, apply the start_date and/or end_date range if they exist
        if start_date:
            query = query.filter(models.ContactMessage.created_at >= start_date)
        if end_date:
            query = query.filter(models.ContactMessage.created_at <= end_date)

    # 4. Order by newest first (optional but highly recommended for an admin panel)
    query = query.order_by(models.ContactMessage.created_at.desc())

    # 5. Execute and return
    messages = query.all()
    
    return messages


@router.post("/", response_model=schemas.ContactMessageOut, status_code=status.HTTP_201_CREATED)
def create_contact_message(
    message_in: schemas.ContactMessageCreate,
    background_tasks: BackgroundTasks, # 2. Inject it into the endpoint
    db: Session = Depends(get_db)
):
    """
    Creates a new contact message and triggers an email natively via FastAPI.
    """
    # Save the record to the database
    new_message = models.ContactMessage(
        first_name=message_in.first_name,
        last_name=message_in.last_name,
        email=message_in.email,
        message=message_in.message,
        inquiry_type=message_in.inquiry_type
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # 3. Trigger the email task natively! 
    # (Just make sure your send_admin_email function no longer has the @shared_task decorator)
    background_tasks.add_task(send_admin_email, new_message.id)

    return new_message

@router.patch("/{id}/read", response_model=schemas.ContactMessageOut)
def mark_message_as_read(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(oauth2.get_current_user)
):
    """
    Mark a specific contact message as read.
    """
    message_query = db.query(models.ContactMessage).filter(models.ContactMessage.id == id)
    message = message_query.first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Contact message with id {id} not found"
        )

    # Update the is_read status
    message_query.update({"is_read": True}, synchronize_session=False)
    db.commit()

    return message_query.first()