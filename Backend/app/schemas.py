from typing import Optional, List, Union, Dict, Any
import uuid
from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator
from datetime import datetime
import enum
from . import  models

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    # Enforce basic password length validation at the schema level!
    new_password: str = Field(..., min_length=8, description="Must be at least 8 characters")

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

class ContactMessageOut(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    message: str
    inquiry_type: str  # Enum will be converted to string automatically
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ContactMessageCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    message: str
    inquiry_type: Optional[models.InquiryType] = models.InquiryType.GENERAL

    @field_validator('inquiry_type', mode='before')
    @classmethod
    def lowercase_inquiry_type(cls, value):
        if isinstance(value, str):
            return value.lower()
        return value


class ProductImageCreate(BaseModel):
    image_url: str
    alt_text: str
    is_primary: bool = False
    is_video_snippet: bool = False

class ProductImageOut(ProductImageCreate):
    id: int
    
    class Config:
        from_attributes = True

# --- Product Schemas ---
class ProductCreate(BaseModel):
    title: str
    description: str
    price: float
    category: models.ProductCategory = models.ProductCategory.READY_TO_WEAR
    is_featured: bool = False
    is_bespoke: bool = False
    is_active: bool = True
    images: List[ProductImageCreate] = []

class ProductUpdateStatus(BaseModel):
    """Schema specifically for toggling visibility flags on the frontend."""
    is_featured: Optional[bool] = None
    is_bespoke: Optional[bool] = None
    is_active: Optional[bool] = None

class ProductOut(BaseModel):
    id: int
    title: str
    description: str
    price: float
    category: str
    is_featured: bool
    is_bespoke: bool
    is_active: bool
    images: List[ProductImageOut] = []

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    email: EmailStr
    last_name: str
    first_name: str
    created_at: datetime
    class Config:
        from_attributes = True

class DashboardMetricsOut(BaseModel):
    totalProducts: int
    featuredProducts: int
    unreadInquiries: int

# 1. Pydantic schema matching the React interface
class DashboardMetricsOut(BaseModel):
    totalProducts: int
    featuredProducts: int
    unreadInquiries: int