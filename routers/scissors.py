from fastapi import Depends, HTTPException, Request, status, APIRouter, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from starlette.datastructures import URL
from datetime import datetime
import crud, models, schemas, validators, io, requests
from database import SessionLocal, engine
from config import get_settings
from .auth import get_current_user

scissors_router = APIRouter()

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates") 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency= Annotated [models.User, Depends(get_current_user)]


# ***********   FUNCTIONS  ************

async def get_current_url(request: Request, db: db_dependency) -> Optional[models.URL]:
    url = request.url.path
    if url == "/url-details":
        url_key = request.query_params.get("key")
        if url_key:
            url = db.query(models.URL).filter(models.URL.key == url_key).first()
            return url
    return None


def get_admin_info(db_url: models.URL) -> schemas.URLInfo:
    base_url = URL(get_settings().base_url)
    db_url.url = str(base_url.replace(path=db_url.key))
    return db_url


# ***********   ROUTES  ************

@scissors_router.get("/", response_class=HTMLResponse)
async def read_all_by_user(request:Request, db: db_dependency):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    urls = db.query(models.URL).filter(models.URL.user_id == user.get("id")).all()

    return templates.TemplateResponse("home.html", {"request": request, "urls": urls})


@scissors_router.get("/url-details", response_class=HTMLResponse)
async def read_all_by_url(request:Request, db: db_dependency):
    url = await get_current_url(request, db)
    if url is None:
        return RedirectResponse("/home", status_code=status.HTTP_302_FOUND)
    
    clicks = db.query(models.Click).filter(models.Click.url_id == url.id).all()

    return templates.TemplateResponse("url-details.html", {"request": request, "clicks": clicks, "url": url})


@scissors_router.get("/create-url", response_class=HTMLResponse)
async def create_new_url(request:Request):
    return templates.TemplateResponse("create-url.html", {"request": request})

@scissors_router.post("/create-url", response_class=HTMLResponse)
async def create_new_url_post(request:Request, 
                              db: db_dependency, 
                              target_url: str = Form(...), 
                              custom_key: str = Form(...)):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    if not validators.url(target_url):
        msg = "Your provided URL is not valid"
        return templates.TemplateResponse("create-url.html", {"request": request, "msg": msg})
        
    if custom_key is None:
        db_url = crud.create_db_url(user, db, target_url, custom_key)
    
    custom_key_in_db = (db.query(models.URL).filter(models.URL.custom_key == custom_key).first())
    if custom_key_in_db:
        if custom_key_in_db.custom_key:
            msg = "Custom URL Name already exists, choose another name"
            return templates.TemplateResponse("create-url.html", {"request": request, "msg": msg})
    
    # Validate custom URL (if provided)
    if custom_key:
        if len(custom_key) > 20:  # Adjust length limit as needed
            msg = "Custom URL cannot be longer than 20 characters"
            return templates.TemplateResponse("create-url.html", {"request": request, "msg": msg})
        if not custom_key.isalnum():  # Modify allowed characters as needed
            msg = "Custom URL Name can only contain alphanumeric characters with no spaces in between"
            return templates.TemplateResponse("create-url.html", {"request": request, "msg": msg})

        # Check for existing custom URL (optional, add if needed)
        existing_url = crud.get_db_url_by_custom_key(user=user, db=db, custom_key=custom_key)
        if existing_url:
            raise HTTPException(
                status_code=409,  # Use 422 for conflicts here
                detail="Custom URL already exists. URL already shortened as: "
                f"{get_settings().base_url}/{existing_url.key}"
            )
        db_url = crud.create_db_url_by_custom_key(user, db, target_url, custom_key)
    else:
        db_url = crud.create_db_url(user, db, target_url, custom_key)
    db_url = get_admin_info(db_url)
    schemas.URLInfo.url = db_url.url
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


# Important for the whole project - This is the redirecting code
@scissors_router.get("/{url_key}")
def forward_to_target_url(
        url_key: str,
        request: Request,
        db: db_dependency
    ):
    if db_url := crud.get_db_url_by_key(db=db, url_key=url_key):
        click = models.Click(url_id=db_url.id, timestamp=datetime.utcnow())
        if request.client.host:  # Check if IP is available
            click.ip_address = request.client.host  # Use responsibly and disclose collection
        db.add(click)
        crud.update_db_clicks(db=db, db_url=db_url)
        return RedirectResponse(db_url.target_url)
    else:
        raise HTTPException(status_code=404, detail=f"URL '{request.url}' doesn't exist")


@scissors_router.get("/activate/{secret_key}", response_class=HTMLResponse)
async def activate_url(request: Request, secret_key: str, db: db_dependency):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    db_url = crud.activate_db_url_by_secret_key(user=user, db=db, secret_key=secret_key)
        
    if db_url is None:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
        
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


@scissors_router.get("/deactivate/{secret_key}", response_class=HTMLResponse)
async def deactivate_url(request: Request, secret_key: str, db: db_dependency):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    
    db_url = crud.deactivate_db_url_by_secret_key(user=user, db=db, secret_key=secret_key)
    
    if db_url is None:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)







# ROUTERS USED FOR FASTAPI DOCS

# @scissors_router.get("/test")
# async def test(request: Request):
#     return templates.TemplateResponse("home.html", {"request": request})

# @scissors_router.get("/", status_code=status.HTTP_200_OK)
# async def read_all(user: user_dependency, db: db_dependency):
#     all_urls = db.query(models.URL).filter(models.URL.user_id == user.get('id')).all()
#     return all_urls  

# def raise_bad_request(message):
#     raise HTTPException(status_code=400, detail=message)

# def raise_not_found(request):
#     message = f"URL '{request.url}' doesn't exist"
#     raise HTTPException(status_code=404, detail=message)


# @scissors_router.post("/short_url", response_model=schemas.URLInfo, status_code=status.HTTP_201_CREATED)
# def create_url(user: user_dependency,
#                db: db_dependency,
#                url: schemas.URLBase):
#     if user is None:
#         raise HTTPException(status_code=401, detail="Authentication Failed")
#     if not validators.url(url.target_url):
#         raise_bad_request(message="Your provided URL is not valid")
    
#     if url.custom_key is None:
#         db_url = crud.create_db_url(db=db, url=url)
    
#     # Validate custom URL (if provided)
#     if url.custom_key:
#         if len(url.custom_key) > 20:  # Adjust length limit as needed
#             raise_bad_request(message="Custom URL cannot be longer than 20 characters")
#         if not url.custom_key.isalnum():  # Modify allowed characters as needed
#             raise_bad_request(message="Custom URL can only contain alphanumeric characters")

#         # Check for existing custom URL (optional, add if needed)
#         existing_url = crud.get_db_url_by_custom_key(user=user, db=db, custom_key=url.custom_key)
#         if existing_url:
#             raise HTTPException(
#                 status_code=409,  # Use 422 for conflicts here
#                 detail="Custom URL already exists. URL already shortened as: "
#                 f"{get_settings().base_url}/{existing_url.key}"
#             )
#         db_url = crud.create_db_url_by_custom_key(user=user,db=db, url=url, custom_key=url.custom_key)
#     else:
#         db_url = crud.create_db_url(user=user,db=db, url=url)
#     db_url = get_admin_info(db_url)
#     schemas.URLInfo.url = db_url.url
#     db.add(db_url)
#     db.commit()
#     db.refresh(db_url)
#     return db_url

# # Important for the whole project - This is the redirecting code
# @scissors_router.get("/{url_key}")
# def forward_to_target_url(
#         url_key: str,
#         request: Request,
#         db: db_dependency
#     ):
#     if db_url := crud.get_db_url_by_key(db=db, url_key=url_key):
#         click = models.Click(url_id=db_url.id, timestamp=datetime.utcnow())
#         if request.client.host:  # Check if IP is available
#             click.ip_address = request.client.host  # Use responsibly and disclose collection
#         db.add(click)
#         crud.update_db_clicks(db=db, db_url=db_url)
#         return RedirectResponse(db_url.target_url)
#     else:
#         raise_not_found(request)     
        
# @scissors_router.get(
#     "/admin/{secret_key}",
#     name="URL info",
#     response_model=schemas.URLInfo,
#     status_code=status.HTTP_200_OK
# )
# def get_url_info(
#     user: user_dependency, secret_key: str, request: Request, db: db_dependency
# ):
#     if user is None:
#         raise HTTPException(status_code=401, detail="Authentication Failed")
#     if db_url := crud.get_db_url_by_secret_key(user=user, db=db, secret_key=secret_key):
#         return get_admin_info(db_url)
#     else:
#         raise_not_found(request)
        
        
# def get_admin_info(db_url: models.URL) -> schemas.URLInfo:
#     base_url = URL(get_settings().base_url)
#     admin_endpoint = scissors_router.url_path_for(
#         "URL info", secret_key=db_url.secret_key
#     )
#     db_url.url = str(base_url.replace(path=db_url.key))
#     db_url.admin_url = str(base_url.replace(path=admin_endpoint))
#     return db_url


# @scissors_router.put("/admin/deactivate/{secret_key}")
# def deactivate_url(
#     user: user_dependency, secret_key: str, request: Request, db: db_dependency
# ):
#     if user is None:
#         raise HTTPException(status_code=401, detail="Authentication Failed")
#     if db_url := crud.deactivate_db_url_by_secret_key(user, db, secret_key=secret_key):
#         message = f"Successfully deactivated shortened URL for '{db_url.target_url}'"
#         return {"detail": message}
#     else:
#         raise_not_found(request)
       
        
# @scissors_router.put("/admin/reactivate/{secret_key}")
# def reactivate_url(
#     user: user_dependency, secret_key: str, request: Request, db: db_dependency
# ):
#     if user is None:
#         raise HTTPException(status_code=401, detail="Authentication Failed")
#     if db_url := crud.reactivate_db_url_by_secret_key(user=user, db=db, secret_key=secret_key):
#         message = f"Successfully reactivated shortened URL for '{db_url.target_url}'"
#         return {"detail": message}
#     else:
#         raise_not_found(request)