from pydantic import ConfigDict,BaseModel,Field,EmailStr

from datetime import datetime


class UserBase(BaseModel):
    username: str= Field(min_length=1, max_length=100)
    email: EmailStr= Field(max_length=120)



    
class Usercreate(UserBase):
    password: str= Field(min_length=8)


class UserPublic(BaseModel):
    model_config=ConfigDict(from_attributes=True)

    
    id: int
    username: str

    image_file: str | None
    image_path: str


class UserPrivate(UserPublic):
    email: EmailStr

class UserUpdate(UserBase):
    username: str | None= Field(default=None,min_length=1, max_length=100)
    email: EmailStr= Field(default=None,max_length=120)
    image_file: str | None= Field(default=None,min_length=1, max_length=200)

class Token(BaseModel):
    access_token:str
    token_type: str

class Postbase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content:str = Field(min_length=1)


class Postcreate(Postbase):
    user_id:int
    pass

class Postupdate(Postbase):
    title: str | None = Field(default=None,min_length=1, max_length=100)
    content:str | None = Field(default=None,min_length=1)

class PostResponse(Postbase):
    model_config=ConfigDict(from_attributes=True)

    id:int
    user_id:int
    date_posted:datetime
    author:UserPublic

