#!/usr/bin/env python3
"""WhatsApp Bot con Neonize + Claude CLI Integration"""

import logging
import os
import sys
import subprocess
import json
import sqlite3

# Crear directorio de configuración
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".claude-to-whatsapp")
os.makedirs(CONFIG_DIR, exist_ok=True)

# Configurar logging - reducir verbosity de Neonize
logging.basicConfig(
    level=logging.WARNING,  # Cambiado a WARNING para reducir ruido
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(CONFIG_DIR, 'whatsapp.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Nuestro logger usa INFO

# Importar Neonize
from neonize.client import NewClient
from neonize.events import ConnectedEv, PairStatusEv, MessageEv, HistorySyncEv

# Configuración
DB_PATH = os.path.join(CONFIG_DIR, "whatsapp_session.db")
SESSIONS_FILE = os.path.join(CONFIG_DIR, "claude_sessions.json")
client = None
MY_NUMBER = None  # Se guardará el número propio cuando se conecte


def optimize_sqlite():
    """
    Optimiza la base de datos SQLite para reducir problemas de locking
    Activa WAL mode y aumenta el timeout
    """
    if not os.path.exists(DB_PATH):
        # Si no existe, Neonize la creará, no podemos optimizarla aún
        return

    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Activar WAL mode (permite lecturas simultáneas con escrituras)
        cursor.execute("PRAGMA journal_mode=WAL;")
        wal_mode = cursor.fetchone()
        logger.info(f"📊 SQLite WAL mode: {wal_mode[0]}")

        # Aumentar busy timeout a 30 segundos
        cursor.execute("PRAGMA busy_timeout=30000;")

        # Optimizaciones adicionales
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA cache_size=-10000;")  # 10MB cache
        cursor.execute("PRAGMA temp_store=MEMORY;")

        conn.commit()
        conn.close()
        logger.info("✅ Base de datos SQLite optimizada")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo optimizar SQLite: {e}")


def load_sessions():
    """Carga los session IDs de Claude desde archivo"""
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_sessions(sessions):
    """Guarda los session IDs de Claude en archivo"""
    try:
        with open(SESSIONS_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        logger.error(f"Error guardando sesiones: {e}")


def ask_claude(prompt, session_id=None):
    """
    Envía un prompt a Claude usando el CLI y devuelve la respuesta y session_id

    Args:
        prompt: El prompt para enviar a Claude
        session_id: El session_id para continuar una conversación (opcional)

    Returns:
        tuple: (response_text, session_id)
    """
    try:
        # Construir comando para PowerShell
        if session_id:
            ps_script = f'claude -r "{session_id}" "{prompt}" --output-format json --dangerously-skip-permissions'
        else:
            ps_script = f'claude -p "{prompt}" --output-format json --dangerously-skip-permissions'

        logger.info(f"🤖 Enviando a Claude: {prompt[:50]}...")

        # Ejecutar comando usando PowerShell
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )

        # Parsear respuesta JSON
        response = json.loads(result.stdout)

        # Extraer respuesta y session_id
        response_text = response.get('result', '')
        new_session_id = response.get('session_id', '')

        return response_text, new_session_id

    except subprocess.TimeoutExpired:
        logger.error("⏱️ Timeout esperando respuesta de Claude")
        return "Lo siento, tardé demasiado en responder. Intenta de nuevo.", session_id
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parseando JSON de Claude: {e}")
        logger.error(f"Output: {result.stdout[:500]}")
        return "Hubo un error procesando la respuesta de Claude.", session_id
    except Exception as e:
        logger.error(f"❌ Error comunicando con Claude: {e}")
        return "Hubo un error al comunicarme con Claude.", session_id


def on_connected(client: NewClient, _: ConnectedEv):
    """Evento cuando se conecta a WhatsApp"""
    logger.info("⚡ ¡Conectado a WhatsApp!")


def on_pair_status(_: NewClient, message: PairStatusEv):
    """Evento cuando se completa el emparejamiento"""
    global MY_NUMBER
    MY_NUMBER = str(message.ID.User)
    logger.info(f"✅ Sesión guardada exitosamente")
    logger.info(f"📱 Tu número: {MY_NUMBER}")
    logger.info(f"💾 Credenciales guardadas en: {DB_PATH}")
    logger.info(f"🔒 Solo responderás a mensajes de tu propio número")


def on_history_sync(client: NewClient, history: HistorySyncEv):
    """Evento cuando se sincroniza el historial"""
    # Silencioso - no loggear para reducir ruido
    pass


def on_message(client: NewClient, message: MessageEv):
    """Evento cuando se recibe un mensaje"""
    try:
        # Obtener información del mensaje - mantener como objeto JID
        chat = message.Info.MessageSource.Chat
        sender = str(message.Info.MessageSource.Sender)

        # Verificar que el mensaje sea del propio número
        if MY_NUMBER and MY_NUMBER not in sender:
            # Silenciosamente ignorar mensajes de otros números
            return

        # Obtener texto del mensaje
        msg = message.Message
        text = None

        if hasattr(msg, 'conversation') and msg.conversation:
            text = str(msg.conversation)
        elif hasattr(msg, 'extendedTextMessage') and msg.extendedTextMessage:
            if hasattr(msg.extendedTextMessage, 'text'):
                text = str(msg.extendedTextMessage.text)
        elif hasattr(msg, 'protocolMessage'):
            return

        if not text:
            return

        text = text.strip()

        # Mostrar información del mensaje
        logger.info(f"📩 Mensaje de {sender}")
        logger.info(f"💬 Texto: {text}")

        # Obtener o crear session_id para este chat (convertir JID a string para clave)
        chat_key = str(chat)
        sessions = load_sessions()
        session_id = sessions.get(chat_key)

        # Enviar a Claude
        response, new_session_id = ask_claude(text, session_id)

        # Guardar session_id si cambió
        if new_session_id and new_session_id != session_id:
            sessions[chat_key] = new_session_id
            save_sessions(sessions)
            logger.info(f"💾 Session ID guardada para chat: {chat_key}")

        # Mostrar respuesta de Claude
        logger.info(f"🤖 Claude: {response[:200]}...")

        # Enviar respuesta a WhatsApp
        try:
            client.send_message(chat, response)
            logger.info(f"📤 Respuesta enviada a WhatsApp")
        except Exception as e:
            logger.error(f"❌ Error enviando a WhatsApp: {e}")

    except AttributeError:
        pass
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")


def main():
    global client

    logger.info("=" * 50)
    logger.info("🐍 WhatsApp Bot + Claude CLI")
    logger.info("=" * 50)

    # Crear el cliente
    logger.info(f"📂 Base de datos: {DB_PATH}")
    logger.info(f"📂 Sesiones Claude: {SESSIONS_FILE}")

    if os.path.exists(DB_PATH):
        logger.info("💾 Sesión WhatsApp guardada. Reconectando...")
        # Optimizar SQLite antes de conectar
        optimize_sqlite()
    else:
        logger.info("📋 Primera vez. Escanea el QR...")

    client = NewClient(DB_PATH)

    # Registrar eventos
    client.event(ConnectedEv)(on_connected)
    client.event(PairStatusEv)(on_pair_status)
    client.event(HistorySyncEv)(on_history_sync)
    client.event(MessageEv)(on_message)

    # Conectar
    logger.info("\n🔄 Conectando a WhatsApp...\n")

    try:
        client.connect()
    except Exception as e:
        logger.error(f"❌ Error al conectar: {e}")
        sys.exit(1)

    # Mantener corriendo con KeyboardInterrupt simple
    logger.info("\n✅ Bot activo. Presiona Ctrl+C para detener...")
    logger.info("📨 Esperando mensajes...")
    logger.info("💡 Si Ctrl+C no funciona, cierra esta ventana y abre otra.\n")

    running = True
    try:
        # Bucle que espera KeyboardInterrupt o una bandera
        while running:
            import time
            try:
                time.sleep(0.5)
            except:
                running = False
                break
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n⚠️  Interrumpido")
        running = False

    logger.info("👋 Cerrando sesión...")
    if client:
        client.stop()
        logger.info("✅ Cliente detenido correctamente")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n👋 Programa terminado")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
