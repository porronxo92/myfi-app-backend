# Sistema de Gestión de Usuarios - Documentación Completa

## 📋 Resumen

Se ha implementado un sistema completo de gestión de usuarios siguiendo la estructura y patrones existentes del proyecto FastAPI.

---

## 🗂️ Archivos Creados

### 1. **Modelo ORM** - `app/models/user.py`
Define la tabla `users` en la base de datos con SQLAlchemy.

**Campos:**
- `id` (UUID): Primary key, generado automáticamente
- `email` (String 255): Único, requerido, con validación de formato
- `username` (String 50): Único, opcional
- `password_hash` (String 255): Hash bcrypt de la contraseña
- `full_name` (String 100): Nombre completo, opcional
- `is_active` (Boolean): Usuario activo/inactivo (default: True)
- `is_admin` (Boolean): Permisos de administrador (default: False)
- `last_login` (DateTime): Última fecha de login, opcional
- `created_at` (DateTime): Fecha de creación automática
- `updated_at` (DateTime): Fecha de actualización automática

**Relaciones:**
- `accounts`: Un usuario tiene muchas cuentas (1:N)
- Cascade delete: Al borrar usuario se borran sus cuentas

**Métodos:**
- `to_dict()`: Convierte a diccionario (sin password_hash por seguridad)
- `account_count`: Property que cuenta las cuentas del usuario

---

### 2. **Schemas Pydantic** - `app/schemas/user.py`

**UserCreate** - POST /api/users
```python
{
  "email": "usuario@example.com",
  "username": "usuario123",
  "password": "Password123!",
  "full_name": "Juan Pérez"
}
```
- Validación de email con EmailStr
- Password mínimo 8 caracteres

**UserUpdate** - PUT /api/users/{id}
```python
{
  "full_name": "Juan Pérez García",
  "is_active": true,
  "password": "NewPassword123!"  // Opcional
}
```
- Todos los campos opcionales

**UserLogin** - POST /api/users/login
```python
{
  "email": "usuario@example.com",
  "password": "Password123!"
}
```

**UserResponse** - Respuestas GET
```python
{
  "id": "uuid",
  "email": "usuario@example.com",
  "username": "usuario123",
  "full_name": "Juan Pérez",
  "is_active": true,
  "is_admin": false,
  "last_login": "2025-12-22T10:30:00",
  "created_at": "2025-01-15T08:00:00",
  "account_count": 3
}
```
- **IMPORTANTE**: `password_hash` NUNCA se devuelve
- Serialización automática de datetime a ISO string

**PasswordChange** - POST /api/users/{id}/change-password
```python
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!"
}
```

---

### 3. **Servicio de Lógica** - `app/services/user_service.py`

**Métodos principales:**

#### Hashing de contraseñas (bcrypt)
- `_hash_password(password)`: Hashea contraseña con bcrypt
- `_verify_password(plain, hashed)`: Verifica contraseña

#### CRUD Básico
- `get_all(db, skip, limit, is_active)`: Listar con paginación
- `get_by_id(db, user_id)`: Obtener por UUID
- `get_by_email(db, email)`: Buscar por email
- `get_by_username(db, username)`: Buscar por username
- `create(db, user_data)`: Crear nuevo usuario
- `update(db, user_id, user_data)`: Actualizar usuario
- `delete(db, user_id)`: Eliminar usuario (cascade a cuentas)
- `get_total_count(db, is_active)`: Contar usuarios

#### Autenticación
- `authenticate(db, email, password)`: Login
  - Verifica email existe
  - Verifica usuario activo
  - Verifica contraseña
  - Actualiza `last_login`

#### Cambio de contraseña
- `change_password(db, user_id, password_data)`: Cambiar password
  - Verifica contraseña actual
  - Hashea y guarda nueva contraseña

**Validaciones automáticas:**
- Email único (lanza ValueError si existe)
- Username único (lanza ValueError si existe)
- Contraseñas siempre hasheadas (nunca en texto plano)

---

### 4. **Endpoints REST** - `app/routes/users.py`

#### POST /api/users - Crear usuario
- **Auth**: Requiere API Key
- **Request**: UserCreate
- **Response**: UserResponse (201 Created)

#### GET /api/users - Listar usuarios
- **Auth**: Requiere API Key
- **Query params**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 20)
  - `is_active` (bool, opcional)
- **Response**: PaginatedResponse con UserResponse[]

#### GET /api/users/{user_id} - Obtener usuario
- **Auth**: Requiere API Key
- **Response**: UserResponse

#### PUT /api/users/{user_id} - Actualizar usuario
- **Auth**: Requiere API Key
- **Request**: UserUpdate
- **Response**: UserResponse

#### DELETE /api/users/{user_id} - Eliminar usuario
- **Auth**: Requiere API Key
- **Response**: 204 No Content
- **Nota**: También elimina las cuentas del usuario (cascade)

#### POST /api/users/login - Login
- **Auth**: NO requiere API Key
- **Request**: UserLogin
- **Response**: UserResponse si credenciales correctas
- **Error**: 401 Unauthorized si fallan credenciales

#### POST /api/users/{user_id}/change-password - Cambiar contraseña
- **Auth**: Requiere API Key
- **Request**: PasswordChange
- **Response**: `{"message": "Contraseña actualizada correctamente"}`
- **Error**: 400 Bad Request si contraseña actual incorrecta

---

## 🔗 Relaciones con Otras Entidades

### Modificaciones en `app/models/account.py`

Se agregó la relación con usuarios:

```python
# Nueva columna en Account
user_id = Column(
    UUID(as_uuid=True),
    ForeignKey('users.id', ondelete='CASCADE'),
    nullable=True,  # Para compatibilidad con datos existentes
    comment="Usuario propietario de la cuenta (FK)"
)

# Nueva relación
user = relationship(
    "User",
    back_populates="accounts"
)
```

**Comportamiento:**
- `user_id` es nullable para no romper cuentas existentes
- Al borrar un usuario, se borran sus cuentas (CASCADE)
- Al borrar una cuenta, el usuario permanece

---

## 🗃️ Base de Datos

### Script SQL: `sql_create_users_table.sql`

**Ejecutar en PostgreSQL:**

```sql
-- 1. Crear tabla users
CREATE TABLE users (...);

-- 2. Crear índices
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- 3. Agregar columna user_id a accounts
ALTER TABLE accounts ADD COLUMN user_id UUID;

-- 4. Agregar foreign key
ALTER TABLE accounts
ADD CONSTRAINT fk_accounts_user 
FOREIGN KEY (user_id) 
REFERENCES users(id) 
ON DELETE CASCADE;

-- 5. Crear índice para JOINs
CREATE INDEX idx_accounts_user_id ON accounts(user_id);
```

**Usuarios de prueba incluidos:**
1. **Admin**: 
   - Email: `admin@example.com`
   - Username: `admin`
   - Password: `Test123!`
   - is_admin: `true`

2. **Usuario regular**:
   - Email: `user@example.com`
   - Username: `usuario`
   - Password: `User123!`
   - is_admin: `false`

---

## 📦 Dependencias Agregadas

**requirements.txt:**
```
bcrypt==4.2.1          # Hashing seguro de contraseñas
email-validator==2.2.0 # Validación de emails en Pydantic
```

**Instalación:**
```bash
pip install bcrypt==4.2.1 email-validator==2.2.0
```

---

## 🔐 Seguridad

### Hashing de Contraseñas (bcrypt)
- **Salt rounds**: 12 (por defecto en bcrypt)
- **Algoritmo**: bcrypt (resistente a rainbow tables y GPU cracking)
- **Nunca** se almacenan contraseñas en texto plano
- **Nunca** se devuelven hashes en respuestas API

### Validaciones
- **Email**: Formato válido (regex en DB + EmailStr en Pydantic)
- **Contraseña**: Mínimo 8 caracteres
- **Unicidad**: Email y username únicos en DB

### Rate Limiting
- Todos los endpoints (excepto /login) protegidos con rate limit
- Login también tiene rate limit para prevenir brute force

---

## 🧪 Ejemplos de Uso

### 1. Crear usuario
```bash
curl -X POST "http://localhost:8000/api/users" \
  -H "X-API-Key: 52ba344c0282e5d826837fd59b6f5cca" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo@example.com",
    "username": "nuevo_usuario",
    "password": "MiPassword123!",
    "full_name": "Nuevo Usuario"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Test123!"
  }'
```

### 3. Listar usuarios activos
```bash
curl "http://localhost:8000/api/users?is_active=true&page=1&page_size=10" \
  -H "X-API-Key: 52ba344c0282e5d826837fd59b6f5cca"
```

### 4. Actualizar usuario
```bash
curl -X PUT "http://localhost:8000/api/users/{user_id}" \
  -H "X-API-Key: 52ba344c0282e5d826837fd59b6f5cca" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Nombre Actualizado",
    "is_active": false
  }'
```

### 5. Cambiar contraseña
```bash
curl -X POST "http://localhost:8000/api/users/{user_id}/change-password" \
  -H "X-API-Key: 52ba344c0282e5d826837fd59b6f5cca" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "Test123!",
    "new_password": "NewPassword456!"
  }'
```

### 6. Eliminar usuario
```bash
curl -X DELETE "http://localhost:8000/api/users/{user_id}" \
  -H "X-API-Key: 52ba344c0282e5d826837fd59b6f5cca"
```

---

## 📊 Estructura del Proyecto Actualizada

```
backend/
├── app/
│   ├── models/
│   │   ├── __init__.py          ✅ Actualizado (importa User)
│   │   ├── account.py           ✅ Modificado (user_id, relación)
│   │   ├── category.py
│   │   ├── transaction.py
│   │   └── user.py              🆕 NUEVO
│   │
│   ├── schemas/
│   │   ├── __init__.py          ✅ Actualizado (importa user.*)
│   │   ├── account.py
│   │   ├── category.py
│   │   ├── transaction.py
│   │   ├── upload.py
│   │   └── user.py              🆕 NUEVO
│   │
│   ├── services/
│   │   ├── account_service.py
│   │   ├── category_service.py
│   │   ├── transaction_service.py
│   │   └── user_service.py      🆕 NUEVO
│   │
│   ├── routes/
│   │   ├── __init__.py          ✅ Actualizado (importa users)
│   │   ├── accounts.py
│   │   ├── categories.py
│   │   ├── transactions.py
│   │   ├── upload.py
│   │   └── users.py             🆕 NUEVO
│   │
│   ├── main.py                  ✅ Actualizado (registra router users)
│   └── ...
│
├── requirements.txt             ✅ Actualizado (bcrypt, email-validator)
└── sql_create_users_table.sql   🆕 NUEVO
```

---

## ✅ Checklist de Implementación

- [x] Modelo User con campos completos
- [x] Relación User → Accounts (1:N)
- [x] Schemas Pydantic (Create, Update, Response, Login, PasswordChange)
- [x] Servicio con CRUD completo
- [x] Hashing bcrypt de contraseñas
- [x] Validación de email único
- [x] Validación de username único
- [x] Endpoint de login (sin API Key)
- [x] Endpoint de cambio de contraseña
- [x] Paginación en listados
- [x] Rate limiting en todos los endpoints
- [x] Logger en todas las operaciones
- [x] Serialización datetime a ISO string
- [x] Script SQL para crear tabla
- [x] Datos de prueba en SQL
- [x] Modificación de Account con user_id
- [x] Actualización de __init__.py
- [x] Registro de router en main.py
- [x] Dependencias en requirements.txt

---

## 🚀 Próximos Pasos

1. **Ejecutar script SQL** en la base de datos:
   ```bash
   psql -U admin -d app_finance -f sql_create_users_table.sql
   ```

2. **Reiniciar servidor** (se recargará automáticamente si está en --reload)

3. **Probar endpoints** en http://localhost:8000/docs

4. **(Opcional) Asignar cuentas existentes a usuarios:**
   ```sql
   UPDATE accounts 
   SET user_id = (SELECT id FROM users WHERE email = 'admin@example.com')
   WHERE user_id IS NULL;
   ```

5. **(Futuro) Implementar JWT tokens** en lugar de solo API Key

---

## 📝 Notas Importantes

- **Contraseñas**: NUNCA se almacenan en texto plano, siempre bcrypt
- **API Key**: Login NO requiere API Key, resto de endpoints SÍ
- **Cascade Delete**: Al borrar usuario se borran sus cuentas
- **Compatibilidad**: `user_id` en accounts es nullable para no romper datos existentes
- **Validaciones**: Email y username únicos verificados en servicio y DB
- **Logging**: Todas las operaciones registradas en logs
