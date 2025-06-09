from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database.db import get_db
from app.models import Category, CategoryDb

router = APIRouter(prefix="/category", tags=["category"])


# Helper function
def category_helper(cat) -> dict:
    return {"id": str(cat["_id"]), "category_name": cat["category_name"]}


#  Create Category
@router.post("/", response_model=CategoryDb)
async def create_category(category: Category, db=Depends(get_db)):
    category_collection = db["category_collection"]
    cat = category.dict(by_alias=True, exclude_unset=True)
    result = await category_collection.insert_one(cat)
    new_cat = await category_collection.find_one({"_id": result.inserted_id})
    return category_helper(new_cat)


#  Get All Categories
@router.get("/", response_model=list[CategoryDb])
async def get_categories(
    page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db=Depends(get_db)
):
    category_collection = db["category_collection"]
    skip = (page - 1) * size
    limit = size
    categories = []
    async for cat in category_collection.find().skip(skip).limit(limit):
        categories.append(category_helper(cat))
    return categories


#  Get Category by ID
@router.get("/{cat_id}", response_model=CategoryDb)
async def get_category(cat_id: str, db=Depends(get_db)):
    category_collection = db["category_collection"]
    cat = await category_collection.find_one({"_id": ObjectId(cat_id)})
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return category_helper(cat)


#  Update Category
@router.put("/{cat_id}", response_model=CategoryDb)
async def update_category(cat_id: str, updated: Category, db=Depends(get_db)):
    category_collection = db["category_collection"]
    update_data = updated.dict(by_alias=True, exclude_unset=True)
    result = await category_collection.update_one(
        {"_id": ObjectId(cat_id)}, {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Category not updated")
    updated_cat = await category_collection.find_one({"_id": ObjectId(cat_id)})
    return category_helper(updated_cat)


#  Delete Category
@router.delete("/{cat_id}")
async def delete_category(cat_id: str, db=Depends(get_db)):
    category_collection = db["category_collection"]
    result = await category_collection.delete_one({"_id": ObjectId(cat_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted"}
