from fastapi import APIRouter, Depends, HTTPException
from app.models import StudentFine, StudentFineResponse, StudentFineUpdate
from app.database.db import get_db
from app.models import UserRole
from app.routers.user import require_roles
from bson import ObjectId
from datetime import datetime
from typing import List

router = APIRouter(prefix="/student_fines", tags=["student_fine"])


@router.post("/", response_model=StudentFineResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def create_student_fine(student_fine: StudentFine, db=Depends(get_db)):
    student_fine_collection = db["student_fine_collection"]
    book_collection = db["book_collection"]
    issued_collection = db["issued_collection"]
    student_fine_dict = student_fine.model_dump()  # Updated for Pydantic v2+

    # Validate book ID
    try:
        book_obj_id = ObjectId(student_fine_dict["book_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid book ID")

    db_book = await book_collection.find_one({"_id": book_obj_id})
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Validate issued_book_id
    try:
        issued_book_obj_id = ObjectId(student_fine_dict["issued_book_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid issued book ID")

    issued_record = await issued_collection.find_one({"_id": issued_book_obj_id})
    if not issued_record:
        raise HTTPException(status_code=404, detail="Issued book record not found")

    # Validate student_id matches issued record
    if student_fine_dict["student_id"] != issued_record.get("student_id"):
        raise HTTPException(status_code=400, detail="Student ID does not match the issued book record")

    # Check if book is overdue
    now = datetime.now()
    return_date_raw = issued_record.get("return_date")
    is_returned = issued_record.get("is_returned", False)

    if return_date_raw:
        try:
            # Parse return_date string to datetime if necessary
            return_date = return_date_raw if isinstance(return_date_raw, datetime) else datetime.fromisoformat(return_date_raw)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid return_date format")
    else:
        raise HTTPException(status_code=400, detail="Missing return_date in issued record")

    if now > return_date and not is_returned:
        late_days = (now - return_date).days
        student_fine_dict["fine_amount"] = late_days * 50
    else:
        raise HTTPException(status_code=400, detail="Book is not overdue or already returned")

    student_fine_dict["fine_date"] = now

    result = await student_fine_collection.insert_one(student_fine_dict)
    student_fine_dict["id"] = str(result.inserted_id)

    return StudentFineResponse(**student_fine_dict)


@router.get("/", response_model=List[StudentFineResponse], dependencies=[Depends(require_roles(UserRole.librarian))])
async def get_student_fines(page: int = 1, size: int = 10, db=Depends(get_db)):
    student_fine_collection = db["student_fine_collection"]
    skip = (page - 1) * size
    limit = size

    cursor = student_fine_collection.find().skip(skip).limit(limit)
    fines = []
    async for fine in cursor:
        fine["id"] = str(fine.pop("_id"))
        fines.append(StudentFineResponse(**fine))
    return fines


@router.get("/{fine_id}", response_model=StudentFineResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def get_student_fine(fine_id: str, db=Depends(get_db)):
    student_fine_collection = db["student_fine_collection"]
    try:
        obj_id = ObjectId(fine_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid fine ID")

    fine = await student_fine_collection.find_one({"_id": obj_id})
    if not fine:
        raise HTTPException(status_code=404, detail="Fine not found")

    fine["id"] = str(fine.pop("_id"))
    return StudentFineResponse(**fine)


@router.put("/{fine_id}", response_model=StudentFineResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def update_student_fine(fine_id: str, fine_data: StudentFineUpdate, db=Depends(get_db)):
    student_fine_collection = db["student_fine_collection"]
    try:
        obj_id = ObjectId(fine_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid fine ID")

    update = fine_data.model_dump(exclude_unset=True)

    result = await student_fine_collection.update_one(
        {"_id": obj_id},
        {"$set": update}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Fine not updated")

    updated_fine = await student_fine_collection.find_one({"_id": obj_id})
    if not updated_fine:
        raise HTTPException(status_code=404, detail="Fine not found")

    updated_fine["id"] = str(updated_fine.pop("_id"))
    return StudentFineResponse(**updated_fine)


@router.delete("/{fine_id}", dependencies=[Depends(require_roles(UserRole.librarian))])
async def delete_student_fine(fine_id: str, db=Depends(get_db)):
    student_fine_collection = db["student_fine_collection"]
    try:
        obj_id = ObjectId(fine_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid fine ID")

    result = await student_fine_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Fine not found")

    return {"message": "Fine deleted successfully"}
