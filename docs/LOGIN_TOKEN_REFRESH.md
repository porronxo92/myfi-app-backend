## 🔑 Access Token (30 minutos)
**Uso:** Para **TODAS las peticiones** a la API

```javascript
// Ejemplo de petición con access_token
fetch('http://localhost:8000/api/accounts', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  }
})
```

**Características:**
- ⏱️ **Corta duración**: 30 minutos
- 🔒 **Se envía en cada petición** como header `Authorization: Bearer <token>`
- 🎯 **Es el que valida tu identidad** en endpoints protegidos

## 🔄 Refresh Token (7 días)
**Uso:** Solo para **renovar** el access_token cuando expire

```javascript
// Solo cuando el access_token expire (error 401)
fetch('http://localhost:8000/api/users/refresh', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    refresh_token: refresh_token
  })
})
```

**Características:**
- ⏱️ **Larga duración**: 7 días
- 🔄 **Se usa UNA sola vez** cada 30 minutos (cuando access_token expira)
- 💾 **Guárdalo de forma segura** (localStorage/sessionStorage)

---

## 📱 Flujo completo en el Frontend

```javascript
// 1. LOGIN - Guardar ambos tokens
async function login(email, password) {
  const response = await fetch('http://localhost:8000/api/users/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  const data = await response.json();
  
  // Guardar en localStorage
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  localStorage.setItem('user', JSON.stringify(data.user));
  
  return data;
}

// 2. PETICIONES NORMALES - Usar access_token
async function apiRequest(url, options = {}) {
  const access_token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${access_token}`,
      'Content-Type': 'application/json',
      ...options.headers
    }
  });
  
  // Si el token expiró (401), renovarlo
  if (response.status === 401) {
    const renewed = await renewAccessToken();
    if (renewed) {
      // Reintentar la petición con el nuevo token
      return apiRequest(url, options);
    } else {
      // Refresh token también expiró, redirigir a login
      window.location.href = '/login';
      return;
    }
  }
  
  return response.json();
}

// 3. RENOVAR TOKEN - Usar refresh_token
async function renewAccessToken() {
  const refresh_token = localStorage.getItem('refresh_token');
  
  if (!refresh_token) {
    return false;
  }
  
  try {
    const response = await fetch('http://localhost:8000/api/users/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token })
    });
    
    if (!response.ok) {
      return false;
    }
    
    const data = await response.json();
    
    // Guardar los NUEVOS tokens
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    
    return true;
  } catch (error) {
    console.error('Error renovando token:', error);
    return false;
  }
}

// 4. EJEMPLO DE USO
async function getAccounts() {
  return apiRequest('http://localhost:8000/api/accounts');
}

async function uploadFile(file) {
  const formData = new FormData();
  formData.append('fichero', file);
  
  return apiRequest('http://localhost:8000/api/upload', {
    method: 'POST',
    body: formData,
    headers: {} // FormData gestiona Content-Type automáticamente
  });
}
```

---

## 📊 Resumen visual

```
┌─────────────────────────────────────────────────────┐
│ LOGIN                                               │
│ ──────────────────────────────────────────────────  │
│  POST /api/users/login                              │
│  → Devuelve: access_token + refresh_token           │
│  → Guardar AMBOS en localStorage                    │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ PETICIONES NORMALES (30 min)                        │
│ ──────────────────────────────────────────────────  │
│  GET /api/accounts                                  │
│  Authorization: Bearer {access_token}  ✅           │
└─────────────────────────────────────────────────────┘
                      ↓
              ⏰ Después de 30 min
                      ↓
┌─────────────────────────────────────────────────────┐
│ RENOVAR TOKEN                                       │
│ ──────────────────────────────────────────────────  │
│  POST /api/users/refresh                            │
│  Body: { refresh_token }                            │
│  → Devuelve: NUEVO access_token + refresh_token     │
│  → Actualizar localStorage                          │
└─────────────────────────────────────────────────────┘
                      ↓
              🔄 Repetir ciclo
```

---

## 🎯 Respuesta directa

**Para integrar en tu frontend:**

1. **Guarda ambos tokens** después del login
2. **Usa `access_token`** en TODAS las peticiones (header `Authorization: Bearer ...`)
3. **Cuando recibas error 401** (token expirado), usa `refresh_token` para renovar
4. **Actualiza ambos tokens** después de cada renovación

El `refresh_token` te permite que el usuario **NO tenga que hacer login cada 30 minutos**, sino que su sesión dure **7 días** renovándose automáticamente en segundo plano.