import uvicorn
import os
import pandas as pd
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from collections import deque

# --- 1. Bibliotecas de Segurança ---
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

# --- 2. NOVO: Bibliotecas do Simulador ---
import asyncio
import httpx
import random

# --- 3. Configuração da "Pequena IA" ---
IA_ERROR_THRESHOLD = 5
IA_TIME_WINDOW_SECONDS = 60
recent_errors = deque()

# --- 4. Configuração do Banco de Dados (MongoDB) ---
MONGO_URL = os.environ.get("MONGO_CONNECTION_URL")
if not MONGO_URL:
    print("ERRO: MONGO_CONNECTION_URL não definida.")
    MONGO_URL = "mongodb://user:pass@host/db_fallback" 
    
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client.liveops
events_collection = db.events
users_collection = db.users

# --- 5. Configuração de Segurança (JWT & Hashing) ---
SECRET_KEY = os.environ.get("SECRET_KEY") 
if not SECRET_KEY:
    print("AVISO: SECRET_KEY não definida.")
    SECRET_KEY = "f3eca3acafa72c1b233cb241b98b261ab39f5f68f141cf8f7dec1a1b14503fd1"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- 6. Configuração do App FastAPI ---
app = FastAPI(
    title="LiveOps Dashboard Backend",
    description="Processa, salva, protege e distribui eventos.",
    version="0.4.0" # Versão Nova
)

# --- 7. Configuração do CORS (Pronto para Deploy) ---
origins = ["*"] # Permite TODAS as origens
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 8. Modelos de Dados (Eventos) ---
class EventMetadata(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    order_id: Optional[str] = None
    total_amount: Optional[float] = None
    region: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    page_url: Optional[str] = None
    referrer: Optional[str] = None

class Event(BaseModel):
    user_id: str
    timestamp: str
    event_type: str
    metadata: EventMetadata

# --- 9. Modelos de Dados (Segurança) ---
class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    username: Optional[str] = None
class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
class UserInDB(User):
    hashed_password: str
class UserCreate(BaseModel):
    username: str
    password: str

# --- 10. Funções de Segurança (Hashing & Tokens) ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password):
    return pwd_context.hash(password)
async def get_user(username: str):
    user = await users_collection.find_one({"username": username})
    if user:
        return UserInDB(**user)
    return None
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = await get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# --- 11. Gestor de WebSocket ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Nova conexão! {len(self.active_connections)} clientes conectados.")
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Cliente desconectado. {len(self.active_connections)} clientes restantes.")
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except RuntimeError as e:
                print(f"Erro ao enviar: {e}. Removendo cliente.")
                self.disconnect(connection)
manager = ConnectionManager()

# --- 12. Função da "Pequena IA" ---
async def check_anomaly(event: Event):
    global recent_errors
    if event.event_type != 'payment_error':
        return
    now = datetime.utcnow()
    recent_errors.append(now)
    window_start_time = now - timedelta(seconds=IA_TIME_WINDOW_SECONDS)
    while recent_errors and recent_errors[0] < window_start_time:
        recent_errors.popleft()
    if len(recent_errors) >= IA_ERROR_THRESHOLD:
        print(f"ALERTA DE IA: {len(recent_errors)} erros nos últimos {IA_TIME_WINDOW_SECONDS} segundos!")
        alert_message = f"Anomalia Detectada: {len(recent_errors)} falhas de pagamento nos últimos {IA_TIME_WINDOW_SECONDS}s."
        alert_event = {
            "event_type": "IA_ALERT",
            "timestamp": now.isoformat() + "Z",
            "message": alert_message,
            "metadata": {"error_count": len(recent_errors)}
        }
        await manager.broadcast(json.dumps(alert_event))
        try:
            await events_collection.insert_one(alert_event)
        except Exception as e:
            print(f"Erro ao salvar alerta no DB: {e}")
        recent_errors.clear()

# --- 13. Endpoints de Autenticação ---
@app.post("/auth/register", response_model=User)
async def register_user(user: UserCreate):
    existing_user = await get_user(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este nome de utilizador já existe.",
        )
    hashed_password = get_password_hash(user.password)
    user_in_db = UserInDB(username=user.username, hashed_password=hashed_password)
    new_user_data = user_in_db.model_dump()
    await users_collection.insert_one(new_user_data)
    return User(username=user_in_db.username)

@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de utilizador ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- 14. Endpoint de Eventos (PROTEGIDO) ---
@app.post("/api/event")
async def receive_event(event: Event, current_user: User = Depends(get_current_user)):
    event_dict = event.model_dump()
    try:
        await events_collection.insert_one(event_dict)
    except Exception as e:
        print(f"Erro ao salvar no MongoDB: {e}")
    event_json = event.model_dump_json()
    await manager.broadcast(event_json)
    await check_anomaly(event)
    return {"status": "ok", "saved": True, "user": current_user.username}

# --- 15. Endpoints de Histórico (BI) (PROTEGIDOS) ---
@app.get("/api/history/summary-24h")
async def get_history_summary(current_user: User = Depends(get_current_user)):
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    sales_pipeline = [
        {"$match": {"timestamp": {"$gte": start_time.isoformat() + "Z", "$lt": end_time.isoformat() + "Z"}, "event_type": "purchase_complete"}},
        {"$group": {"_id": None, "total_sales": {"$sum": "$metadata.total_amount"}, "total_orders": {"$sum": 1}}}
    ]
    errors_pipeline = [
        {"$match": {"timestamp": {"$gte": start_time.isoformat() + "Z", "$lt": end_time.isoformat() + "Z"}, "event_type": "payment_error"}},
        {"$group": {"_id": None, "total_errors": {"$sum": 1}}}
    ]
    try:
        sales_result = await events_collection.aggregate(sales_pipeline).to_list(length=1)
        errors_result = await events_collection.aggregate(errors_pipeline).to_list(length=1)
    except Exception as e:
        print(f"Erro ao consultar agregação do MongoDB: {e}")
        return {"error": "Falha ao consultar o banco de dados"}
    summary = {"total_sales": 0, "total_orders": 0, "total_errors": 0}
    if sales_result:
        summary["total_sales"] = sales_result[0].get("total_sales", 0)
        summary["total_orders"] = sales_result[0].get("total_orders", 0)
    if errors_result:
        summary["total_errors"] = errors_result[0].get("total_errors", 0)
    return summary

@app.get("/api/history/sales-hourly-24h")
async def get_sales_hourly_summary(current_user: User = Depends(get_current_user)):
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    hourly_sales_pipeline = [
        {"$match": {"timestamp": {"$gte": start_time.isoformat() + "Z", "$lt": end_time.isoformat() + "Z"}, "event_type": "purchase_complete"}},
        {"$project": {"timestamp_date": {"$toDate": "$timestamp"}, "total_amount": "$metadata.total_amount"}},
        {"$group": {"_id": {"hour": {"$hour": "$timestamp_date"}}, "total_sales": {"$sum": "$total_amount"}}},
        {"$sort": {"_id.hour": 1}},
        {"$project": {"_id": 0, "hour": "$_id.hour", "sales": "$total_sales"}}
    ]
    try:
        sales_result = await events_collection.aggregate(hourly_sales_pipeline).to_list(length=24)
    except Exception as e:
        print(f"Erro ao consultar agregação horária: {e}")
        return {"error": "Falha ao consultar o banco de dados"}
    sales_map = {item['hour']: item['sales'] for item in sales_result}
    current_utc_hour = end_time.hour
    final_sales_data = []
    for i in range(24):
        hour_key = (current_utc_hour + 1 + i) % 24
        sales_value = sales_map.get(hour_key, 0)
        final_sales_data.append({"name": f"{hour_key:02d}:00", "Vendas": sales_value})
    return final_sales_data

@app.get("/api/history/user/{user_id}")
async def get_user_history(user_id: str, current_user: User = Depends(get_current_user)):
    # ... (código igual, não precisa mudar) ...
    print(f"Recebida requisição de histórico para o utilizador: {user_id}")
    summary_pipeline = [
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}, "total_value": {"$sum": "$metadata.total_amount"}}}
    ]
    events_pipeline = [
        {"$sort": {"timestamp": -1}},
        {"$limit": 100}
    ]
    main_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$facet": {"summary": summary_pipeline, "recent_events": events_pipeline}}
    ]
    try:
        result = await events_collection.aggregate(main_pipeline).to_list(length=1)
    except Exception as e:
        print(f"Erro ao consultar histórico do utilizador: {e}")
        raise HTTPException(status_code=500, detail="Falha ao consultar o banco de dados")
    if not result or not result[0]['summary']:
        return {"summary": [], "recent_events": []}
    print(f"Histórico do utilizador {user_id} enviado.")
    return result[0]

# --- 16. WebSocket Endpoint (PROTEGIDO) ---
async def get_current_user_from_token_query(token: str):
    try:
        return await get_current_user(token=token)
    except HTTPException:
        return None

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
  
    user = await get_current_user_from_token_query(token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(websocket)
    print(f"Utilizador '{user.username}' conectou-se ao WebSocket.")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Erro no WebSocket: {e}")
        manager.disconnect(websocket)

# --- 17. NOVO: LÓGICA DO SIMULADOR EMBUTIDO ---


RENDER_API_URL = "https://liveops-dashboard-fullstack.onrender.com" 
# Credenciais para o simulador fazer login
SIMULATOR_USER = "admin"
SIMULATOR_PASS = "1234" 


EVENT_TYPES = ["page_view", "add_to_cart", "remove_from_cart", "checkout_start", "payment_error", "purchase_complete", "user_login", "user_logout"]
PRODUCTS = [
    {"id": "P001", "name": "Smartwatch XYZ", "price": 299.99},
    {"id": "P002", "name": "Fone Bluetooth Mega", "price": 149.50},
    {"id": "P003", "name": "Carregador Portátil 10000mAh", "price": 75.00},
    {"id": "P004", "name": "Câmera de Segurança HD", "price": 350.00},
    {"id": "P005", "name": "Mouse Gamer Óptico", "price": 120.00},
]
REGIONS = ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Porto Alegre", "Curitiba", "Salvador", "Fortaleza", "Brasília"]

# Função de Geração de Eventos (copiada do simulador.py)
def generate_event_simulated():
    event_type = random.choice(EVENT_TYPES)
    user_id = f"user_{random.randint(1000, 9999)}"
    timestamp = datetime.utcnow().isoformat() + "Z"
    event_data = {"user_id": user_id, "timestamp": timestamp, "event_type": event_type, "metadata": {}}
    if event_type in ["add_to_cart", "remove_from_cart", "purchase_complete"]:
        product = random.choice(PRODUCTS)
        event_data["metadata"]["product_id"] = product["id"]
        event_data["metadata"]["product_name"] = product["name"]
        event_data["metadata"]["price"] = product["price"]
        event_data["metadata"]["quantity"] = random.randint(1, 3)
    if event_type == "purchase_complete":
        event_data["metadata"]["order_id"] = f"ORD{random.randint(100000, 999999)}"
        event_data["metadata"]["total_amount"] = round(product["price"] * event_data["metadata"]["quantity"], 2)
        event_data["metadata"]["region"] = random.choice(REGIONS)
    elif event_type == "payment_error":
        event_data["metadata"]["error_code"] = f"ERR{random.randint(100, 999)}"
        event_data["metadata"]["error_message"] = random.choice(["Cartão Recusado", "Transação Não Autorizada", "Limite Excedido"])
        event_data["metadata"]["region"] = random.choice(REGIONS)
    elif event_type == "page_view":
        event_data["metadata"]["page_url"] = random.choice(["/home", "/products", "/cart"])
        event_data["metadata"]["referrer"] = random.choice(["google", "facebook", "direct"])
    return event_data

# Função de Login (Assíncrona com httpx)
async def get_auth_token_async():
    print(f"A autenticar o simulador interno como '{SIMULATOR_USER}'...")
    login_data = {'username': SIMULATOR_USER, 'password': SIMULATOR_PASS}
    
   
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{RENDER_API_URL}/auth/token", data=login_data, timeout=60.0)
            if response.status_code == 200:
                print("Simulador interno autenticado com sucesso!")
                return response.json()['access_token']
            else:
                print(f"Erro ao autenticar simulador: {response.status_code} - {response.text}")
                return None
        except httpx.RequestError as e:
            print(f"Erro de conexão do simulador: {e}. O servidor já 'acordou'?")
            return None

# Loop Principal do Simulador (Assíncrono com httpx)
async def run_simulator_loop(token: str):
    print("Simulador interno INICIADO. A gerar dados em background...")
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                event = generate_event_simulated()
                response = await client.post(f"{RENDER_API_URL}/api/event", json=event, headers=headers, timeout=30.0)
                
                if response.status_code == 401:
                    print("Token do simulador expirou. A parar.")
                    break # Para o loop
                
                # Abrandar o simulador
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
            except httpx.RequestError as e:
                print(f"Erro de rede no simulador interno: {e}")
                await asyncio.sleep(10) # Espera 10s se houver erro de rede
            except Exception as e:
                print(f"Erro inesperado no loop do simulador: {e}")
                await asyncio.sleep(10)

# Função de "Arranque" do Simulador
async def start_simulator_task():
    print("Servidor arrancou. A aguardar 10s para o servidor estabilizar...")
    await asyncio.sleep(10) # Dá 10s para o servidor Uvicorn "acordar"
    
    token = await get_auth_token_async()
    if token:
        # Cria uma "tarefa" (task) que corre em background para sempre
        # sem bloquear o servidor principal
        asyncio.create_task(run_simulator_loop(token))
    else:
        print("Não foi possível obter token. O simulador interno NÃO VAI ARRANCAR.")


# --- 18. Eventos de Inicialização/Desligamento ---
@app.on_event("startup")
async def startup_db_client():
    print("Conectando ao MongoDB...")
    try:
        await db_client.admin.command('serverStatus')
        print("Conectado ao MongoDB com sucesso!")
        await users_collection.create_index("username", unique=True)
        print("Índice de utilizadores garantido.")
        
        # --- MUDANÇA: Ligar o simulador em background ---
        asyncio.create_task(start_simulator_task())
        
    except Exception as e:
        print(f"FALHA AO CONECTAR no MongoDB Atlas ou criar índice: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    print("Fechando conexão com o MongoDB...")
    db_client.close()

# --- 19. Rodar o Servidor (PARA PRODUÇÃO) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False) # reload=False é crucial




