# Fix: Error 431 al subir foto de perfil

**Fecha:** 2026-03-01  
**Error:** `431 Request Header Fields Too Large`  
**Causa:** Envío de imagen base64 en query parameter (URL)

## Problema

Al intentar actualizar la foto de perfil desde el frontend, se produce el error:

```
Failed to load resource: the server responded with a status of 431 (Request Header Fields Too Large)
```

### Causa Raíz

El frontend Angular estaba enviando la imagen base64 como **query parameter en la URL**:

```typescript
// ❌ INCORRECTO - Causa error 431
const url = `${apiUrl}/users/me/profile-picture?profile_picture_url=${imageBase64}`;
this.http.put(url, {}).subscribe(...);
```

**¿Por qué falla?**
- Las URLs tienen límites de tamaño (~2-8 KB dependiendo del servidor)
- Una imagen en base64 puede ser 50 KB - 500 KB o más
- Los headers HTTP que incluyen la URL exceden el límite → Error 431

## Solución

Enviar la imagen en el **body JSON** en lugar de query parameter.

### Backend (Ya corregido)

El endpoint ahora **solo acepta** body JSON:

```python
@router.put("/me/profile-picture", response_model=UserResponse)
async def update_profile_picture(
    picture_data: ProfilePictureUpdate = Body(...),  # Body requerido
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: bool = Depends(check_rate_limit)
):
    """
    ⚠️ IMPORTANTE: La imagen debe enviarse en el body JSON, 
    NO en query parameters (causa error 431)
    """
```

### Frontend Angular - Cambio Necesario

#### ❌ Antes (Incorrecto):

```typescript
// user.service.ts
updateProfilePicture(imageBase64: string): Observable<User> {
  // ❌ Envía en la URL - CAUSA ERROR 431
  const url = `${this.apiUrl}/users/me/profile-picture?profile_picture_url=${imageBase64}`;
  
  return this.http.put<User>(url, {}, {
    headers: { 'Authorization': `Bearer ${this.getToken()}` }
  });
}
```

#### ✅ Después (Correcto):

```typescript
// user.service.ts
updateProfilePicture(imageBase64: string): Observable<User> {
  // ✅ Envía en el body JSON - FUNCIONA CORRECTAMENTE
  const url = `${this.apiUrl}/users/me/profile-picture`;
  
  return this.http.put<User>(url, {
    profile_picture: imageBase64  // ← Imagen en el body
  }, {
    headers: {
      'Authorization': `Bearer ${this.getToken()}`,
      'Content-Type': 'application/json'
    }
  });
}
```

### Componente (sin cambios)

El componente que llama al servicio **no necesita cambios**:

```typescript
// profile.component.ts
onFileSelected(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    const base64String = reader.result as string;
    
    // Esta llamada funciona igual, solo cambia el servicio internamente
    this.userService.updateProfilePicture(base64String).subscribe({
      next: (user) => {
        console.log('✅ Foto actualizada', user);
        this.currentUser = user;
      },
      error: (err) => {
        console.error('❌ Error', err);
      }
    });
  };
  
  reader.readAsDataURL(file);
}
```

## Formato de Request

### Headers
```
PUT /api/users/me/profile-picture
Authorization: Bearer <token>
Content-Type: application/json
```

### Body JSON
```json
{
  "profile_picture": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD..."
}
```

El backend:
1. ✅ Acepta data URL completa (`data:image/jpeg;base64,...`)
2. ✅ Acepta base64 puro (sin prefijo `data:`)
3. ✅ Extrae automáticamente el base64 de data URLs
4. ✅ Valida que sea base64 válido
5. ✅ Almacena encriptado en la columna `profile_picture`

## Prueba con cURL

```bash
curl -X PUT "http://localhost:8000/api/users/me/profile-picture" \
  -H "Authorization: Bearer <tu_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_picture": "data:image/jpeg;base64,/9j/4AAQ..."
  }'
```

## Validación

Después del cambio en Angular, verifica:

1. ✅ No debe aparecer error 431
2. ✅ La imagen se sube correctamente
3. ✅ La respuesta incluye el usuario actualizado con `profile_picture`
4. ✅ Los logs del backend muestran: `"Imagen recibida via body JSON"`

## ⚠️ IMPORTANTE: Mostrar la imagen en el Frontend

### Problema: El backend devuelve base64 puro (sin prefijo)

El backend **almacena y devuelve solo el base64 puro** para eficiencia:

```json
{
  "profile_picture": "/9j/4AAQSkZJRgABAQEAYABgAAD..."  // ← Sin prefijo data:image
}
```

Pero el navegador necesita el prefijo completo para mostrar la imagen:

```html
<!-- ❌ NO FUNCIONA - El navegador intenta cargar como URL -->
<img [src]="user.profile_picture" />

<!-- ✅ FUNCIONA - Con prefijo data URL -->
<img [src]="'data:image/jpeg;base64,' + user.profile_picture" />
```

### Solución 1: Pipe Angular (Recomendado)

Crea una pipe reutilizable para manejar las imágenes:

```typescript
// safe-image.pipe.ts
import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';

@Pipe({
  name: 'safeImage'
})
export class SafeImagePipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(base64: string | null | undefined, mimeType: string = 'image/jpeg'): SafeUrl | string {
    if (!base64) {
      return 'assets/default-avatar.png'; // Imagen por defecto
    }

    // Si ya tiene el prefijo data:, devolverlo directamente
    if (base64.startsWith('data:')) {
      return this.sanitizer.bypassSecurityTrustUrl(base64);
    }

    // Agregar prefijo data URL
    const dataUrl = `data:${mimeType};base64,${base64}`;
    return this.sanitizer.bypassSecurityTrustUrl(dataUrl);
  }
}
```

Registrar en el módulo:

```typescript
// app.module.ts o shared.module.ts
import { SafeImagePipe } from './pipes/safe-image.pipe';

@NgModule({
  declarations: [
    SafeImagePipe,
    // ... otros componentes
  ],
  exports: [SafeImagePipe] // Exportar si es shared module
})
export class SharedModule { }
```

Usar en templates:

```html
<!-- Uso básico -->
<img [src]="user.profile_picture | safeImage" alt="Profile" />

<!-- Con tipo MIME específico -->
<img [src]="user.profile_picture | safeImage:'image/png'" alt="Profile" />

<!-- Con fallback automático a imagen por defecto -->
<img [src]="user.profile_picture | safeImage" 
     class="rounded-full w-32 h-32" 
     alt="Profile" />
```

### Solución 2: Método en el Componente

Si no quieres crear una pipe:

```typescript
// profile.component.ts
export class ProfileComponent {
  user: User;

  getProfilePictureUrl(base64: string | null | undefined): string {
    if (!base64) {
      return 'assets/default-avatar.png';
    }

    // Si ya tiene el prefijo, devolverlo
    if (base64.startsWith('data:')) {
      return base64;
    }

    // Agregar prefijo
    return `data:image/jpeg;base64,${base64}`;
  }
}
```

Usar en template:

```html
<img [src]="getProfilePictureUrl(user.profile_picture)" alt="Profile" />
```

### Solución 3: Transformar en el Servicio

Agregar el prefijo automáticamente cuando se recibe el usuario:

```typescript
// user.service.ts
export class UserService {
  private addDataUrlPrefix(user: User): User {
    if (user.profile_picture && !user.profile_picture.startsWith('data:')) {
      user.profile_picture = `data:image/jpeg;base64,${user.profile_picture}`;
    }
    return user;
  }

  updateProfilePicture(imageBase64: string): Observable<User> {
    const url = `${this.apiUrl}/users/me/profile-picture`;
    
    return this.http.put<User>(url, {
      profile_picture: imageBase64
    }).pipe(
      map(user => this.addDataUrlPrefix(user)) // ← Transformar respuesta
    );
  }

  getCurrentUser(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/users/me`).pipe(
      map(user => this.addDataUrlPrefix(user))
    );
  }
}
```

Con esta solución, en el template funciona directamente:

```html
<img [src]="user.profile_picture" alt="Profile" />
```

### Comparación de Soluciones

| Solución | Ventajas | Desventajas |
|----------|----------|-------------|
| **Pipe** | ✅ Reutilizable<br>✅ Limpio en templates<br>✅ Maneja nulls<br>✅ Sanitización incluida | Requiere crear pipe |
| **Método** | ✅ Sin dependencias extras<br>✅ Fácil de implementar | ❌ Repetir en cada componente |
| **Servicio** | ✅ Centralizado<br>✅ Transparente para componentes | ❌ Modifica datos<br>❌ Requiere aplicar en todos los endpoints |

**Recomendación:** Usa la **Pipe** para máxima reutilización y limpieza de código.

## Límites Recomendados

Aunque el endpoint no tiene límite específico, considera:

- **Máximo recomendado:** 2-3 MB por imagen
- **Óptimo:** 200-500 KB
- **Best practice:** Redimensionar/comprimir imágenes en el frontend antes de enviar

### Ejemplo de compresión en Angular:

```typescript
import { NgxImageCompressService } from 'ngx-image-compress';

constructor(private imageCompress: NgxImageCompressService) {}

async compressAndUpload(file: File): Promise<void> {
  const reader = new FileReader();
  
  reader.onload = async () => {
    const imageDataUrl = reader.result as string;
    
    // Comprimir imagen (calidad 75%, máx 1024px)
    const compressedImage = await this.imageCompress.compressFile(
      imageDataUrl,
      -1,  // orientación
      75,  // calidad (0-100)
      75,  // calidad
      1024, // maxWidth
      1024  // maxHeight
    );
    
    // Subir imagen comprimida
    this.userService.updateProfilePicture(compressedImage).subscribe(...);
  };
  
  reader.readAsDataURL(file);
}
```

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `app/routes/users.py` | Eliminar soporte de query parameter, solo body JSON |
| `app/schemas/user.py` | `ProfilePictureUpdate` schema (sin cambios) |
| `docs/PROFILE_PICTURE_API.md` | Actualizar documentación con advertencia error 431 |

## Referencias

- [RFC 7231 - HTTP Status Code 431](https://datatracker.ietf.org/doc/html/rfc6585#section-5)
- [MDN: 431 Request Header Fields Too Large](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/431)
