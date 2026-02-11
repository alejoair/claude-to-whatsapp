# Estructura del Bot WhatsApp + Claude CLI

## Resumen Arquitectónico

```
WhatsApp Message → Neonize Client → Message Handler → Claude CLI (PowerShell) → Response → WhatsApp
                                          ↓
                                  Session Management (SQLite)
                                  Notifications (thread periódico)
```

## Clase Principal: `WhatsAppBot`

### Atributos del `__init__`

| Atributo | Tipo | Propósito |
|-----------|------|-----------|
| `client` | `NewClient` | Cliente de WhatsApp (Neonize) |
| `my_number` | `str` | Número del usuario (para seguridad) |
| `my_jid` | `str` | JID completo del usuario |
| `pending_requests` | `dict` | Solicitudes activas: `{chat_key: {start_time, prompt, chat, client}}` |
| `_notification_thread` | `Thread` | Thread de notificaciones periódicas |
| `_notification_running` | `bool` | Flag del thread de notificaciones |
| `_notification_lock` | `Lock` | Lock para thread-safe operations |
| `system_prompt` | `str` | System prompt personalizado |
| `agents_dir` | `str` | Directorio de agentes `.claude/agents/` |

---

## Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────────────┐
│                        whatsapp_bot.py                        │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  1. CONFIGURACIÓN                                     │
│  - Crear directorios de configuración                  │
│  - Configurar logging                                       │
│  - Inicializar DB del bot                                  │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. INIT (__init__)                                     │
│  - Cargar my_number, my_jid guardados                   │
│  - Verificar flag de reinicio                             │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. RUN()                                                │
│  - Crear cliente Neonize                                    │
│  - Registrar eventos (ConnectedEv, PairStatusEv, MessageEv)        │
│  - Iniciar thread de conexión                                │
│  - Iniciar thread de notificaciones                         │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. MENSAJE RECIBIDO (on_message)                      │
│  - Verificar IsFromMe y sender==chat                    │
│  - Ignorar BOTSYS:                                        │
│  - Procesar comandos BOTSET:                            │
│  - Invocar ask_claude_async()                             │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. ASK_CLAUDE_ASYNC (Thread separado)                  │
│  - Registrar en pending_requests                              │
│  - Llamar ask_claude()                                    │
│  - Guardar session_id si cambió                           │
│  - Enviar respuesta a WhatsApp                                 │
│  - Limpiar pending_requests (finally)                        │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  6. ASK_CLAUDE + _EXECUTE_CLAUDE_COMMAND                 │
│  - Cargar system_prompt.txt                                   │
│  - Cargar agentes (.md con frontmatter YAML)                 │
│  - Crear archivo temporal de agentes                       │
│  - Ejecutar comando Claude CLI (PowerShell)                  │
│  - Manejar reintentos de sesión inválida                  │
│  - Parsear respuesta JSON                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Eventos de Neonize

| Evento | Método | Cuándo se dispara |
|---------|---------|------------------|
| `ConnectedEv` | `on_connected()` | Bot conecta a WhatsApp |
| `PairStatusEv` | `on_pair_status()` | Primer emparejamiento (QR) |
| `HistorySyncEv` | `on_history_sync()` | Sincronización de historial |
| `MessageEv` | `on_message()` | Mensaje recibido |

---

## Filtros de Seguridad

### Self-Message Filter
```python
is_self_message = is_from_me and (sender_str == chat_str)
```

Solo responde a mensajes donde:
- El mensaje es del propio usuario (`IsFromMe == True`)
- El remitente es igual al chat (`sender == chat`)

### Ignorar Mensajes del Sistema
```python
if text.startswith("BOTSYS:"):
    return  # Ignorar para evitar bucles
```

---

## Comandos del Bot (BOTSET:)

| Comando | Acción |
|---------|---------|
| `reload` | Reinicia el bot con notificación |
| `logout` | Cierra sesión WhatsApp y elimina credenciales |
| `status` | Muestra estado del bot |
| `help` | Lista comandos disponibles |

---

## Base de Datos (SQLite)

### Ubicación
```
~/.claude-to-whatsapp/
├── whatsapp_session.db    # Sesión de WhatsApp (Neonize)
└── bot_data.db           # Datos del bot
```

### Tabla `bot_config`
```
bot_config
├── key (PRIMARY KEY)
└── value
```

### Keys guardados
- `my_jid` - JID completo del usuario
- `my_number` - Número del usuario
- `claude_session_id` - Session ID de Claude CLI

---

## Sistema de Agentes

### Directorio
```
.claude/agents/
├── agent-builder.md
├── code-reviewer.md
└── python-explorer.md
```

### Formato de Agente (.md)
```yaml
---
name: nombre-del-agente
description: Breve descripción
tools: Bash, Read, Grep, Glob
skills: skill1, skill2  # Opcional
model: sonnet  # sonnet, haiku, opus
---

# Instrucciones del agente...
```

---

## Sistema de Skills

### Directorio
```
.claude/skills/
└── test-execution/
    ├── SKILL.md
    └── scripts/
        └── create_test_file.py
```

### Formato de Skill (.md)
```yaml
---
name: nombre-skill
description: Qué hace y cuándo usarla
allowed-tools: Bash(python *)
---

# Instrucciones de la skill...
```

---

## Notificaciones Periódicas

### Thread de Notificaciones
- Ejecuta cada **30 segundos**
- Envía mensajes `BOTSYS:⏳ Tiempo transcurrido: Xs`
- Solo para solicitudes activas en `pending_requests`

### Formato de Notificación
```
BOTSYS:⏳ Tiempo transcurrido: 1m 30s
```

---

## Prefijos de Mensajes

| Prefijo | Uso |
|---------|------|
| `BOT_PREFIX` | Respuestas de Claude |
| `SYS_PREFIX` | Mensajes del sistema (BOTSYS) - *NO USADO* |

```
BOT_PREFIX = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
SYS_PREFIX = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
```

---

## Configuración

### Archivos de Configuración
```
system_prompt.txt     # System prompt personalizado (opcional)
.reload_flag         # Flag de reinicio temporal
```

### Logs
```
~/.claude-to-whatsapp/whatsapp.log
```

---

## Comando Claude CLI (PowerShell)

### Construcción del Comando
```python
base_cmd = "claude"

# Con system prompt
if system_prompt:
    base_cmd += f' --append-system-prompt "{escaped_prompt}"'

# Con agentes (archivo temporal)
if agents_json:
    base_cmd += f' --agents @{temp_agents_file}'

# Con session_id existente
if session_id:
    ps_script = f'{base_cmd} -r "{session_id}" "{prompt}" --output-format json --dangerously-skip-permissions'
else:
    ps_script = f'{base_cmd} -p "{prompt}" --output-format json --dangerously-skip-permissions'

# Ejecutar
subprocess.run(["powershell", "-Command", ps_script], ...)
```

---

## Manejo de Errores

### Session ID Inválido
```python
if "No conversation found" in stderr:
    return None, None  # Reintentar sin session_id
```

### Timeout
```python
except subprocess.TimeoutExpired:
    return "Lo siento, tardé demasiado en responder. Intenta de nuevo.", None
```

### JSON Parse Error
```python
except json.JSONDecodeError:
    if "No conversation found" in stderr:
        return None, None  # Reintentar
```

---

## Funciones Clave

| Función | Propósito | Retorna |
|----------|-------------|----------|
| `ask_claude()` | Ejecuta comando Claude con reintentos | `(response, session_id)` |
| `_execute_claude_command()` | Ejecuta comando CLI real | `(response, session_id)` |
| `ask_claude_async()` | Wrapper con threading y envío a WA | `None` |
| `_load_agents()` | Parsear archivos .md de agentes | `json` o `None` |
| `save_session_id()` | Guardar session en DB | `None` |
| `load_session_id()` | Cargar session desde DB | `session_id` o `None` |
| `_load_system_prompt()` | Cargar system_prompt.txt | `None` |
| `process_bot_command()` | Manejar comandos BOTSET: | `bool` |

---

## Flujo de Reintentos (Session ID)

```
ask_claude(prompt, session_id)
    │
    ▼ (primer intento)
    _execute_claude_command(prompt, session_id)
    │
    ├─ SUCCESS → return (result, new_session_id)
    │
    └─ FAIL (session inválido)
        │
        ▼ (segundo intento)
        _execute_claude_command(prompt, None)  # Sin session_id
        │
        └─ return (result, new_session_id)
```

---

## Archivos Clave

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `whatsapp_bot.py` | ~840 | Bot principal |
| `system_prompt.txt` | ~360 | System prompt personalizado |
| `.claude/agents/*.md` | ~360 | Definiciones de agentes |
| `.claude/skills/*/SKILL.md` | ~25 | Definiciones de skills |
| `.claude/skills/*/scripts/*.py` | ~40 | Scripts ejecutables |
