from typing import Annotated
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm

from fastapi import APIRouter,Depends,HTTPException, status,Request
from sqlalchemy import select,func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth import (
    create_access_token,verify_access_token,hash_password,verify_password,oauth2_scheme
)

from config import settings


import models
from database import get_db
from schemas import PostResponse,Usercreate,UserPrivate,UserPublic,UserUpdate,Token

router=APIRouter()

@router.post(
        "",
        response_model=UserPrivate,
        status_code=status.HTTP_201_CREATED
        )
async def create_user(user:Usercreate,db: Annotated[AsyncSession, Depends(get_db)]):

    result= await db.execute(
        select(models.User)
        .where(func.lower(models.User.username)==user.username.lower())
        )

    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User name already exists"
            )
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == user.email.lower()),
    )
    
    existing_email=result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
            )
    
    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password)
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/token",response_model=Token)
async def login_for_access_token(
    from_data:Annotated[OAuth2PasswordRequestForm,Depends()],
    db:Annotated[AsyncSession,Depends(get_db)],
):
    
    result= await db.execute(select(models.User).where(
        func.lower(models.User.email)==from_data.username.lower()
    ))

    user= result.scalars().first()

    if not user and not verify_password(from_data.password,user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWw-Authenticate":"Bearer"},
        )
    access_token_expire=timedelta(minutes=settings.access_token_expire_minutes)
    access_token=create_access_token(
        data={"sub":str(user.id)},
        expires_data=access_token_expire
    )

    return Token(access_token=access_token,token_type="Bearer")


@router.get("/me",response_model=UserPrivate)
async def get_current_user(
    #  here this "oauth2_scheme" is used to extract token from auth headers
    token:Annotated[str,Depends(oauth2_scheme)],

    db:Annotated[AsyncSession,Depends(get_db)],
):
    user_id=verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id_int=int(user_id)
    except(TypeError,ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result= await db.execute(select(models.User).where(models.User.id==user_id_int))

    user= result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,detail="User not found", headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user
    

@router.get("",response_model=list[UserPublic])
async def get_all_users(request:Request,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.User))
    user=result.scalars().all()
    return user

@router.get("/{user_id}",response_model=UserPrivate,status_code=status.HTTP_200_OK)
async def get_user(user_id:int,db:Annotated[AsyncSession,Depends(get_db)]):

    result= await db.execute(select(models.User).where(models.User.id==user_id))

    user= result.scalars().first()

    if user:
        return user
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
        )

@router.get("/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id:int,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.User).where(models.User.id==user_id))
     
    user=result.scalars().first()

    if not user:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User posts not found"
    )

    posts=await db.execute(select(models.Post)
                           .options(selectinload(models.Post.author))
                           .where(models.Post.user_id==user.id)
                           .order_by(models.Post.date_posted.desc()))
    user_posts=posts.scalars().all()
    return user_posts



@router.patch("/{user_id}",response_model=UserPrivate)
async def Update_user_full(user_id:int,user_update:UserUpdate,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.User).where(models.User.id==user_id))
    user=result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not fouxnd"
        )
    
    if user_update.username is not None and user_update.username.lower() != user.username.lower():
        result=await db.execute(select(models.User).where(func.lower(models.User.username) == user_update.username.lower()))
        username=result.scalars().first()
        if username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exist"
            )
        
    if user_update.email is not None and user_update.email != user.email:
        result= await db.execute(select(models.User).where(func.lower(models.User.email)==user_update.email.lower()))
        email=result.scalars().first()
        if email:
              raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exist"
            )
        
    updated_data=user_update.model_dump(exclude_unset=True)
    for field,value in updated_data.items():
        setattr(user,field,value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}",status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id:int,
                db:Annotated[AsyncSession,Depends(get_db)]): 
    result= await db.execute(select(models.User).where(models.User.id==user_id))
    user=result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    await db.delete(user)
    await db.commit()