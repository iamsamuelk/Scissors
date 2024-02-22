from pydantic import ConfigDict, BaseModel
from typing import Optional

# URL Schema
class URLBase(BaseModel):
    target_url: str
    custom_key: Optional[str] = None

class URL(URLBase):
    is_active: bool
    clicks: int
    model_config = ConfigDict(from_attributes=True)

class URLInfo(URL):
    url: str
    
class URLCreate(URL):
    user_id: int
    
# User Schema
class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    

# Token Schema
class Token(BaseModel):
    access_token: str
    token_type: str