import os
import requests
import json
import logging
import traceback
import random

from dotenv import load_dotenv
from fastapi import HTTPException

from models.UserRegister import UserRegister
from models.UserLogin import UserLogin
from models.EmailActivation import EmailActivation

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

from utils.database import fetch_query_as_json
from utils.security import create_jwt_token

from azure.storage.queue import QueueClient, BinaryBase64DecodePolicy, BinaryBase64EncodePolicy


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar la app de Firebase Admin
cred = credentials.Certificate("secrets/firebase-secret.json")
firebase_admin.initialize_app(cred)


load_dotenv()


azure_sak = os.getenv('AZURE_SAK')
queue_name = os.getenv('QUEUE_ACTIVATE')


queue_client = QueueClient.from_connection_string(azure_sak, queue_name)
queue_client.message_decode_policy = BinaryBase64DecodePolicy()
queue_client.message_encode_policy = BinaryBase64EncodePolicy()

async def insert_message_on_queue(message: str):
     message_bytes = message.encode('utf-8')
     queue_client.send_message(
         queue_client.message_encode_policy.encode(message_bytes)
     )


async def register_user_firebase(user: UserRegister):
    user_record = {}
    try:
        # Crear usuario en Firebase Authentication
        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password
        )

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {e}"
        )\
    
    query = f"INSERT INTO exampleprep.users (email, firstname, lastname,active) VALUES ('{user.email}', '{user.firstname}', '{user.lastname}',0);"
    result = {}
    try:

        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]

        await insert_message_on_queue(user.email)

        return result

    except Exception as e:
        firebase_auth.delete_user(user_record.uid)
        raise HTTPException(status_code=500, detail=str(e))


async def login_user_firebase(user: UserLogin):
    try:
        # Autenticar usuario con Firebase Authentication usando la API REST
        api_key =os.getenv("API_KEY_FIREBASE") # Reemplaza esto con tu apiKey de Firebase
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": user.email,
            "password": user.password,
            "returnSecureToken": True
        }
        response = requests.post(url, json=payload)
        response_data = response.json()

        if "error" in response_data:
            raise HTTPException(
                status_code=400,
                detail=f"Error al autenticar usuario: {response_data['error']['message']}"
            )

        query = f"""select 
                        email
                        , firstname
                        , lastname
                        , active
                    from [exampleprep].[users]
                    where email = '{ user.email }'
                    """

        try:
            result_json = await fetch_query_as_json(query)
            result_dict = json.loads(result_json)
            return {
                "message": "Usuario autenticado exitosamente",
                "idToken": create_jwt_token(
                    result_dict[0]["firstname"],
                    result_dict[0]["lastname"],
                    user.email,
                    result_dict[0]["active"]
                )
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        error_detail = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(
            status_code=400,
            detail=f"Error al login usuario: {error_detail}"
        )


async def generate_activation_code(email: EmailActivation):

    code = random.randint(100000, 999999)
    query =  f"EXEC exampleprep.generate_activation_code @Email = '{email.email}', @Code = {code}"
    result = {}
    try:
        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "estegmail":email.email,
        "mira_loco":result,
        "message": "Código de activación generado exitosamente",
        "code": code
    }

async def put_activation_code(email: EmailActivation, code: int):
    query = f"EXEC exampleprep.VerifyAndActivateUser_Test @Email ='{email.email}', @Code = {code}"
    result = {}
    
    try:
        # Realiza la consulta
        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]  # Asumimos que el primer elemento tiene la respuesta

        # Verifica si el código ha expirado
        if result.get("Message") == 'Código expirado':
            # Loguea el correo
            logger.info("MIRAAAAAAAAAAAA ACA ESTA EL CORREO: %s", email.email)
            
            # Inserta el correo nuevamente en la cola
            await insert_message_on_queue(email.email)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "estegmail": email.email,
        "serverResponse": result,
        "message": "Código de activación generado exitosamente",
        "code": code
    }

async def time_code(email: EmailActivation):
    query = f"EXEC [exampleprep].GetRecentActivationCodeWithTimeElapsed @Email ='{email.email}'"
    result = {}
    
    try:
        # Realiza la consulta
        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]  # Asumimos que el primer elemento tiene la respuesta



    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
     
        "serverResponse": result
        
    }

# SET ANSI_NULLS ON
# GO

# SET QUOTED_IDENTIFIER ON
# GO

# CREATE PROCEDURE [exampleprep].[generate_activation_code](
#   @Email NVARCHAR(255),
# @Code INT
# )
  
# AS
# BEGIN
#     SET NOCOUNT ON;

#     DECLARE @n INT=SELECT @n = COUNT(*) FROM [exampleprep].[users] WHERE [email] = @Email;

#     IF @n > 0
#     BEGIN
#         INSERT INTO [exampleprep].[activation_codes] ([email], [code]) VALUES (@Email, @Code);
#     END;

#     -- Retorna un valor de control (opcional)
#     SELECT 1 AS Completed;

# END;
# GO