from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

# password hashing
pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")


# JWT settings
SECRET_KEY = "3GvZhLwZyMJl4zS9B8tRhrGfF9LxkIArEWTCLXrwMnc"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hash_password):
    return pwd_context.verify(plain_password, hash_password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    
