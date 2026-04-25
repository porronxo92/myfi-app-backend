# Integración Frontend — Agente Conversacional (Chat)

> **Fecha:** 2026-04-01
> **Backend endpoint:** `POST /api/insights/chat`
> **Auth:** Bearer token (obligatorio)

---

## 1. Resumen

El backend ahora expone un endpoint de chat mejorado que permite:
- Conversaciones en lenguaje natural sobre finanzas
- Historial de conversación (mantenido por el frontend)
- Acciones propuestas (crear transacción, crear categoría) con confirmación

---

## 2. Contrato de API

### 2.1 Request

```typescript
interface ChatRequest {
  message: string;                    // Mensaje actual del usuario (1-2000 chars)
  conversation_history: ChatMessage[]; // Historial previo (max 50 mensajes)
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}
```

**Ejemplo:**
```json
POST /api/insights/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "¿Cuánto he gastado este mes en supermercado?",
  "conversation_history": [
    { "role": "user", "content": "Hola" },
    { "role": "assistant", "content": "¡Hola! Soy MyFi, tu asistente financiero..." }
  ]
}
```

### 2.2 Response

```typescript
interface ChatResponse {
  message: string;                      // Respuesta textual del agente
  proposed_action: ProposedAction | null; // Acción propuesta (requiere confirmación)
  suggested_questions: string[];        // Preguntas sugeridas (max 3)
  timestamp: string;                    // ISO timestamp
}

interface ProposedAction {
  type: 'create_transaction' | 'create_category';
  description: string;    // Texto legible para mostrar en modal de confirmación
  endpoint: string;       // Endpoint a llamar si usuario confirma (ej: "POST /api/transactions")
  data: object;           // Payload listo para enviar al endpoint
}
```

**Ejemplo respuesta informativa:**
```json
{
  "message": "Este mes has gastado 234,50€ en Supermercado, un 15% más que el mes pasado.",
  "proposed_action": null,
  "suggested_questions": [
    "¿Cuáles son mis categorías de mayor gasto?",
    "¿Cuánto me queda de presupuesto en alimentación?",
    "¿Cómo evoluciona mi gasto en supermercado?"
  ],
  "timestamp": "2026-04-01T10:30:00.000000"
}
```

**Ejemplo respuesta con acción:**
```json
{
  "message": "Entendido. Voy a registrar el gasto. Por favor confirma antes de guardarlo.",
  "proposed_action": {
    "type": "create_transaction",
    "description": "Crear gasto de -45,00€ - Mercadona (categoría: Supermercado)",
    "endpoint": "POST /api/transactions",
    "data": {
      "account_id": "550e8400-e29b-41d4-a716-446655440000",
      "amount": -45.00,
      "date": "2026-04-01",
      "description": "Mercadona",
      "type": "expense",
      "category_id": "7f3d2c1b-a890-4567-bcde-123456789abc",
      "source": "chat_agent"
    }
  },
  "suggested_questions": [],
  "timestamp": "2026-04-01T10:30:00.000000"
}
```

---

## 3. Código de integración Angular

### 3.1 Interfaces (chat.models.ts)

```typescript
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ProposedAction {
  type: 'create_transaction' | 'create_category';
  description: string;
  endpoint: string;
  data: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  conversation_history: ChatMessage[];
}

export interface ChatResponse {
  message: string;
  proposed_action: ProposedAction | null;
  suggested_questions: string[];
  timestamp: string;
}
```

### 3.2 Servicio (chat.service.ts)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@env/environment';
import { ChatRequest, ChatResponse, ProposedAction } from './chat.models';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly apiUrl = `${environment.apiUrl}/insights/chat`;

  constructor(private http: HttpClient) {}

  sendMessage(request: ChatRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(this.apiUrl, request);
  }

  executeAction(action: ProposedAction): Observable<any> {
    // Extraer método y URL del endpoint string
    const [method, path] = action.endpoint.split(' ');
    const url = `${environment.apiUrl}${path.replace('/api', '')}`;

    if (method === 'POST') {
      return this.http.post(url, action.data);
    } else if (method === 'PUT') {
      return this.http.put(url, action.data);
    }

    throw new Error(`Método no soportado: ${method}`);
  }
}
```

### 3.3 Componente (chat.component.ts)

```typescript
import { Component, OnInit } from '@angular/core';
import { ChatService } from './chat.service';
import { ChatMessage, ChatResponse, ProposedAction } from './chat.models';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmDialogComponent } from '@shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss']
})
export class ChatComponent implements OnInit {
  messages: ChatMessage[] = [];
  inputMessage = '';
  isLoading = false;
  suggestedQuestions: string[] = [];

  constructor(
    private chatService: ChatService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    // Mensaje de bienvenida inicial (opcional, local)
    this.messages.push({
      role: 'assistant',
      content: '¡Hola! Soy MyFi, tu asistente financiero. ¿En qué puedo ayudarte?'
    });
  }

  async sendMessage(): Promise<void> {
    if (!this.inputMessage.trim() || this.isLoading) return;

    const userMessage = this.inputMessage.trim();
    this.inputMessage = '';
    this.isLoading = true;

    // Añadir mensaje del usuario al historial local
    this.messages.push({ role: 'user', content: userMessage });

    try {
      // Preparar historial (excluir el mensaje que acabamos de añadir)
      const history = this.messages.slice(0, -1);

      const response = await this.chatService.sendMessage({
        message: userMessage,
        conversation_history: history
      }).toPromise();

      // Añadir respuesta del agente
      this.messages.push({ role: 'assistant', content: response.message });

      // Actualizar preguntas sugeridas
      this.suggestedQuestions = response.suggested_questions || [];

      // Si hay acción propuesta, mostrar confirmación
      if (response.proposed_action) {
        await this.handleProposedAction(response.proposed_action);
      }

    } catch (error: any) {
      this.handleError(error);
    } finally {
      this.isLoading = false;
    }
  }

  private async handleProposedAction(action: ProposedAction): Promise<void> {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Confirmar acción',
        message: action.description,
        confirmText: 'Confirmar',
        cancelText: 'Cancelar'
      }
    });

    const confirmed = await dialogRef.afterClosed().toPromise();

    if (confirmed) {
      try {
        await this.chatService.executeAction(action).toPromise();

        // Añadir confirmación al historial
        this.messages.push({
          role: 'user',
          content: `[Confirmado: ${action.description}]`
        });
        this.messages.push({
          role: 'assistant',
          content: '✅ Acción ejecutada correctamente.'
        });

      } catch (error) {
        this.messages.push({
          role: 'assistant',
          content: '❌ Error al ejecutar la acción. Por favor, inténtalo de nuevo.'
        });
      }
    } else {
      this.messages.push({
        role: 'assistant',
        content: 'Entendido, no se ha realizado ninguna acción.'
      });
    }
  }

  private handleError(error: any): void {
    let errorMessage = 'Ha ocurrido un error. Por favor, inténtalo de nuevo.';

    // Manejar error de quota (429)
    if (error.status === 429 && error.error?.detail?.limit) {
      const detail = error.error.detail;
      errorMessage = `Has usado ${detail.used}/${detail.limit} consultas hoy. ` +
                     `Tu cuota se restablecerá mañana.`;
    }

    this.messages.push({ role: 'assistant', content: errorMessage });
  }

  onSuggestedQuestionClick(question: string): void {
    this.inputMessage = question;
    this.sendMessage();
  }

  clearChat(): void {
    this.messages = [{
      role: 'assistant',
      content: '¡Hola! Soy MyFi, tu asistente financiero. ¿En qué puedo ayudarte?'
    }];
    this.suggestedQuestions = [];
  }
}
```

### 3.4 Template (chat.component.html)

```html
<div class="chat-container">
  <!-- Header -->
  <div class="chat-header">
    <h3>💬 MyFi Assistant</h3>
    <button mat-icon-button (click)="clearChat()" matTooltip="Nueva conversación">
      <mat-icon>refresh</mat-icon>
    </button>
  </div>

  <!-- Messages -->
  <div class="chat-messages" #messagesContainer>
    <div *ngFor="let msg of messages"
         class="message"
         [class.user]="msg.role === 'user'"
         [class.assistant]="msg.role === 'assistant'">
      <div class="message-content">{{ msg.content }}</div>
    </div>

    <div *ngIf="isLoading" class="message assistant loading">
      <div class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    </div>
  </div>

  <!-- Suggested questions -->
  <div class="suggested-questions" *ngIf="suggestedQuestions.length > 0">
    <button mat-stroked-button
            *ngFor="let q of suggestedQuestions"
            (click)="onSuggestedQuestionClick(q)">
      {{ q }}
    </button>
  </div>

  <!-- Input -->
  <div class="chat-input">
    <mat-form-field appearance="outline" class="full-width">
      <input matInput
             [(ngModel)]="inputMessage"
             placeholder="Escribe tu mensaje..."
             (keyup.enter)="sendMessage()"
             [disabled]="isLoading">
    </mat-form-field>
    <button mat-fab color="primary"
            (click)="sendMessage()"
            [disabled]="isLoading || !inputMessage.trim()">
      <mat-icon>send</mat-icon>
    </button>
  </div>
</div>
```

---

## 4. Manejo de errores

### 4.1 Error de quota (HTTP 429)

```json
{
  "detail": {
    "message": "Has alcanzado tu límite diario de 20 consultas a Gemini AI.",
    "used": 20,
    "limit": 20,
    "reset_date": "2026-04-02"
  }
}
```

**Manejo en interceptor:**
```typescript
if (error.status === 429 && error.error?.detail?.limit) {
  const d = error.error.detail;
  this.toastr.warning(
    `Has usado ${d.used}/${d.limit} consultas. Disponible mañana.`,
    'Límite de IA alcanzado'
  );
}
```

### 4.2 Otros errores (500, etc.)
```typescript
if (error.status === 500) {
  this.toastr.error('Error del servidor. Inténtalo más tarde.', 'Error');
}
```

---

## 5. Consideraciones de UX

| Aspecto | Comportamiento |
|---------|----------------|
| **Historial** | Se mantiene en memoria del componente, se pierde al recargar |
| **Loading** | Mostrar indicador de typing mientras espera respuesta |
| **Confirmación** | Modal antes de ejecutar cualquier acción |
| **Preguntas sugeridas** | Mostrar como chips/botones clickables |
| **Scroll** | Auto-scroll al último mensaje cuando llega respuesta |
| **Límite caracteres** | Input máximo 2000 caracteres |

---

## 6. Diagrama de flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                      USUARIO ENVÍA MENSAJE                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Frontend: añade mensaje a historial local + muestra loading    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  POST /api/insights/chat                                        │
│  { message, conversation_history }                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend: carga contexto financiero + llama a Gemini           │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌──────────────────────────┐      ┌──────────────────────────────┐
│  proposed_action = null  │      │  proposed_action != null     │
│  (solo informativo)      │      │  (requiere confirmación)     │
└──────────────────────────┘      └──────────────────────────────┘
                │                               │
                ▼                               ▼
┌──────────────────────────┐      ┌──────────────────────────────┐
│  Mostrar mensaje +       │      │  Mostrar mensaje +           │
│  preguntas sugeridas     │      │  MODAL DE CONFIRMACIÓN       │
└──────────────────────────┘      └──────────────────────────────┘
                                                │
                                  ┌─────────────┴─────────────┐
                                  ▼                           ▼
                         ┌──────────────┐            ┌──────────────┐
                         │  CONFIRMA    │            │  CANCELA     │
                         └──────────────┘            └──────────────┘
                                  │                           │
                                  ▼                           ▼
                         ┌────────────────────┐      ┌──────────────────┐
                         │ POST /api/...      │      │ "No se realizó   │
                         │ (transactions,     │      │  ninguna acción" │
                         │  categories)       │      └──────────────────┘
                         └────────────────────┘
                                  │
                                  ▼
                         ┌────────────────────┐
                         │ "✅ Acción         │
                         │  ejecutada"        │
                         └────────────────────┘
```

---

## 7. Endpoint consulta de quota (opcional)

Si quieres mostrar la quota restante en la UI:

```typescript
// GET /api/users/me/gemini-quota
interface GeminiQuota {
  used: number;
  remaining: number;
  limit: number;
  reset_date: string;
  percentage_used: number;
}
```

---

## 8. Checklist de implementación

- [ ] Crear interfaces TypeScript (`chat.models.ts`)
- [ ] Crear servicio (`chat.service.ts`)
- [ ] Crear componente chat con template
- [ ] Añadir estilos CSS/SCSS
- [ ] Implementar modal de confirmación
- [ ] Manejar error 429 en interceptor
- [ ] Añadir botón toggle para abrir/cerrar chat
- [ ] Testing manual de flujos principales
