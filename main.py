from typing import Annotated


from fastapi import FastAPI,Request,HTTPException,status,Depends
# from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as  starletteHTTPException
from schemas import Postcreate,PostResponse,Usercreate,UserResponse

from sqlalchemy import select

from sqlalchemy.orm import Session

import models
from database import  Base,engine, get_db
from schemas import Postcreate,PostResponse

Base.metadata.create_all(bind=engine)



app= FastAPI()

app.mount("/static",StaticFiles(directory="static"),name="static")

app.mount("/media", StaticFiles(directory="media"),name="media")

templates= Jinja2Templates(directory='templates')


@app.get("/",name="home",include_in_schema=False)
def Start(request:Request,db:Annotated[Session,Depends(get_db)]):
    result=db.execute(select(models.Post))
    posts=result.scalars().all()
    return templates.TemplateResponse( 
        request,
        "home.html",
        {"posts":posts,"title":"Home"}
    )


@app.get("/post/{post_id}",include_in_schema=False)
def post_page(request:Request,post_id:int,db:Annotated[Session,Depends(get_db)]):
    result=db.execute(select(models.Post).where(models.Post.id==post_id))
    post=result.scalars().first()
    
    if post:
        title=post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post":post,"title":title}
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found"
        )


@app.get("user/{user_id}",include_in_schema=False,name="user_posts")
def user_posts(request:Request,user_id:int,db:Annotated[Session,Depends(get_db)]):
    result=db.execute(select(models.User).where(models.User.id==user_id))
    user=result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    posts=db.execute(select(models.Post).where(models.Post.user_id==user_id))
    user_post=posts.scalars().all()

    return templates.TemplateResponse( 
        request, 
        "user_posts.html",
        {"posts":user_posts,"user":user,
        "title":f"{user.username}'s Posts"} )
        





    


@app.post(
        "/api/users",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED
        )
def create_user(user:Usercreate,db: Annotated[Session, Depends(get_db)]):
    print(user.username)
    print(user.email)

    result= db.execute(
        select(models.User).where(models.User.username==user.username)
        )

    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User name already exists"
            )
    result = db.execute(
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
    db.commit()
    db.refresh(new_user)
    return new_user
    
@app.get("/api/user/",response_model=list[UserResponse])
def get_all_users(request:Request,db:Annotated[Session,Depends(get_db)]):
    result=db.execute(select(models.User))
    user=result.scalars().all()
    return user

@app.get("/api/user/{user_id}",response_model=UserResponse,status_code=status.HTTP_200_OK)
def get_user(user_id:int,db:Annotated[Session,Depends(get_db)]):

    result=db.execute(select(models.User).where(models.User.id==user_id))

    user= result.scalars().first()

    if user:
        return user
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
        )
    
    
    

@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(user_id:int,db:Annotated[Session,Depends(get_db)]):
    result=db.execute(select(models.User).where(models.User.id==user_id))
     
    user=result.scalars().first()

    if not user:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User posts not found"
    )

    posts=db.execute(select(models.Post).where(models.Post.user_id==user.id))
    user_posts=posts.scalars().all()
    return user_posts





    
    
# WORKING 


@app.get("/api/posts",response_model=list[PostResponse])
def get_posts(db:Annotated[Session,Depends(get_db)]):
    result= db.execute(select(models.Post))
    posts=result.scalars().all()
    return posts
    

@app.get("/api/post/{post_id}",response_model=PostResponse)
def get_post(post_id :int,db:Annotated[Session,Depends(get_db)]):
    result=db.execute(select(models.Post).where(models.Post.id==post_id))
    posts=result.scalars().first()
    if posts:
        return posts
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Posts not found"
    )



@app.post("/api/posts",response_model=PostResponse,status_code=status.HTTP_201_CREATED)
def create_post(post:Postcreate,db:Annotated[Session,Depends(get_db)]):

    result=db.execute(select(models.User).where(models.User.id==post.user_id))
    user=result.scalars().all()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    new_post=models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
          )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


# @app.exception_handler(starletteHTTPException)
# def general_http_exception_handler(request:Request, exception:starletteHTTPException):
#     message=(
#         exception.detail
#         if exception.detail
#         else " An error occurred. Please check your request and try again."
#     )

#     if request.url.path.startswith("/api"):
#         return JSONResponse(
#             status_code=exception.status_code,
#             content={"detail": message},
#         )

#     return templates.TemplateResponse(
#         request,
#         "error.html",
#         {
#             "status_code": exception.status_code,
#             "title": exception.status_code,
#             "message": message, 
#         },
#         status_code=exception.status_code,
#     )


# @app.exception_handler(RequestValidationError)
# def validation_exception_handler(request: Request, exception: RequestValidationError):
#     if request.url.path.startswith("/api"):
#         return JSONResponse(
#             status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
#             content={"detail": exception.errors()},
#         )

#     return templates.TemplateResponse(
#         request,
#         "error.html",
#         {
#             "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
#             "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
#             "message": "Invalid request. Please check your input and try again.",
#         },
#         status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
#     )




