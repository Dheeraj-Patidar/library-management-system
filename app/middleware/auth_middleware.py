# # app/middleware/jwt_auth.py
# from fastapi import Request
# from fastapi.responses import JSONResponse
# import jwt

# SECRET_KEY = "3GvZhLwZyMJl4zS9B8tRhrGfF9LxkIArEWTCLXrwMnc" 

# async def jwt_middleware(request: Request, call_next):
#     if request.url.path.startswith("/public"):
#         return await call_next(request)

#     auth_header = request.headers.get("Authorization")

#     if not auth_header or not auth_header.startswith("Bearer "):
#         print("Missing or invalid Authorization header")
#         return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})

#     token = auth_header.split(" ")[1]

#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
#         request.state.user = payload
#     except jwt.ExpiredSignatureError:
#         return JSONResponse(status_code=401, content={"detail": "Token expired"})
#     except jwt.InvalidTokenError:
#         return JSONResponse(status_code=401, content={"detail": "Invalid token"})

#     return await call_next(request)


