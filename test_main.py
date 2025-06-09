from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.database.db import get_db
from app.main import app
from app.models import User, UserRole
from app.routers.user import get_current_user  # or wherever it's defined

now = datetime.now(tz=timezone.utc)
import uuid
from unittest.mock import AsyncMock

# Fixtures for Mocking Database Collections and Dependencies..................................................................
import pytest
from bson import ObjectId

from app.auth import create_access_token, hash_password

# Shared memory store


@pytest.fixture
def mock_user_collection():
    db_store = {}

    async def find_one(query):
        _id = query.get("_id")
        if _id:
            return db_store.get(str(_id))  # convert ObjectId to string key
        if "email" in query:
            for user in db_store.values():
                if user["email"] == query["email"]:
                    return user
        return None

    async def insert_one(user_dict):
        _id = ObjectId()
        user_dict["_id"] = _id
        db_store[str(_id)] = user_dict
        return AsyncMock(inserted_id=_id)

    async def delete_one(query):
        _id = query.get("_id")
        if _id and str(_id) in db_store:  # ensure str conversion
            del db_store[str(_id)]
            return AsyncMock(deleted_count=1)
        return AsyncMock(deleted_count=0)

    async def delete_many(_):
        count = len(db_store)
        db_store.clear()
        return AsyncMock(deleted_count=count)

    mock = AsyncMock()
    mock.find_one.side_effect = find_one
    mock.insert_one.side_effect = insert_one
    mock.delete_one.side_effect = delete_one
    mock.delete_many.side_effect = delete_many

    return mock


# Custom async iterator to simulate async database cursor
# This is a workaround since AsyncMock does not support async iterators directly


class AsyncIterator:
    def __init__(self, items):
        self._items = items
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


@pytest.fixture
def mock_student_fine_collection():
    fines_store = []

    async def find(query={}):
        student_id_query = query.get("student_id")
        if isinstance(student_id_query, ObjectId):
            student_id_query = str(student_id_query)
        results = [
            fine
            for fine in fines_store
            if fine.get("student_id") == student_id_query or query == {}
        ]
        return AsyncIterator(results)

    async def insert_one(fine):
        if "student_id" in fine and isinstance(fine["student_id"], ObjectId):
            fine["student_id"] = str(fine["student_id"])

        fine["_id"] = ObjectId()
        fines_store.append(fine)

        mock_result = AsyncMock()
        mock_result.inserted_id = fine["_id"]
        return mock_result

    mock = AsyncMock()
    mock.find.side_effect = find
    mock.insert_one.side_effect = insert_one

    return mock


@pytest.fixture
def mock_author_collection():
    mock = AsyncMock()
    mock.insert_one.return_value.inserted_id = ObjectId("507f1f77bcf86cd799439011")
    mock.find_one = AsyncMock(
        return_value={
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "author_name": "Test Author",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    )
    return mock


@pytest.fixture
def mock_book_collection():
    mock = AsyncMock()

    mock.insert_one.return_value.inserted_id = ObjectId("60d5ec49f8d2e86f1f3f83b1")
    mock.find_one.return_value = {
        "_id": ObjectId("60d5ec49f8d2e86f1f3f83b1"),
        "book_name": "Test Book",
        "author_id": "507f1f77bcf86cd799439011",
        "category_id": "60d5ec49f8d2e86f1f3f83b1",
        "is_available": True,
    }

    mock.find = lambda *args, **kwargs: AsyncIterator(
        [
            {
                "_id": ObjectId("60d5ec49f8d2e86f1f3f83b1"),
                "book_name": "Test Book",
                "author_id": "507f1f77bcf86cd799439011",
                "category_id": "60d5ec49f8d2e86f1f3f83b1",
                "is_available": True,
            }
        ]
    )
    # Mocking find to return a single book document
    mock.find_one = AsyncMock(
        return_value={
            "_id": ObjectId("60d5ec49f8d2e86f1f3f83b1"),
            "book_name": "Test Book",
            "author_id": "507f1f77bcf86cd799439011",
            "category_id": "60d5ec49f8d2e86f1f3f83b1",
            "is_available": True,
        }
    )

    return mock


@pytest.fixture
def mock_category_collection():
    mock = AsyncMock()
    mock.insert_one.return_value.inserted_id = ObjectId("60d5ec49f8d2e86f1f3f83b1")
    mock.find_one.return_value = {
        "_id": ObjectId("60d5ec49f8d2e86f1f3f83b1"),
        "category_name": "Test Category",
    }
    mock.find = lambda *args, **kwargs: AsyncIterator(
        [
            {
                "_id": ObjectId("60d5ec49f8d2e86f1f3f83b1"),
                "category_name": "Test Category",
            }
        ]
    )
    return mock


@pytest.fixture
def mock_student_collection():
    mock = AsyncMock()
    fake_id = ObjectId("507f1f77bcf86cd799439012")

    mock.insert_one.return_value.inserted_id = fake_id
    mock.find_one = AsyncMock(
        return_value={
            "_id": fake_id,
            "student_name": "Test Student",
            "email": "test@student.com",
        }
    )

    # For update_one
    mock.update_one.return_value.modified_count = 1

    # For delete_one
    mock.delete_one.return_value.deleted_count = 1

    # For find returning multiple student - will use AsyncIterator pattern in mock_db fixture

    return mock


@pytest.fixture
def mock_issued_collection():
    mock = AsyncMock()

    # Sample issued book document
    issued_book = {
        "_id": ObjectId("507f191e810c19729de860ea"),
        "book_id": "60d5ec49f8d2e86f1f3f83b1",
        "student_id": "507f1f77bcf86cd799439012",
        "issued_date": "2024-01-01",
        "return_date": "2024-02-01",
        "is_returned": False,
    }

    mock.find = lambda *args, **kwargs: AsyncIterator([issued_book])

    # Mock insert_one to return a mock result with inserted_id
    mock.insert_one.return_value.inserted_id = issued_book["_id"]

    # Mock find_one to return the issued_book dict directly (no MagicMocks)
    mock.find_one.return_value = issued_book

    return mock


@pytest.fixture
def mock_db(
    mock_author_collection,
    mock_book_collection,
    mock_category_collection,
    mock_student_collection,
    mock_issued_collection,
    mock_user_collection,
    mock_student_fine_collection,
):
    return {
        "author_collection": mock_author_collection,
        "book_collection": mock_book_collection,
        "category_collection": mock_category_collection,
        "student_collection": mock_student_collection,
        "issued_collection": mock_issued_collection,
        "user_collection": mock_user_collection,
        "student_fine_collection": mock_student_fine_collection,
    }


@pytest.fixture(autouse=True)
async def override_get_db(mock_db):
    async def _override():
        yield mock_db

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_get_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# Tests for User Endpoints.........................................................................................


@pytest.fixture
def admin_token():
    return create_access_token({"sub": "admin@example.com", "role": "admin"})


@pytest.mark.asyncio
async def test_register(async_client):
    unique_id = uuid.uuid4().hex[:8]
    user_data = {
        "username": f"testuser_{unique_id}",
        "email": f"user_{unique_id}@example.com",
        "password": "password123",
        "role": "student",
    }

    reg_response = await async_client.post("/users/", json=user_data)
    assert reg_response.status_code == 200


@pytest.mark.asyncio
async def test_register_user_already_exists(async_client, mock_user_collection):
    email = "existinguser@example.com"

    # Cleanup before test (optional: mock already ensures no real DB call)
    await mock_user_collection.delete_many({"email": email})

    user_data = {
        "username": "existinguser",
        "email": email,
        "password": "password123",
        "role": "student",
    }

    response1 = await async_client.post("/users/", json=user_data)

    assert response1.status_code == 200

    response2 = await async_client.post("/users/", json=user_data)
    assert response2.status_code == 409
    assert response2.json()["detail"] == "Email Already Exist"


@pytest.mark.asyncio
async def test_login_user(async_client):
    unique_id = uuid.uuid4().hex[:8]
    email = f"user_{unique_id}@example.com"
    password = "password123"

    reg = await async_client.post(
        "/users/",
        json={
            "username": f"user_{unique_id}",
            "email": email,
            "password": password,
            "role": "student",
        },
    )

    assert reg.status_code == 200

    login_response = await async_client.post(
        "/users/token", data={"username": email, "password": password}
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_get_user_by_id(async_client, admin_token):
    # Create user
    create_response = await async_client.post(
        "/users/",
        json={
            "username": "admin2",
            "email": "admin2@example.com",
            "password": "adminpass",
            "role": "admin",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert create_response.status_code == 200
    user_id = create_response.json()["id"]

    # Retrieve user
    response = await async_client.get(
        f"/users/{user_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )

    if response.status_code != 200:
        print("RESPONSE TEXT:", response.text)

    assert response.status_code == 200
    assert response.json()["email"] == "admin2@example.com"


@pytest.mark.asyncio
async def test_update_user(async_client, admin_token):
    # Create user first
    create_response = await async_client.post(
        "/users/",
        json={
            "username": "admin2",
            "email": "updated@example.com",
            "password": "initialpass",
            "role": "student",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert create_response.status_code == 200
    user_id = create_response.json()["id"]

    # Now update the user
    response = await async_client.put(
        f"/users/{user_id}",
        json={
            "username": "updatedadmin2",
            "email": "updated@example.com",
            "password": "newpassword123",
            "role": "student",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "updated@example.com"


# @pytest.mark.asyncio
# async def test_delete_user(async_client, admin_token):
#     # Create user to delete
#     create_response = await async_client.post("/users/", json={
#         "username": "user",
#         "email": "user@example.com",
#         "password": "user123",
#         "role": "student"
#     }, headers={"Authorization": f"Bearer {admin_token}"})

#     assert create_response.status_code == 200
#     user_id = create_response.json()["id"]
#     print("Created User ID:", user_id)

#     # Check user exists in DB by calling GET endpoint or similar
#     get_response = await async_client.get(f"/users/{user_id}", headers={"Authorization": f"Bearer {admin_token}"})
#     print("GET USER RESPONSE:", get_response.status_code, get_response.text)
#     assert get_response.status_code == 200

#     # Now delete

#     response = await async_client.delete(f"/users/{user_id}", headers={"Authorization": f"Bearer {admin_token}"})

#     print("DELETE RESPONSE:", response.status_code, response.text)
#     assert response.status_code == 200
#     assert response.json()["detail"] == "User deleted successfully"


# @pytest.mark.asyncio
# async def test_get_user_fines(async_client, admin_token, mock_student_fine_collection):
#     # Step 1: Create the user
#     create_response = await async_client.post("/users/", json={
#         "username": "user",
#         "email": "user@example.com",
#         "password": "finepassword",
#         "role": "student"
#     }, headers={"Authorization": f"Bearer {admin_token}"})

#     assert create_response.status_code == 200
#     user_id = create_response.json()["id"]

#     # Step 2: Insert a fine for that user
#     await mock_student_fine_collection.insert_one({
#     "student_id": user_id,
#     "book_id": "dummy_book_id",
#     "issued_book_id": "dummy_issued_id",
#     "fine_amount": 100.0,
#     "fine_date": datetime.utcnow(),
#     "is_paid": False
#     })

#     # Step 3: Fetch fines
#     response = await async_client.get(f"/users/{user_id}/fines", headers={
#         "Authorization": f"Bearer {admin_token}"
#     })

#     assert response.status_code == 200
#     fines = response.json()
#     assert isinstance(fines, list)
#     assert fines
#     assert fines[0]["fine_amount"] == 100.0


# Tests for CreateAuthor Endpoints.........................................................................................
@pytest.mark.asyncio
async def test_create_author(async_client):
    payload = {"author_name": "Test Author"}
    response = await async_client.post("/author/", json=payload)
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["author_name"] == "Test Author"
    assert ObjectId.is_valid(json_resp["id"])


# Tests for Get Authors Endpoints.........................................................................................
@pytest.mark.asyncio
async def test_get_author(async_client):
    author_id = "507f1f77bcf86cd799439011"
    response = await async_client.get(f"/author/authors/{author_id}")
    assert response.status_code == 200
    json_resp = response.json()
    assert "id" in json_resp
    assert "books" in json_resp


# Tests for Update Authors Endpoints......................................................................................
@pytest.mark.asyncio
async def test_update_author_success(async_client, mock_author_collection):
    author_id = "507f1f77bcf86cd799439011"
    payload = {"author_name": "Updated Author"}

    # Mock update_one to return modified_count = 1 (successful update)
    mock_author_collection.update_one.return_value.modified_count = 1

    # Mock find_one to return updated author document
    mock_author_collection.find_one.return_value = {
        "_id": ObjectId(author_id),
        "author_name": "Updated Author",
        "created_at": now.isoformat(),
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    response = await async_client.put(f"/author/{author_id}", json=payload)
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["author_name"] == "Updated Author"
    assert json_resp["id"] == author_id


# Tests for Update Author Not Found Endpoints......................................................................................
@pytest.mark.asyncio
async def test_update_author_not_found(async_client, mock_author_collection):
    author_id = "507f1f77bcf86cd799439011"
    payload = {"author_name": "Updated Author"}

    # Mock update_one to return modified_count = 0 (no update)
    mock_author_collection.update_one.return_value.modified_count = 0

    response = await async_client.put(f"/author/{author_id}", json=payload)
    assert response.status_code == 404
    assert response.json() == {"detail": "Author not updated"}


# Tests for Delete Author Endpoints......................................................................................
@pytest.mark.asyncio
async def test_delete_author_success(async_client, mock_author_collection):
    author_id = "507f1f77bcf86cd799439011"

    # Mock delete_one to simulate successful deletion
    mock_author_collection.delete_one.return_value.deleted_count = 1

    response = await async_client.delete(f"/author/{author_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Author deleted"}


# Tests for Delete Author Not Found Endpoints......................................................................................
@pytest.mark.asyncio
async def test_delete_author_not_found(async_client, mock_author_collection):
    author_id = "507f1f77bcf86cd799439011"

    # Mock delete_one to simulate author not found
    mock_author_collection.delete_one.return_value.deleted_count = 0

    response = await async_client.delete(f"/author/{author_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Author not found"}


# tests for  Category Endpoints......................................................................................................................


@pytest.mark.asyncio
async def test_create_category(async_client):
    payload = {"category_name": "Test Category"}
    response = await async_client.post("/category/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category_name"] == "Test Category"
    assert ObjectId.is_valid(data["id"])


@pytest.mark.asyncio
async def test_get_category_by_id(async_client):
    category_id = "60d5ec49f8d2e86f1f3f83b1"
    response = await async_client.get(f"/category/{category_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == category_id
    assert data["category_name"] == "Test Category"


@pytest.mark.asyncio
async def test_get_category_not_found(async_client, mock_category_collection):
    mock_category_collection.find_one.return_value = None
    response = await async_client.get("/category/000000000000000000000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


@pytest.mark.asyncio
async def test_update_category_success(async_client, mock_category_collection):
    category_id = "60d5ec49f8d2e86f1f3f83b1"
    payload = {"category_name": "Updated Category"}

    mock_category_collection.update_one.return_value.modified_count = 1
    mock_category_collection.find_one.return_value = {
        "_id": ObjectId(category_id),
        "category_name": "Updated Category",
    }

    response = await async_client.put(f"/category/{category_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category_name"] == "Updated Category"


@pytest.mark.asyncio
async def test_update_category_not_found(async_client, mock_category_collection):
    category_id = "60d5ec49f8d2e86f1f3f83b1"
    payload = {"category_name": "Updated Category"}

    mock_category_collection.update_one.return_value.modified_count = 0

    response = await async_client.put(f"/category/{category_id}", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not updated"


@pytest.mark.asyncio
async def test_delete_category_success(async_client, mock_category_collection):
    category_id = "60d5ec49f8d2e86f1f3f83b1"
    mock_category_collection.delete_one.return_value.deleted_count = 1

    response = await async_client.delete(f"/category/{category_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Category deleted"}


@pytest.mark.asyncio
async def test_delete_category_not_found(async_client, mock_category_collection):
    category_id = "60d5ec49f8d2e86f1f3f83b1"
    mock_category_collection.delete_one.return_value.deleted_count = 0

    response = await async_client.delete(f"/category/{category_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


# tests for Student Endpoints......................................................................................................................


@pytest.mark.asyncio
async def test_create_student(async_client, mock_student_collection):
    payload = {"student_name": "Test Student", "email": "test@student.com"}

    response = await async_client.post("/students/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["student_name"] == payload["student_name"]
    assert data["email"] == payload["email"]
    assert ObjectId.is_valid(data["id"])


@pytest.mark.asyncio
async def test_get_student_with_issued_books(
    async_client, mock_student_collection, mock_issued_collection
):
    student_id = "507f1f77bcf86cd799439012"

    response = await async_client.get(f"/students/{student_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student_id
    assert data["student_name"] == "Test Student"
    assert len(data["issued_books"]) == 1
    assert data["issued_books"][0]["book_id"] == "60d5ec49f8d2e86f1f3f83b1"


@pytest.mark.asyncio
async def test_get_student_with_invalid_id(async_client):
    invalid_id = "invalidid"
    response = await async_client.get(f"/students/{invalid_id}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid student ID"


@pytest.mark.asyncio
async def test_update_student_success(async_client, mock_student_collection):
    student_id = "507f1f77bcf86cd799439012"
    payload = {"student_name": "Updated Student", "email": "updated@student.com"}

    mock_student_collection = mock_student_collection
    mock_student_collection.update_one.return_value.modified_count = 1
    mock_student_collection.find_one.return_value = {
        "_id": ObjectId(student_id),
        "student_name": payload["student_name"],
        "email": payload["email"],
    }

    response = await async_client.put(f"/students/{student_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["student_name"] == payload["student_name"]
    assert data["email"] == payload["email"]


@pytest.mark.asyncio
async def test_update_student_not_updated(async_client, mock_student_collection):
    student_id = "507f1f77bcf86cd799439012"
    payload = {"student_name": "Updated Student", "email": "updated@student.com"}

    mock_student_collection.update_one.return_value.modified_count = 0

    response = await async_client.put(f"/students/{student_id}", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Student not updated"


@pytest.mark.asyncio
async def test_delete_student_success(async_client, mock_student_collection):
    student_id = "507f1f77bcf86cd799439012"

    mock_student_collection.delete_one.return_value.deleted_count = 1

    response = await async_client.delete(f"/students/{student_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Student deleted"


@pytest.mark.asyncio
async def test_delete_student_not_found(async_client, mock_student_collection):
    student_id = "507f1f77bcf86cd799439012"

    mock_student_collection.delete_one.return_value.deleted_count = 0

    response = await async_client.delete(f"/students/{student_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found"


@pytest.mark.asyncio
async def test_delete_student_invalid_id(async_client):
    invalid_id = "invalidid"

    response = await async_client.delete(f"/students/{invalid_id}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid student ID"


# Tests for Book Endpoints......................................................................................................................


@pytest.fixture
async def librarian_token(async_client):
    user_data = {
        "username": "librarian@example.com",
        "email": "librarian@example.com",
        "password": "password123",
        "role": "librarian",
    }

    # Register the user
    reg_response = await async_client.post("/users/", json=user_data)
    login_data = {"username": "librarian@example.com", "password": "password123"}

    login_response = await async_client.post("/users/token", data=login_data)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    return login_response.json()["access_token"]


# Sample data for tests
sample_book_create = {
    "book_name": "Test Book",
    "author_id": "507f1f77bcf86cd799439011",
    "category_id": "60d5ec49f8d2e86f1f3f83b1",
    "is_available": True,
}

sample_book_update = {"is_available": False}


@pytest.mark.asyncio
async def test_create_book(async_client, mock_db, librarian_token):
    response = await async_client.post(
        "/books/",
        json=sample_book_create,
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["book_name"] == sample_book_create["book_name"]
    assert data["author_id"] == sample_book_create["author_id"]
    assert data["category_id"] == sample_book_create["category_id"]
    assert data["is_available"] is True


# @pytest.mark.asyncio
# async def test_get_books(async_client, mock_db,librarian_token):
#     # Mock the find method to return an async iterator
#     mock_db["book_collection"].find = AsyncMock(return_value=AsyncIterator([
#         {
#             "_id": ObjectId("60d5ec49f8d2e86f1f3f83b1"),
#             "book_name": "Test Book",
#             "author_id": "507f1f77bcf86cd799439011",
#             "category_id": "60d5ec49f8d2e86f1f3f83b1",
#             "is_available": True
#         }
#     ]))

#     response = await async_client.get("/books/", headers={
#         "Authorization": f"Bearer {librarian_token}"
#     })
#     assert response.status_code == 200
#     data = response.json()
#     assert isinstance(data, list)
#     assert len(data) > 0
#     assert data[0]["book_name"] == "Test Book"


@pytest.mark.asyncio
async def test_get_book_by_id(async_client, mock_book_collection, librarian_token):
    book_id = "60d5ec49f8d2e86f1f3f83b1"
    response = await async_client.get(
        f"/books/{book_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == book_id
    assert data["book_name"] == "Test Book"


@pytest.mark.asyncio
async def test_get_book_not_found(async_client, mock_book_collection, librarian_token):
    mock_book_collection.find_one.return_value = None
    book_id = "60d5ec49f8d2e86f1f3f83b1"
    response = await async_client.get(
        f"/books/{book_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_update_book_success(async_client, mock_book_collection, librarian_token):
    book_id = "60d5ec49f8d2e86f1f3f83b1"
    payload = sample_book_update

    mock_book_collection.update_one.return_value.modified_count = 1
    mock_book_collection.find_one.return_value = {
        "_id": ObjectId(book_id),
        "book_name": "Test Book",
        "author_id": "507f1f77bcf86cd799439011",
        "category_id": "60d5ec49f8d2e86f1f3f83b1",
        "is_available": False,
    }

    response = await async_client.put(
        f"/books/{book_id}",
        json=payload,
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_available"] is False


@pytest.mark.asyncio
async def test_update_book_not_found(
    async_client, mock_book_collection, librarian_token
):
    book_id = "60d5ec49f8d2e86f1f3f83b1"
    payload = sample_book_update

    mock_book_collection.update_one.return_value.modified_count = 0

    response = await async_client.put(
        f"/books/{book_id}",
        json=payload,
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not updated"


@pytest.mark.asyncio
async def test_delete_book_success(async_client, mock_book_collection, librarian_token):
    book_id = "60d5ec49f8d2e86f1f3f83b1"

    mock_book_collection.delete_one.return_value.deleted_count = 1

    response = await async_client.delete(
        f"/books/{book_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Book deleted"


@pytest.mark.asyncio
async def test_delete_book_not_found(
    async_client, mock_book_collection, librarian_token
):
    book_id = "60d5ec49f8d2e86f1f3f83b1"

    mock_book_collection.delete_one.return_value.deleted_count = 0

    response = await async_client.delete(
        f"/books/{book_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


@pytest.mark.asyncio
async def test_delete_book_invalid_id(
    async_client, mock_book_collection, librarian_token
):
    invalid_id = "invalidid"

    response = await async_client.delete(
        f"/books/{invalid_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid book ID"


# Tests for Issued Book Endpoints......................................................................................................................


@pytest.mark.asyncio
async def test_issue_book(async_client, mock_db, librarian_token):
    payload = {
        "book_id": "60d5ec49f8d2e86f1f3f83b1",
        "student_id": "507f1f77bcf86cd799439012",
        "issued_date": "2024-01-01",
        "return_date": "2024-02-01",
        "is_returned": False,
    }

    response = await async_client.post(
        "/issued/", json=payload, headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == payload["book_id"]
    assert data["student_id"] == payload["student_id"]
    assert data["is_returned"] is False


# @pytest.mark.asyncio
# async def test_get_issued_books(async_client, mock_db,librarian_token):
#     # Mock the find method to return an async iterator
#     mock_db["issued_collection"].find = AsyncMock(return_value=AsyncIterator([
#         {
#             "_id": ObjectId("507f191e810c19729de860ea"),
#             "book_id": "60d5ec49f8d2e86f1f3f83b1",
#             "student_id": "507f1f77bcf86cd799439012",
#             "issued_date": "2024-01-01",
#             "return_date": "2024-02-01",
#             "is_returned": False
#         }
#     ]))
#     response = await async_client.get("/issued/", headers={
#         "Authorization": f"Bearer {librarian_token}"
#     })
#     assert response.status_code == 200
#     data = response.json()
#     assert isinstance(data, list)
#     assert len(data) > 0
#     assert data[0]["book_id"] == "60d5ec49f8d2e86f1f3f83b1"


@pytest.mark.asyncio
async def test_get_issued_book_by_id(async_client, mock_db, librarian_token):
    issued_id = "507f191e810c19729de860ea"
    response = await async_client.get(
        f"/issued/{issued_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == issued_id
    assert data["book_id"] == "60d5ec49f8d2e86f1f3f83b1"


@pytest.mark.asyncio
async def test_get_issued_book_not_found(async_client, mock_db, librarian_token):
    mock_db["issued_collection"].find_one.return_value = None
    issued_id = "507f191e810c19729de860ea"
    response = await async_client.get(
        f"/issued/{issued_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Issued record not found"


@pytest.mark.asyncio
async def test_update_issued_book_success(async_client, mock_db, librarian_token):
    issued_id = "507f191e810c19729de860ea"
    payload = {"is_returned": True}

    mock_db["issued_collection"].update_one.return_value.modified_count = 1
    mock_db["issued_collection"].find_one.return_value = {
        "_id": ObjectId(issued_id),
        "book_id": "60d5ec49f8d2e86f1f3f83b1",
        "student_id": "507f1f77bcf86cd799439012",
        "issued_date": "2024-01-01",
        "return_date": "2024-02-01",
        "is_returned": True,
    }

    response = await async_client.put(
        f"/issued/{issued_id}",
        json=payload,
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_returned"] is True


@pytest.mark.asyncio
async def test_update_issued_book_not_found(async_client, mock_db, librarian_token):
    issued_id = "507f191e810c19729de860ea"
    payload = {"is_returned": True}
    mock_db["issued_collection"].update_one.return_value.modified_count = 0
    response = await async_client.put(
        f"/issued/{issued_id}",
        json=payload,
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "No changes made"


@pytest.mark.asyncio
async def test_delete_issued_book_success(async_client, mock_db, librarian_token):
    issued_id = "507f191e810c19729de860ea"
    mock_db["issued_collection"].delete_one.return_value.deleted_count = 1
    response = await async_client.delete(
        f"/issued/{issued_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Issued record deleted"


@pytest.mark.asyncio
async def test_delete_issued_book_not_found(async_client, mock_db, librarian_token):
    issued_id = "507f191e810c19729de860ea"
    mock_db["issued_collection"].delete_one.return_value.deleted_count = 0
    response = await async_client.delete(
        f"/issued/{issued_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Issued record not found"


@pytest.mark.asyncio
async def test_delete_issued_book_invalid_id(async_client, mock_db, librarian_token):
    invalid_id = "invalidid"
    response = await async_client.delete(
        f"/issued/{invalid_id}", headers={"Authorization": f"Bearer {librarian_token}"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid ID"


# Tests for Student Fine Endpoints......................................................................................................................


# from unittest.mock import AsyncMock, patch

# @pytest.mark.asyncio
# @patch("app.routers.student_fine.datetime")  # Patch datetime in the router module
# @patch("app.routers.student_fine.issued_collection")  # Patch issued_collection used in the route
# @patch("app.routers.student_fine.student_fine_collection")  # Patch student_fine_collection used in the route
# async def test_create_student_fine(
#     mock_student_fine_collection,
#     mock_issued_collection,
#     mock_datetime,
#     async_client,
#     librarian_token
# ):
#     # Fix current datetime
#     fake_now = datetime(2024, 1, 5, 12, 0, 0)
#     mock_datetime.now.return_value = fake_now
#     mock_datetime.fromisoformat = datetime.fromisoformat  # keep fromisoformat usable

#     # Mock issued book record found (issued 5 days ago, returned late)
#     issued_id = ObjectId("507f191e810c19729de860ea")
#     student_id = "507f1f77bcf86cd799439012"
#     mock_issued_collection.find_one = AsyncMock(return_value={
#         "_id": issued_id,
#         "student_id": student_id,
#         "return_date": fake_now - timedelta(days=5),  # 5 days ago
#         "is_returned": False,
#     })

#     # Mock inserting fine returns inserted_id
#     inserted_fine_id = ObjectId()
#     async def insert_one_mock(fine):
#         fine["_id"] = inserted_fine_id
#         return AsyncMock(inserted_id=inserted_fine_id)
#     mock_student_fine_collection.insert_one = insert_one_mock

#     # Payload with fine amount per day 50.0 (expect 5 days * 50 = 250)
#     payload = {
#         "student_id": student_id,
#         "book_id": "60d5ec49f8d2e86f1f3f83b1",
#         "issued_book_id": str(issued_id),
#         "fine_amount": 50.0,
#         "is_paid": False,
#     }

#     # Make POST request
#     response = await async_client.post(
#         "/student_fines/",
#         json=payload,
#         headers={"Authorization": f"Bearer {librarian_token}"}
#     )

#     # Assert successful creation
#     assert response.status_code == 200
#     data = response.json()
#     # The fine amount in response should be days overdue * fine_amount
#     assert data["fine_amount"] == 5 * 50.0
#     assert data["student_id"] == student_id
#     assert data["is_paid"] is False


# @pytest.mark.asyncio
# async def test_get_student_fines(async_client, mock_student_fine_collection,librarian_token):
#     student_id = "507f1f77bcf86cd799439012"

#     # Mock the find method to return an async iterator
#     mock_student_fine_collection.find = AsyncMock(return_value=AsyncIterator([
#         {
#             "_id": ObjectId("507f191e810c19729de860ea"),
#             "student_id": student_id,
#             "book_id": "60d5ec49f8d2e86f1f3f83b1",
#             "issued_book_id": "507f191e810c19729de860ea",
#             "fine_amount": 100.0,
#             "fine_date": datetime.utcnow().isoformat(),
#             "is_paid": False
#         }
#     ]))

#     response = await async_client.get(f"/student_fines/", headers={
#         "Authorization": f"Bearer {librarian_token}"
#     })
#     assert response.status_code == 200
#     data = response.json()
#     assert isinstance(data, list)
#     assert len(data) > 0
#     assert data[0]["student_id"] == student_id
