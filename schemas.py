from pydantic import ConfigDict,BaseModel,Field

class Postbase(BaseModel):
    title:str =Field(min_length=1,max_length=100)
    content:str = Field(min_length=1)
    author:str = Field(min_length=1,max_length=100)

class Postcreate(Postbase):
    pass

class PostResponse(Postbase):
    model_config=ConfigDict(from_attributes=True)

    id:int
    date_posted:str

