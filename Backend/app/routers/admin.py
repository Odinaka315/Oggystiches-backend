from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Adjust these imports based on your actual project structure
from ..database import get_db

from .. import models, schemas, oauth2

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin Dashboard"]
)



# 2. The secure endpoint
@router.get("/metrics", response_model=schemas.DashboardMetricsOut)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(oauth2.get_current_user) # Secures the route
):
    # Query 1: Total count of all products in the database
    total_products = db.query(models.Product).count()
    
    # Query 2: Total count of products where is_featured is True
    featured_products = db.query(models.Product).filter(models.Product.is_featured == True).count()
    
    # Query 3: Total count of unread messages. 
    # (Assuming your ContactMessage model has a boolean field named 'is_read')
    unread_inquiries = db.query(models.ContactMessage).filter(models.ContactMessage.is_read == False).count()
    
    return schemas.DashboardMetricsOut(
        totalProducts=total_products,
        featuredProducts=featured_products,
        unreadInquiries=unread_inquiries
    )