from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.auth import create_access_token, decode_token, hash_password, verify_password
from app.database.db import get_db
from app.models import CreateUser, UpdateUser, UserResponse, UserRole

router = APIRouter(prefix="/users", tags=["user"])


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")


# register user
@router.post("/", response_model=UserResponse)
async def register_user(user: CreateUser, db=Depends(get_db)):
    user_collection = db["user_collection"]
    hashed_pw = hash_password(user.password)
    user_dict = user.dict()

    user_dict["password"] = hashed_pw
    user_dict["role"] = user.role.value
    if await user_collection.find_one({"email": user_dict["email"]}):
        raise HTTPException(status_code=409, detail="Email Already Exist")
    result = await user_collection.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    return UserResponse(**user_dict)


# generate token on login
@router.post("/token", response_model=dict())
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    user_collection = db["user_collection"]
    user = await user_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user["email"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}


# get current user
async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    user_collection = db["user_collection"]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await user_collection.find_one({"email": payload["sub"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# role checker
def require_roles(*allowed_roles: UserRole):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=403, detail="You don't have access to this resource"
            )
        return user

    return role_checker


# get all users
@router.get(
    "/",
    response_model=List[UserResponse],
    dependencies=[Depends(require_roles(UserRole.admin))],
)
async def get_all_users(
    page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db=Depends(get_db)
):
    user_collection = db["user_collection"]
    skip = (page - 1) * size
    limit = size
    users_cursur = user_collection.find().skip(skip).limit(limit)
    if not users_cursur:
        raise HTTPException(status_code=404, detail="No users found")
    users = []
    async for user in users_cursur:
        user["id"] = str(user["_id"])
        user["role"] = UserRole[user["role"]]  # Convert string to Enum
        users.append(UserResponse(**user))
    return users


# update user


@router.put("/{user_id}")
async def update_user(user_id: str, user_update: UpdateUser, db=Depends(get_db)):
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "Invalid user ID")

    existing_user = await db["user_collection"].find_one({"_id": obj_id})
    if not existing_user:
        raise HTTPException(404, "User not found")

    update_data = user_update.dict(exclude_unset=True)
    await db["user_collection"].update_one({"_id": obj_id}, {"$set": update_data})

    updated_user = await db["user_collection"].find_one({"_id": obj_id})
    updated_user["id"] = str(updated_user["_id"])
    updated_user.pop("_id", None)
    return updated_user


# delete user
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(UserRole.admin))],
)
async def delete_user(user_id: str, db=Depends(get_db)):
    user_collection = db["user_collection"]

    user = await user_collection.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await user_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"detail": "User deleted successfully"}


# get user with id


@router.get("/{user_id}")
async def get_user_by_id(user_id: str, db=Depends(get_db)):
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = await db["user_collection"].find_one({"_id": obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Convert _id to id for response
    user["id"] = str(user["_id"])
    user.pop("_id", None)
    return user


def parse_mongo_document(doc: dict) -> dict:
    doc = doc.copy()
    doc["id"] = str(doc.pop("_id"))
    return doc


# get all fines of user
@router.get("/{user_id}/fines", dependencies=[Depends(require_roles(UserRole.admin))])
async def get_user_fines(user_id: str, db=Depends(get_db)):
    user_collection = db["user_collection"]
    student_fine_collection = db["student_fine_collection"]
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=404, detail="Invalid user Id format")

    user = await user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    fines_cursor = student_fine_collection.find({"student_id": ObjectId(user_id)})

    fines = []
    async for fine in fines_cursor:
        fines.append(parse_mongo_document(fine))

    return fines
