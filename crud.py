from fastapi import Depends, HTTPException, status, Request, Form
from sqlalchemy.orm import Session
from routers.auth import get_current_user
from typing import Annotated

import keygen, models, schemas

user_dependency= Annotated [models.User, Depends(get_current_user)]

def create_db_url(user:user_dependency, 
                  db: Session, 
                  target_url: str = Form(...), 
                  custom_key: str = Form(...)) -> models.URL:
    if custom_key:
        # Validate custom URL (length, characters, uniqueness, etc.)
        # Raise appropriate exceptions for validation errors
        db_url = create_db_url_by_custom_key(user, db, target_url, custom_key)
    else:
        key = keygen.create_unique_random_key(db)
        secret_key = f"{key}_{keygen.create_random_key(length=8)}"
        db_url = models.URL(
            target_url=target_url,
            key=key,
            secret_key=secret_key,
            user_id=user.get('id')
        )
        db.add(db_url)
        db.commit()
        db.refresh(db_url)
        return db_url
    
def create_db_url_by_custom_key(user:user_dependency, 
                                db: Session, 
                                target_url: str = Form(...), 
                                custom_key: str = Form(...)) -> models.URL:
    key = keygen.create_unique_random_key(db, custom_key=custom_key)
    secret_key = f"{key}_{keygen.create_random_key(length=8)}"

    db_url = models.URL(
        target_url=target_url,
        key=key,
        secret_key=secret_key,
        custom_key=custom_key,
        user_id=user.get('id')
    )
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    return db_url

def get_db_url_by_key(db: Session, url_key: str) -> models.URL:
    return (
        db.query(models.URL)
        .filter(models.URL.key == url_key, models.URL.is_active)
        .first()
    )
    
def get_db_url_by_secret_key(user: user_dependency, db: Session, secret_key: str) -> models.URL:
    return (
        db.query(models.URL)
        .filter(models.URL.secret_key == secret_key)
        .filter(models.URL.user_id == user.get('id'))
        .first()
    )
    
def get_db_url_by_custom_key(user: user_dependency, db: Session, custom_key: str) -> models.URL:
    return (
        db.query(models.URL)
        .filter(models.URL.custom_key == custom_key)
        .filter(models.URL.user_id == user.get('id'))
        .first()
    )

def update_db_clicks(db: Session, db_url: schemas.URL) -> models.URL:
    db_url.clicks += 1
    db.commit()
    db.refresh(db_url)
    return db_url

def activate_db_url_by_secret_key(user: user_dependency, db: Session, secret_key: str) -> models.URL:
    db_url = get_db_url_by_secret_key(user, db, secret_key)
    if db_url:
        db_url.is_active = True
        db.commit()
        db.refresh(db_url)
    return db_url

def deactivate_db_url_by_secret_key(user: user_dependency, db: Session, secret_key: str) -> models.URL:
    db_url = get_db_url_by_secret_key(user, db, secret_key)
    if db_url:
        db_url.is_active = False
        db.commit()
        db.refresh(db_url)
    return db_url