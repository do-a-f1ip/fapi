from contextlib import asynccontextmanager
from typing import Annotated

from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler
)


from fastapi import FastAPI,Request,HTTPException,status,Depends
# from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as  starletteHTTPException
from router import Posts,Users


from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


import models
from database import  Base,engine, get_db
from schemas import Postcreate,PostResponse

# Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()




app= FastAPI(lifespan=lifespan)

app.mount("/static",StaticFiles(directory="static"),name="static")

app.mount("/media", StaticFiles(directory="media"),name="media")

templates= Jinja2Templates(directory='templates')

app.include_router(Users.router,prefix="/api/user",tags=["Users"])
app.include_router(Posts.router,prefix="/api/post",tags=["Posts"])


@app.get("/",name="home",include_in_schema=False)
async def Start(request:Request,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts=result.scalars().all()
    return templates.TemplateResponse( 
        request,
        "home.html",
        {"posts":posts,"title":"Home"}
    )


@app.get("/post/{post_id}",include_in_schema=False)
async def post_page(request:Request,post_id:int,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(
                        select(models.Post)
                        .options(selectinload(models.Post.author))
                         .where(models.Post.id==post_id))
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

@app.get("/users/{user_id}/posts",include_in_schema=False,name="user_posts")
async def user_posts(request:Request,user_id:int,db:Annotated[AsyncSession,Depends(get_db)]):
    result= await db.execute(select(models.User).where(models.User.id==user_id))
    user=result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    posts=await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id==user_id))
    user_post=posts.scalars().all()

    return templates.TemplateResponse( 
        request, 
        "user_posts.html",
        {"posts":user_posts,"user":user,
        "title":f"{user.username}'s Posts"} )
    








@app.exception_handler(starletteHTTPException)
async def general_http_exception_handler(request:Request, exception:starletteHTTPException):
    if request.url.path.startswith("/api"):
        return http_exception_handler(request, exception)
    

    message=(
        exception.detail
        if exception.detail
        else " An error occurred. Please check your request and try again."
    )



    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message, 
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )




