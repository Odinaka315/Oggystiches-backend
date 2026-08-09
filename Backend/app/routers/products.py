import cloudinary.uploader
from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile, Response, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from ..database import get_db
from .. import models, oauth2, schemas

router = APIRouter(prefix="/api/v1/products", tags=["Products"])

def validate_files(files: List[UploadFile]):
    """Helper function to enforce the image/video limits."""
    image_count = 0
    video_count = 0

    for file in files:
        if file.content_type.startswith("video/"):
            video_count += 1
        elif file.content_type.startswith("image/"):
            image_count += 1
        else:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}")

    if image_count < 1 or image_count > 3:
        raise HTTPException(status_code=400, detail="A product must have between 1 and 3 images.")
    if video_count > 1:
        raise HTTPException(status_code=400, detail="A product can have at most 1 video snippet.")
    
@router.get("/storefront", response_model=List[schemas.ProductOut])
def get_public_products(
    product_id: Optional[int] = Query(None, description="Filter by exact product ID"),
    title: Optional[str] = Query(None, description="Search by title (case-insensitive partial match)"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    category: Optional[models.ProductCategory] = Query(None, description="Filter by category"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    is_bespoke: Optional[bool] = Query(None, description="Filter by bespoke status"),
    db: Session = Depends(get_db)
):
    """
    Fetch active products for the public storefront with optional filters.
    Hidden/inactive products will never be returned.
    """
    # 1. Start the base query, eagerly loading images, AND enforce is_active == True
    query = (
        db.query(models.Product)
        .options(joinedload(models.Product.images))
        .filter(models.Product.is_active == True)
    )

    # 2. Apply filters dynamically based on what was passed in the request URL
    if product_id is not None:
        query = query.filter(models.Product.id == product_id)
        
    if title:
        # Using .ilike() for case-insensitive partial matching 
        query = query.filter(models.Product.title.ilike(f"%{title}%"))

    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)

    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)

    if category:
        query = query.filter(models.Product.category == category)

    if is_featured is not None:
        query = query.filter(models.Product.is_featured == is_featured)

    if is_bespoke is not None:
        query = query.filter(models.Product.is_bespoke == is_bespoke)

    # 3. Order the results (newest first is usually the standard)
    query = query.order_by(models.Product.created_at.desc())

    # 4. Execute and return
    return query.all()

@router.get("/admin", response_model=List[schemas.ProductOut])
def get_products(
    product_id: Optional[int] = Query(None, description="Filter by exact product ID"),
    title: Optional[str] = Query(None, description="Search by title (case-insensitive partial match)"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    category: Optional[models.ProductCategory] = Query(None, description="Filter by category"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    is_bespoke: Optional[bool] = Query(None, description="Filter by bespoke status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(oauth2.get_current_user)
):
    """
    Fetch products with optional filters.
    If no filters are provided in the URL, it returns all products.
    """
    # 1. Start the base query, eagerly loading images to prevent N+1 query performance issues
    query = db.query(models.Product).options(joinedload(models.Product.images))

    # 2. Apply filters dynamically based on what was passed in the request URL
    if product_id is not None:
        query = query.filter(models.Product.id == product_id)
        
    if title:
        # Using .ilike() for case-insensitive partial matching 
        # (e.g., searching "silk" will find "Red Silk Dress")
        query = query.filter(models.Product.title.ilike(f"%{title}%"))

    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)

    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)

    if category:
        query = query.filter(models.Product.category == category)

    if is_featured is not None:
        query = query.filter(models.Product.is_featured == is_featured)

    if is_bespoke is not None:
        query = query.filter(models.Product.is_bespoke == is_bespoke)

    if is_active is not None:
        query = query.filter(models.Product.is_active == is_active)

    # 3. Order the results (newest first is usually the standard for an admin dashboard)
    query = query.order_by(models.Product.created_at.desc())

    # 4. Execute and return
    return query.all()

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_product(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    
    # 1. FIX: Change 'str' to 'models.ProductCategory'
    category: models.ProductCategory = Form(...), 
    
    is_featured: bool = Form(False),
    is_bespoke: bool = Form(False),
    is_active: bool = Form(True),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(oauth2.get_current_user)
):
    # 1. Validate the file limits
    validate_files(files)

    # 2. Save product text data to DB
    new_product = models.Product(
        title=title,
        description=description,
        price=price,
        
        # 'category' is now a valid Enum object, which SQLAlchemy understands
        category=category, 
        
        is_featured=is_featured,
        is_bespoke=is_bespoke,
        is_active=is_active
    )
    db.add(new_product)
    db.flush()

    # 3. Upload to Cloudinary and save URLs & public_ids to DB
    for index, file in enumerate(files):
        is_video = file.content_type.startswith("video/")
        
        upload_result = cloudinary.uploader.upload(
            file.file, 
            resource_type="auto",
            folder="oggystitches/products"
        )
        
        new_image = models.ProductImage(
            product_id=new_product.id,
            image_url=upload_result.get("secure_url"),
            public_id=upload_result.get("public_id"), 
            alt_text=f"{title} - {'video' if is_video else 'image'} {index + 1}",
            is_primary=(index == 0),
            is_video_snippet=is_video
        )
        db.add(new_image)

    db.commit()
    
    query = (
        db.query(models.Product)
        .options(joinedload(models.Product.images))
        .filter(models.Product.id == new_product.id)
        .first()
    )
    
    return query


@router.put("/{product_id}")
def modify_product(
    product_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    category: models.ProductCategory = Form(...), 
    is_featured: Optional[bool] = Form(None),
    is_bespoke: Optional[bool] = Form(None),
    is_active: Optional[bool] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: models.Users = Depends(oauth2.get_current_user)

):
    # 1. Fetch existing product
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Update text fields if provided
    if title is not None: product.title = title
    if description is not None: product.description = description
    if price is not None: product.price = price
    if category is not None: product.category = category
    if is_featured is not None: product.is_featured = is_featured
    if is_bespoke is not None: product.is_bespoke = is_bespoke
    if is_active is not None: product.is_active = is_active

    # 3. Handle File Replacements
    if files:
        validate_files(files)
        
        # --- NEW: Cloudinary Cleanup Logic ---
        
        # A. Get the old images from the database BEFORE deleting them
        old_images = db.query(models.ProductImage).filter(models.ProductImage.product_id == product_id).all()
        
        # B. Delete them from Cloudinary
        for old_img in old_images:
            try:
                # Cloudinary requires the resource_type to be "video" to delete an mp4
                res_type = "video" if old_img.is_video_snippet else "image"
                cloudinary.uploader.destroy(old_img.public_id, resource_type=res_type)
            except Exception as e:
                # We catch exceptions here so that if Cloudinary has a hiccup, 
                # it doesn't crash the whole update process.
                print(f"Warning: Failed to delete asset {old_img.public_id} from Cloudinary. Error: {str(e)}")

        # C. Delete old image records from the database
        db.query(models.ProductImage).filter(models.ProductImage.product_id == product_id).delete()
        
        # --- END NEW LOGIC ---

        # Upload new files
        for index, file in enumerate(files):
            is_video = file.content_type.startswith("video/")
            upload_result = cloudinary.uploader.upload(
                file.file, 
                resource_type="auto",
                folder="oggystitches/products"
            )
            
            new_image = models.ProductImage(
                product_id=product.id,
                image_url=upload_result.get("secure_url"),
                public_id=upload_result.get("public_id"),  # Ensure you are saving this!
                alt_text=f"{product.title} - {'video' if is_video else 'image'} {index + 1}",
                is_primary=(index == 0),
                is_video_snippet=is_video
            )
            db.add(new_image)

    db.commit()
    query = db.query(models.Product).options(joinedload(models.Product.images)).filter(models.Product.id == product.id).first()
    return query

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.Users = Depends(oauth2.get_current_user)

):
    """
    Deletes a product along with all its Cloudinary assets.
    """
    # 1. Fetch existing product
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # 2. Fetch associated image/video records BEFORE deleting the product
    product_images = db.query(models.ProductImage).filter(models.ProductImage.product_id == product_id).all()

    # 3. Destroy each asset on Cloudinary
    for img in product_images:
        if img.public_id:
            try:
                res_type = "video" if img.is_video_snippet else "image"
                cloudinary.uploader.destroy(img.public_id, resource_type=res_type)
            except Exception as e:
                # Log warning so a Cloudinary failure doesn't block database cleanup
                print(f"Warning: Failed to delete Cloudinary asset {img.public_id}. Error: {str(e)}")

    # 4. Delete the product from the database
    # (Cascade handles deleting the ProductImage DB rows automatically)
    db.delete(product)
    db.commit()

    # HTTP 204 No Content requires an empty body
    return Response(status_code=status.HTTP_204_NO_CONTENT)