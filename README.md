# claude-to-whatsapp

Bot de WhatsApp con integración a Claude AI CLI.

## Características

- Conexión a WhatsApp Web mediante [Neonize](https://github.com/Noclone-Project/neonize)
- Integración con Claude AI CLI
- Sistema de comandos (`BOTSET:`)
- Notificaciones periódicas de estado
- Persistencia de sesión de Claude
- Paquete Python instalable via pip

## Instalación

### Desde PyPI (futuro)

```bash
pip install claude-to-whatsapp
```

### En modo desarrollo (editable)

```bash
cd claude-to-whatsapp
pip install -e .
```

## Uso

### Preparar el directorio de trabajo

El bot lee archivos de configuración del directorio actual donde se ejecuta:

```
tu-directorio/
├── system_prompt.txt     # System prompt personalizado (opcional)
└── .claude/
    ├── agents/            # Definiciones de agentes (.md)
    └── skills/            # Definiciones de skills
```

### Ejecutar el bot

```bash
# Usando el entry point
claude-to-whatsapp

# O usando python -m
python -m claude_to_whatsapp
```

### Primera ejecución

1. Escanea el QR código que aparece en la terminal
2. Envía un mensaje a ti mismo en WhatsApp
3. El bot responderá usando Claude AI

## Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `BOTSET:reload` | Reinicia el bot |
| `BOTSET:logout` | Cierra la sesión de WhatsApp |
| `BOTSET:status` | Muestra el estado del bot |
| `BOTSET:help` | Muestra ayuda |

## Configuración

### System Prompt Personalizado

Crea un archivo `system_prompt.txt` en tu directorio de trabajo:

```text
Responde siempre en español. Formatea tus respuestas para WhatsApp...
```

### Agentes

Crea archivos `.md` en `.claude/agents/` con frontmatter YAML:

```yaml
---
name: python-explorer
description: Explorador de código Python
tools: Bash, Grep, Read
model: sonnet
---

# Instrucciones del agente...
```

### Skills

Skills se definen en `.claude/skills/*/` con archivos `SKILL.md`.

## Directorios de Datos

| Directorio | Ubicación | Contenido |
|-------------|------------|------------|
| Datos del bot | `~/.claude-to-whatsapp/` | `whatsapp_session.db`, `bot_data.db`, `whatsapp.log` |
| Recursos | Directorio actual | `system_prompt.txt`, `.claude/agents/`, `.claude/skills/` |

## Seguridad

El bot solo responde a mensajes enviados por ti mismo (self-messages). Esto garantiza que solo el dueño del número pueda interactuar con el bot.

## Arquitectura

```
claude-to-whatsapp/
├── src/claude_to_whatsapp/
│   ├── cli.py              # Entry point CLI
│   ├── config.py           # Configuración
│   ├── core/               # Lógica del bot
│   ├── integration/        # WhatsApp + Claude
│   ├── events/             # Manejo de eventos
│   ├── persistence/        # Base de datos
│   └── notifications/      # Notificaciones periódicas
├── tests/                 # Suite de pruebas
├── pyproject.toml         # Configuración del paquete
└── README.md              # Este archivo
```

## Desarrolladores

### Ejecutar tests

```bash
pip install -e ".[dev]"
pytest
```

### Linting y formatting

```bash
black src/
ruff check src/
```

## Licencia

MIT

## Autor

alejoair
