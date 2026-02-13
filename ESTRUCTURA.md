# Estructura del Proyecto `claude-to-whatsapp`

## Resumen

Bot que integra WhatsApp (via Neonize) con Claude AI CLI. Solo responde a mensajes propios por seguridad.

## Arquitectura

```
Directorio actual (recursos)
├── system_prompt.txt
└── .claude/agents/*.md

pyproject.toml                    # Configuración del paquete
whatsapp_bot.py                    # Versión monolítica (legacy)
src/claude_to_whatsapp/            # Paquete principal
└── ~/.claude-to-whatsapp/         # Datos del bot (runtime)
```

## Archivos del Paquete (`src/claude_to_whatsapp/`)

### Raíz

| Archivo | Propósito |
|---------|-----------|
| `__init__.py` | Exportaciones públicas y versión |
| `__version__.py` | Versión del paquete (0.1.0) |
| `__main__.py` | Entry point para `python -m` |
| `cli.py` | Entry point CLI (`main()`) |
| `config.py` | Configuración central (dataclasses) |
| `logging_config.py` | Setup de logging |
| `exceptions.py` | Excepciones custom |

### `core/`

| Archivo | Contenido | Propósito |
|---------|----------|-----------|
| `bot.py` | `WhatsAppBot` | Orquestador principal, maneja eventos y coordina componentes |
| `models.py` | `ClaudeRequest`, `ClaudeResponse` | Models para comunicación con Claude |
| `commands.py` | `CommandRegistry`, comandos | Sistema de comandos `BOTSET:` (reload, logout, status, help) |

### `integration/`

| Archivo | Contenido | Propósito |
|---------|----------|-----------|
| `base.py` | `MessageClient`, `AIModelClient` (ABC) | Interfaces base |
| `whatsapp.py` | `WhatsAppClient` | Wrapper de Neonize (connect, send_message, register_handler) |
| `claude.py` | `ClaudeClient` | Wrapper de Claude CLI via PowerShell |

### `events/`

| Archivo | Contenido | Propósito |
|---------|----------|-----------|
| `filters.py` | `MessageFilter` | Filtros: `is_self_message()`, `is_system_message()`, `is_bot_command()`, `extract_text()` |

### `persistence/`

| Archivo | Contenido | Propósito |
|---------|----------|-----------|
| `repositories.py` | `BotConfigRepository` | SQLite para persistir session_id, my_number, my_jid |

### `notifications/`

| Archivo | Contenido | Propósito |
|---------|----------|-----------|
| `thread.py` | `NotificationThread` | Thread que envía notificaciones de tiempo cada 30s |

## Flujo de Datos

```
WhatsApp Message → Neonize → MessageFilter.is_self_message() →
  ├─ Comando BOTSET:? → CommandRegistry.execute()
  └─ Pregunta → ClaudeClient.ask() (via PowerShell) → Respuesta → WhatsApp
```

## Entradas/Salidas

| Recurso | Ubicación |
|---------|-----------|
| `whatsapp_session.db` | `~/.claude-to-whatsapp/` |
| `bot_data.db` | `~/.claude-to-whatsapp/` |
| `whatsapp.log` | `~/.claude-to-whatsapp/` |
| `system_prompt.txt` | Directorio actual |
| `.claude/agents/*.md` | Directorio actual |
