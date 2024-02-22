from fastapi import APIRouter, Depends, status, Response, Request, HTTPException, Form
import schemas, models
from passlib.context import CryptContext
from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional



router = APIRouter()

class LoginForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        
    async def create_outh_form(self):
        form = await self.request.form()
        self.username = form.get("email")
        self.password = form.get("password")

templates = Jinja2Templates(directory="templates")

SECRET_KEY = "511c840c9015ae04929d52c4176d711dd8dd7836183df091306c96547e10df40"
ALGORITHM = "HS256"

bcrpyt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

def authenticate_user(username: str, password: str, db):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return False
    
    if not bcrpyt_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.now() + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(request: Request):
    try:
        token = request.cookies.get("access_token")
        if token is None:
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])    
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if username is None or user_id is None:
            raise None
        return {"username": username, "id": user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid authentication credentials")

# Create a new user
@router.post("/auth/create_user", status_code=status.HTTP_201_CREATED)
async def Create_user(db: db_dependency, create_user_request: schemas.CreateUserRequest):
    create_user_model = models.User(
        username = create_user_request.username,
        email = create_user_request.email,
        hashed_password = bcrpyt_context.hash(create_user_request.password),
    )
    db.add(create_user_model)
    db.commit()


@router.post("/auth/token", response_model=schemas.Token)
async def login_for_access_token(response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    
    if not user:
        return False
    
    token = create_access_token(user.username, user.id, timedelta(minutes=60))
    
    response.set_cookie(key="access_token", value=token, httponly=True)
    
    return True
    

@router.get("/auth", response_class=HTMLResponse)
async def authenticationpage(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/auth", response_class=HTMLResponse)
async def login(request:Request, db: db_dependency):
    try:
        form = LoginForm(request)
        await form.create_outh_form()
        response = RedirectResponse(url="/scissors", status_code=status.HTTP_302_FOUND)
        
        validate_user_cookie = await login_for_access_token(response=response, form_data=form, db=db)
        
        if not validate_user_cookie:
            msg = "Invalid username or password"
            return templates.TemplateResponse("login.html", {"request": request, "msg": msg})
        return response
    except HTTPException:
        msg = "Unknown error"
        return templates.TemplateResponse("login.html", {"request": request, "msg": msg})


@router.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    msg = "Logout successfully"
    response = templates.TemplateResponse("login.html", {"request": request, "msg": msg})
    response.delete_cookie(key="access_token")
    return response


@router.get("/auth/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/auth/register", response_class=HTMLResponse)
async def register_user(request: Request, db: db_dependency, username: str = Form(...), email: str = Form(...),
                        password: str = Form(...), password2: str = Form(...),):
    
    validation1 = db.query(models.User).filter(models.User.username == username).first()
    
    validation2 = db.query(models.User).filter(models.User.email == email).first()
    
    if validation1 is not None or validation2 is not None:
        msg = "Username or email already exists"
        return templates.TemplateResponse("register.html", {"request": request, "msg": msg})
    
    if password != password2:
        msg = "Passwords don't match"
        return templates.TemplateResponse("register.html", {"request": request, "msg": msg})
    
    user_model = models.User()
    user_model.username = username
    user_model.email = email
    user_model.hashed_password = bcrpyt_context.hash(password)
    
    db.add(user_model)
    db.commit()
    
    msg = "Registered successfully"
    return templates.TemplateResponse("login.html", {"request": request, "msg": msg})