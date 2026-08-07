import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP
from .database import Base

# --- Updated Enums ---

class UserRole(enum.Enum):
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"  # Replaced CUSTOMER with SUPER_ADMIN for scaling permissions

class ProductCategory(enum.Enum):
    READY_TO_WEAR = "ready_to_wear"  # E.g., The main collection
    BESPOKE = "bespoke"              # Replaces the wig section logic

class InquiryType(enum.Enum):
    GENERAL = "general"
    BESPOKE_DRESS = "bespoke_dress"
    # Removed CUSTOM_WIG

# --- Models ---

class Users(Base):
    """Strictly for Website Administrators."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.ADMIN)
    profile_image_url = Column(String, nullable=True, server_default="https://www.gravatar.com/avatar/?d=mp")
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))


class Product(Base):
    """Stores the Dresses."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String, nullable=False)  # FIXED: Was Integer
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    
    category = Column(Enum(ProductCategory), nullable=False, default=ProductCategory.READY_TO_WEAR) # FIXED
    
    is_featured = Column(Boolean, server_default='False', nullable=False)
    is_bespoke = Column(Boolean, server_default='False', nullable=False)
    is_active = Column(Boolean, server_default='False', nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

    # Relationship to images
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")


class ProductImage(Base):
    """Stores Cloudinary image URLs for the products."""
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    image_url = Column(String, nullable=False)
    
    alt_text = Column(String, nullable=False)  # FIXED: Removed unique=True
    is_primary = Column(Boolean, server_default='False', nullable=False)
    is_video_snippet = Column(Boolean, server_default='False', nullable=False)
    public_id = Column(String, nullable=False)

    # Relationship back to product
    product = relationship("Product", back_populates="images")


class ContactMessage(Base):
    """Stores messages and bespoke inquiries from customers."""
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False)  # FIXED: Removed unique=True
    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    inquiry_type = Column(Enum(InquiryType), nullable=False, default=InquiryType.GENERAL)
    is_read = Column(Boolean, server_default='False', nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))