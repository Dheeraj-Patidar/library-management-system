from fastapi import FastAPI
from app.routers import author, category, book, student, issuedbook,user, student_fine
# from app.middleware.auth_middleware import jwt_middleware
# from app.middleware.simple_middleware import simple_middleware

app = FastAPI()

# app.middleware("http")(jwt_middleware)  # Apply auth middleware
# app.middleware("http")(simple_middleware)  # Apply simple middleware

app.include_router(user.router)
app.include_router(author.router, prefix='/author', tags=['author'])
app.include_router(category.router)
app.include_router(book.router)
app.include_router(student.router)
app.include_router(issuedbook.router)
app.include_router(student_fine.router) 