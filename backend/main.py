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

# --- 2. Configuração da "Pequena IA" ---
IA_ERROR_THRESHOLD = 5
IA_TIME_WINDOW_SECONDS = 60
recent_errors = deque()

# --- 3. Configuração do Banco de Dados (MongoDB) ---
MONGO_URL = os.environ.get("MONGO_CONNECTION_URL")
if not MONGO_URL:
    print("ERRO: MONGO_CONNECTION_URL não definida.")
    # Usamos uma string de fallback para o motor não falhar na importação
    MONGO_URL = "mongodb://user:pass@host/db_fallback" 
    
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client.liveops # Acede à base de dados 'liveops'
events_collection = db.events # Acede à coleção 'events'
users_collection = db.users   # NOVO: Acede à coleção 'users'

# --- 4. NOVO: Configuração de Segurança (JWT & Hashing) ---

# Cole a sua chave secreta gerada (do Passo 3) AQUI
SECRET_KEY = "f3eca3acafa72c1b233cb241b98b261ab39f5f68f141cf8f7dec1a1b14503fd1"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 

# Contexto para Hashing de Senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema OAuth2 (diz ao FastAPI como "ler" o token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# --- 5. Configuração do App FastAPI ---
app = FastAPI(
    title="LiveOps Dashboard Backend",
    description="Processa, salva, protege e distribui eventos.",
    version="0.3.0"
)

# --- 6. Configuração do CORS ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",  # React (Vite) a aceder a localhost
    "http://127.0.0.1:5173"  # React (Vite) a aceder a 127.0.0.1
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 7. Modelos de Dados (Eventos) ---
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

# --- 8. NOVO: Modelos de Dados (Segurança e Utilizadores) ---
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

# --- 9. NOVO: Funções de Segurança (Hashing & Tokens) ---

def verify_password(plain_password, hashed_password):
    """Verifica se a senha simples corresponde ao hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Gera um hash para a senha."""
    return pwd_context.hash(password)

async def get_user(username: str):
    """Busca um utilizador na coleção 'users' do MongoDB."""
    user = await users_collection.find_one({"username": username})
    if user:
        return UserInDB(**user)
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria um novo token de acesso JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Decodifica o token e retorna o utilizador."""
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

# --- 10. Gestor de WebSocket ---
class ConnectionManager:
    # ... (O código do ConnectionManager não muda) ...
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

# --- 11. Função da "Pequena IA" (Sem mudanças) ---
async def check_anomaly(event: Event):
    # ... (O código do check_anomaly não muda) ...
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

# --- 12. NOVO: Endpoints de Autenticação ---

@app.post("/auth/register", response_model=User)
async def register_user(user: UserCreate):
    """Regista um novo utilizador."""
    existing_user = await get_user(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este nome de utilizador já existe.",
        )
    
    hashed_password = get_password_hash(user.password)
    user_in_db = UserInDB(username=user.username, hashed_password=hashed_password)
    
    # Converte para dict antes de inserir no MongoDB
    new_user_data = user_in_db.model_dump()
    
    await users_collection.insert_one(new_user_data)
    
    # Retorna o modelo User, não o UserInDB (para não expor o hash)
    return User(username=user_in_db.username)

@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Gera um token de acesso (login)."""
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


# --- 13. Endpoint de Eventos (PROTEGIDO) ---

@app.post("/api/event")
async def receive_event(event: Event, current_user: User = Depends(get_current_user)):
    """
    Recebe um evento (PROTEGIDO), salva, checa anomalias e distribui.
    """
    
    
    event_dict = event.model_dump()
    try:
        await events_collection.insert_one(event_dict)
    except Exception as e:
        print(f"Erro ao salvar no MongoDB: {e}")

    event_json = event.model_dump_json()
    await manager.broadcast(event_json)
    await check_anomaly(event)

    return {"status": "ok", "saved": True, "user": current_user.username}

# --- 14. Endpoints de Histórico (BI) (PROTEGIDOS) ---

@app.get("/api/history/summary-24h")
async def get_history_summary(current_user: User = Depends(get_current_user)):
    """Calcula KPIs das últimas 24h (PROTEGIDO)."""
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
    """Retorna vendas agrupadas por hora (PROTEGIDO)."""
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

# --- 15. WebSocket Endpoint (PROTEGIDO) ---

async def get_current_user_from_token_query(token: str):
    """Função auxiliar para validar o token vindo do query param do WebSocket."""
    try:
        # Reutiliza a lógica de get_current_user, mas
       
        return await get_current_user(token=token)
    except HTTPException:
        return None

        # --- 15. NOVO: Endpoint de "Top Produtos" (BI) ---

@app.get("/api/history/top-products-24h")
async def get_top_products_summary(current_user: User = Depends(get_current_user)):
    """
    Retorna os 5 produtos mais vendidos (por quantidade) nas últimas 24h.
    """
    print("Recebida requisição de top produtos /api/history/top-products-24h")

    # 1. Definir o período
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)

    # 2. Criar a "pipeline" de agregação
    top_products_pipeline = [
        {
            # Filtra apenas compras nas últimas 24h
            "$match": {
                "timestamp": {"$gte": start_time.isoformat() + "Z", "$lt": end_time.isoformat() + "Z"},
                "event_type": "purchase_complete"
            }
        },
        {
            # Agrupa pelo nome do produto e soma a quantidade
            "$group": {
                "_id": "$metadata.product_name", # Agrupa por nome
                "total_quantity": {"$sum": "$metadata.quantity"} # Soma as quantidades
            }
        },
        {
            # Ordena do mais vendido (maior) para o menos vendido
            "$sort": {"total_quantity": -1} 
        },
        {
            # Pega apenas os 5 primeiros
            "$limit": 5
        },
        {
            # Formata a saída para o Recharts (nome, valor)
            "$project": {
                "_id": 0, # Remove o _id
                "name": "$_id", # Renomeia _id para 'name'
                "value": "$total_quantity" # Renomeia total_quantity para 'value'
            }
        }
    ]

    # 3. Executar a consulta
    try:
        top_products = await events_collection.aggregate(top_products_pipeline).to_list(length=5)
    except Exception as e:
        print(f"Erro ao consultar top produtos: {e}")
        return {"error": "Falha ao consultar o banco de dados"}

    print(f"Top 5 produtos enviados: {len(top_products)} produtos.")
    return top_products



@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """Mantém a conexão WebSocket viva (PROTEGIDO)."""
    
    # Valida o token recebido no parâmetro 'token' da URL
    user = await get_current_user_from_token_query(token)
    if user is None:
        # Se o token for inválido, fecha a conexão
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


# --- 16. Eventos de Inicialização/Desligamento ---
@app.on_event("startup")
async def startup_db_client():
    print("Conectando ao MongoDB...")
    try:
        await db_client.admin.command('serverStatus')
        print("Conectado ao MongoDB com sucesso!")
        
        # NOVO: Criar índice único para nomes de utilizador
       
        await users_collection.create_index("username", unique=True)
        print("Índice de utilizadores garantido.")
        
    except Exception as e:
        print(f"FALHA AO CONECTAR no MongoDB Atlas ou criar índice: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    print("Fechando conexão com o MongoDB...")
    db_client.close()

# --- 17. Rodar o Servidor ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)