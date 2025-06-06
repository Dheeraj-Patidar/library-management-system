# from fastapi import Request
# import time

# async def simple_middleware(request: Request, call_next):
#     print(f" Middleware triggered on {request.method} {request.url.path}")
#     start = time.time()
#     response = await call_next(request)
#     duration = time.time() - start
#     print(f"✔ Done in {duration:.4f}s")
#     return response
# # 