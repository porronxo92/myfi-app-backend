# API: Actualizar Foto de Perfil

**Fecha:** 2026-03-01  
**Endpoint:** `PUT /api/users/me/profile-picture`  
**Autenticación:** JWT Bearer Token requerido

## Descripción

Actualiza la foto de perfil del usuario autenticado. El backend acepta la imagen en formato base64 o como data URL, valida el formato y almacena el base64 encriptado en la base de datos.

## Request

### Método HTTP
```
PUT /api/users/me/profile-picture
```

### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Body (JSON) - REQUERIDO

⚠️ **IMPORTANTE:** La imagen DEBE enviarse en el body JSON, NO como query parameter en la URL.

**¿Por qué?** Los query parameters tienen límites de tamaño (~2-8 KB). Las imágenes en base64 son mucho más grandes y causan error **431 (Request Header Fields Too Large)** si se envían en la URL.

#### Formato 1: Data URL completa (recomendado)

```json
{
  "profile_picture": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/..."
}
```

#### Formato 2: Base64 puro

```json
{
  "profile_picture": "/9j/4AAQSkZJRgABAQEAYABgAAD/..."
}
```

## Response

### Éxito (200 OK)
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "usuario123",
  "full_name": "Juan Pérez",
  "profile_picture": "/9j/4AAQSkZJRgABAQEAYABgAAD...",  // ⚠️ Base64 PURO (sin prefijo data:)
  "is_active": true,
  "is_admin": false,
  "last_login": "2026-03-01T10:30:00Z",
  "created_at": "2025-01-15T08:00:00Z",
  "account_count": 3
}
```

⚠️ **IMPORTANTE:** El campo `profile_picture` contiene **solo el base64 puro**, sin el prefijo `data:image/...;base64,`.

**Para mostrarlo en HTML**, debes agregar el prefijo:

```typescript
// ❌ NO FUNCIONA
<img [src]="user.profile_picture" />

// ✅ FUNCIONA
<img [src]="'data:image/jpeg;base64,' + user.profile_picture" />
```

Ver sección **"Mostrar la Imagen"** más abajo para soluciones completas.

### Errores

#### 400 Bad Request - Formato inválido
```json
{
  "detail": "Formato de data URL inválido"
}
```
o
```json
{
  "detail": "El campo profile_picture no contiene base64 válido"
}
```

#### 401 Unauthorized - Token inválido
```json
{
  "detail": "Could not validate credentials"
}
```

#### 404 Not Found - Usuario no encontrado
```json
{
  "detail": "Usuario no encontrado"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Error interno del servidor"
}
```

## Integración Frontend

### ⚠️ Cambio Necesario en tu Frontend Angular

**Problema actual:** Tu frontend está enviando la imagen como query parameter en la URL, causando error 431.

**Solución:** Cambiar de query parameter a body JSON.

#### ❌ Implementación Incorrecta (causa error 431):

```typescript
// NO HACER ESTO - Envía en la URL (límite de tamaño)
updateProfilePicture(imageBase64: string): Observable<User> {
  const url = `${this.apiUrl}/users/me/profile-picture?profile_picture_url=${imageBase64}`;
  return this.http.put<User>(url, {}, { headers: { 'Authorization': `Bearer ${this.getToken()}` } });
}
```

#### ✅ Implementación Correcta (body JSON):

```typescript
// HACER ESTO - Envía en el body JSON
updateProfilePicture(imageBase64: string): Observable<User> {
  const url = `${this.apiUrl}/users/me/profile-picture`;
  
  return this.http.put<User>(url, {
    profile_picture: imageBase64  // ← Enviar en el body, no en la URL
  }, {
    headers: {
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    }
  });
}
```

### Angular/TypeScript (Completo)

```typescript
// Servicio de usuario
updateProfilePicture(imageBase64: string): Observable<User> {
  const url = `${this.apiUrl}/users/me/profile-picture`;
  
  return this.http.put<User>(url, {
    profile_picture: imageBase64  // Puede ser data URL o base64 puro
  }, {
    headers: {
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    }
  });
}

// Componente - Manejo de input file
onFileSelected(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    const base64String = reader.result as string; // "data:image/jpeg;base64,..."
    
    this.userService.updateProfilePicture(base64String).subscribe({
      next: (user) => {
        console.log('Foto de perfil actualizada', user);
        this.currentUser = user;
      },
      error: (error) => {
        console.error('Error al actualizar foto de perfil', error);
      }
    });
  };
  
  reader.readAsDataURL(file);
}
```

### JavaScript/Fetch

```javascript
async function updateProfilePicture(file) {
  // Convertir archivo a base64
  const reader = new FileReader();
  
  reader.onload = async function() {
    const base64String = reader.result; // "data:image/jpeg;base64,..."
    
    try {
      const response = await fetch('http://localhost:8000/api/users/me/profile-picture', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          profile_picture: base64String
        })
      });
      
      if (!response.ok) {
        throw new Error('Error al actualizar foto de perfil');
      }
      
      const user = await response.json();
      console.log('Usuario actualizado:', user);
    } catch (error) {
      console.error('Error:', error);
    }
  };
  
  reader.readAsDataURL(file);
}

// Uso con input file
document.getElementById('fileInput').addEventListener('change', function(e) {
  const file = e.target.files[0];
  if (file) {
    updateProfilePicture(file);
  }
});
```

### React

```jsx
import { useState } from 'react';
import axios from 'axios';

function ProfilePictureUpload() {
  const [uploading, setUploading] = useState(false);

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);

    // Convertir a base64
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const response = await axios.put(
          'http://localhost:8000/api/users/me/profile-picture',
          {
            profile_picture: reader.result // Data URL
          },
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            }
          }
        );
        
        console.log('Foto actualizada:', response.data);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setUploading(false);
      }
    };
    
    reader.readAsDataURL(file);
  };

  return (
    <div>
      <input 
        type="file" 
        accept="image/*" 
        onChange={handleFileChange}
        disabled={uploading}
      />
      {uploading && <p>Subiendo...</p>}
    </div>
  );
}
```

## Notas Importantes

1. **Formato aceptado:** El backend acepta tanto data URL (`data:image/jpeg;base64,...`) como base64 puro. Se recomienda usar data URL desde el frontend con `FileReader.readAsDataURL()`.

2. **Validación:** El backend valida que el string sea base64 válido antes de almacenar.

3. **Encriptación:** El base64 se almacena **encriptado** en la base de datos usando AES-256-GCM (cumplimiento GDPR/PSD2).

4. **Tamaño:** No hay límite específico en el endpoint, pero se recomienda comprimir/redimensionar imágenes grandes en el frontend antes de enviar (máx. 2-3 MB recomendado).

5. **Formatos de imagen soportados:** Cualquier formato que el navegador pueda convertir a base64 (JPEG, PNG, GIF, WebP, etc.).

## Ejemplo cURL

```bash
curl -X PUT "http://localhost:8000/api/users/me/profile-picture" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "profile_picture": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD..."
  }'
```

⚠️ **NO usar query parameters** (causa error 431 con imágenes grandes):

## Seguridad

- ✅ Requiere autenticación JWT
- ✅ Solo el usuario autenticado puede actualizar su propia foto
- ✅ Validación de formato base64
- ✅ Almacenamiento encriptado en BD
- ⚠️ Sin rate limiting específico (usa rate limiting general de la API)

## Mostrar la Imagen en Frontend

### ⚠️ Problema: Base64 sin prefijo

El backend devuelve **base64 puro** (sin `data:image/...;base64,`) por eficiencia. El navegador necesita el prefijo completo para mostrar la imagen.

### Solución Recomendada: Pipe Angular

Crea una pipe reutilizable:

```typescript
// safe-image.pipe.ts
import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';

@Pipe({ name: 'safeImage' })
export class SafeImagePipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(base64: string | null | undefined, mimeType: string = 'image/jpeg'): SafeUrl | string {
    if (!base64) return 'assets/default-avatar.png';
    if (base64.startsWith('data:')) return this.sanitizer.bypassSecurityTrustUrl(base64);
    
    const dataUrl = `data:${mimeType};base64,${base64}`;
    return this.sanitizer.bypassSecurityTrustUrl(dataUrl);
  }
}
```

Uso en templates:

```html
<img [src]="user.profile_picture | safeImage" alt="Profile" />
```

### Alternativa: Método en Componente

```typescript
getProfilePictureUrl(base64: string | null | undefined): string {
  if (!base64) return 'assets/default-avatar.png';
  if (base64.startsWith('data:')) return base64;
  return `data:image/jpeg;base64,${base64}`;
}
```

```html
<img [src]="getProfilePictureUrl(user.profile_picture)" alt="Profile" />
```

Ver [FIX_PROFILE_PICTURE_431_ERROR.md](FIX_PROFILE_PICTURE_431_ERROR.md) para más detalles.
