from typing import Annotated

from fastapi import APIRouter,Depends,HTTPException, status,Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import PostResponse,Usercreate,UserResponse,UserUpdate

router=APIRouter()

@router.post(
        "",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED
        )
async def create_user(user:Usercreate,db: Annotated[AsyncSession, Depends(get_db)]):

    result= await db.execute(
        select(models.User)
        .where(models.User.username==user.username)
        )

    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User name already exists"
            )
    result = await db.execute(
        select(models.User).where(models.User.email == user.email),
    )
    
    existing_email=result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
            )
    new_user = models.User(
        username=user.username,
        email=user.email,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("",response_model=list[UserResponse])
async def get_all_users(request:Request,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.User))
    user=result.scalars().all()
    return user

@router.get("/{user_id}",response_model=UserResponse,status_code=status.HTTP_200_OK)
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
                           .where(models.Post.user_id==user.id))
    user_posts=posts.scalars().all()
    return user_posts



@router.patch("/{user_id}",response_model=UserResponse)
async def Update_user_full(user_id:int,user_update:UserUpdate,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.User).where(models.User.id==user_id))
    user=result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not fouxnd"
        )
    
    if user_update.username is not None and user_update.username != user.username:
        result=await db.execute(select(models.User).where(models.User.username == user_update.username))
        username=result.scalars().first()
        if username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exist"
            )
        
    if user_update.email is not None and user_update.email != user.email:
        result= await db.execute(select(models.User).where(models.User.email==user_update.email))
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