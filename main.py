import json
import uvicorn
from urllib.parse import unquote
from typing import Union
from fastapi import FastAPI, HTTPException, Response, Request
from utils.database import fetch_query_as_json
from utils.security import validate, validate_func

from fastapi.middleware.cors import CORSMiddleware
from models.UserRegister import UserRegister
from models.UserLogin import UserLogin
from models.EmailActivation import EmailActivation

from controllers.firebase import register_user_firebase, login_user_firebase, generate_activation_code,put_activation_code,time_code

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos
    allow_headers=["*"],  # Permitir todos los encabezados
)

@app.get("/")
async def read_root(response: Response):
    response.headers["Cache-Control"] = "no-cache"
    # query = "select * from exampleprep.hello"
    query = "select * from [exampleprep].[users]"
    try:
        result = await fetch_query_as_json(query)
        result_dict = json.loads(result) #Este nos ayuda para converit en diccionario
        result_dict = {
            "data": result_dict
            , "version": "0.0.7"
        }
        return result_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/register")
async def register(user: UserRegister):
    return  await register_user_firebase(user)

@app.post("/login")
async def login_custom(user: UserLogin):
    return await login_user_firebase(user)

@app.get("/user")
@validate
async def user(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-cache";
    return {
        "email": request.state.email
        , "firstname": request.state.firstname
        , "lastname": request.state.lastname
    }

@app.post("/user/{email}/code")
@validate_func
async def generate_code(request: Request, email: str):
    e = EmailActivation(email=email)
    return await generate_activation_code(e)

@app.post("/user/{email}/{code}/code2") #este nos ayuda a activar la cuenta
async def generate_code(request: Request, email: str,code: int):
    e = EmailActivation(email=email)
    return await put_activation_code(e,code)




@app.get("/user/activationcode/{email}") # nos ayuda a ver si el usuario esta activado

async def read_activation_code(email: str, response: Response):
    response.headers["Cache-Control"] = "no-cache"
    query = f"""
    	select active from [exampleprep].[users] e where e.email='{email}'

    """
    try:
        result = await fetch_query_as_json(query)
        result_dict = json.loads(result)

        # Asumimos que la consulta retorna un array con el resultado
       
        return result_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/timecode/{email}")
async def generate_code(request: Request, email: str):
    e = EmailActivation(email=email)
    return await time_code(e)
    

    
    

        
                            
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


# import json
# import uvicorn
# from typing import Union

# from fastapi import FastAPI, HTTPException

# from utils.database import fetch_query_as_json
# from fastapi.middleware.cors import CORSMiddleware


# app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
#     allow_credentials=True
# )

# @app.get("/")
# async def read_root():
#     query = "select * from syac.users"
#     try:
#         result = await fetch_query_as_json(query)
#         result_dict = json.loads(result)
#         return { "data": result_dict, "version": "0.0.3" }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": str(item_id) + "holapppp", "q": q}
# if __name__ == '__main__':
#     uvicorn.run(app, host="0.0.0.0", port=8000)
