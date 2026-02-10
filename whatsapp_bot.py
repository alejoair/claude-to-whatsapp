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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(CONFIG_DIR, 'whatsapp.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Importar Neonize
from neonize.client import NewClient
from neonize.events import ConnectedEv, PairStatusEv, MessageEv, HistorySyncEv

# Configuración
DB_PATH = os.path.join(CONFIG_DIR, "whatsapp_session.db")
SESSIONS_FILE = os.path.join(CONFIG_DIR, "claude_sessions.json")


class WhatsAppBot:
    """Bot de WhatsApp con integración a Claude"""

    def __init__(self):
        self.client = None
        self.my_number = None

    def load_sessions(self):
        """Carga los session IDs de Claude desde archivo"""
        if os.path.exists(SESSIONS_FILE):
            try:
                with open(SESSIONS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_sessions(self, sessions):
        """Guarda los session IDs de Claude en archivo"""
        try:
            with open(SESSIONS_FILE, 'w') as f:
                json.dump(sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando sesiones: {e}")

    def ask_claude(self, prompt, session_id=None):
        """
        Envía un prompt a Claude usando el CLI y devuelve la respuesta y session_id
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

    def on_connected(self, client: NewClient, _: ConnectedEv):
        """Evento cuando se conecta a WhatsApp"""
        logger.info("⚡ ¡Conectado a WhatsApp!")

    def on_pair_status(self, _: NewClient, message: PairStatusEv):
        """Evento cuando se completa el emparejamiento"""
        self.my_number = str(message.ID.User)
        logger.info(f"✅ Sesión guardada exitosamente")
        logger.info(f"📱 Tu número: {self.my_number}")
        logger.info(f"📱 Tu JID completo: {message.ID}")
        logger.info(f"💾 Credenciales guardadas en: {DB_PATH}")
        logger.info(f"🔒 Solo responderás a self-messages (mensajes que te envías a ti mismo)")

    def on_history_sync(self, client: NewClient, history: HistorySyncEv):
        """Evento cuando se sincroniza el historial"""
        pass

    def on_message(self, client: NewClient, message: MessageEv):
        """Evento cuando se recibe un mensaje"""
        try:
            # Obtener información del mensaje
            chat = message.Info.MessageSource.Chat
            sender_number = str(message.Info.MessageSource.Sender.User)
            chat_number = str(chat.User)

            # Si my_number no está establecido, intentar obtenerlo del cliente
            if not self.my_number:
                logger.warning(f"⚠️ MY_NUMBER no está establecido. Intentando obtenerlo...")
                self._try_get_number_from_message(message)
                if not self.my_number:
                    logger.warning(f"⚠️ No se pudo determinar MY_NUMBER. Ignorando mensaje.")
                    return

            # Verificar que sea un self-message (sender y chat deben ser tu número)
            if self.my_number != sender_number or self.my_number != chat_number:
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
            logger.info(f"📩 Self-message: {sender_number} → {chat_number}")
            logger.info(f"💬 Texto: {text}")

            # Obtener o crear session_id para este chat
            chat_key = str(chat)
            sessions = self.load_sessions()
            session_id = sessions.get(chat_key)

            # Enviar a Claude
            response, new_session_id = self.ask_claude(text, session_id)

            # Guardar session_id si cambió
            if new_session_id and new_session_id != session_id:
                sessions[chat_key] = new_session_id
                self.save_sessions(sessions)
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

    def _try_get_number_from_message(self, message: MessageEv):
        """Intenta deducir my_number del primer mensaje recibido"""
        try:
            sender = str(message.Info.MessageSource.Sender.User)
            chat = str(message.Info.MessageSource.Chat.User)

            # Si sender y chat son iguales, es un self-message
            if sender == chat:
                self.my_number = sender
                logger.info(f"📱 Tu número (deducido del mensaje): {self.my_number}")
        except:
            pass

    def optimize_sqlite(self):
        """Optimiza la base de datos SQLite"""
        if not os.path.exists(DB_PATH):
            return

        try:
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            cursor = conn.cursor()

            cursor.execute("PRAGMA journal_mode=WAL;")
            wal_mode = cursor.fetchone()
            logger.info(f"📊 SQLite WAL mode: {wal_mode[0]}")

            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA cache_size=-10000;")
            cursor.execute("PRAGMA temp_store=MEMORY;")

            conn.commit()
            conn.close()
            logger.info("✅ Base de datos SQLite optimizada")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo optimizar SQLite: {e}")

    def run(self):
        """Ejecuta el bot"""
        import threading

        logger.info("=" * 50)
        logger.info("🐍 WhatsApp Bot + Claude CLI")
        logger.info("=" * 50)
        logger.info(f"📂 Base de datos: {DB_PATH}")
        logger.info(f"📂 Sesiones Claude: {SESSIONS_FILE}")

        if os.path.exists(DB_PATH):
            logger.info("💾 Sesión WhatsApp guardada. Reconectando...")
            self.optimize_sqlite()
        else:
            logger.info("📋 Primera vez. Escanea el QR...")

        # Crear el cliente
        self.client = NewClient(DB_PATH)

        # Registrar eventos
        self.client.event(ConnectedEv)(self.on_connected)
        self.client.event(PairStatusEv)(self.on_pair_status)
        self.client.event(HistorySyncEv)(self.on_history_sync)
        self.client.event(MessageEv)(self.on_message)

        # Conectar en un thread separado (client.connect() bloquea)
        logger.info("\n🔄 Conectando a WhatsApp...\n")

        def connect_thread():
            try:
                self.client.connect()
            except Exception as e:
                logger.error(f"❌ Error al conectar: {e}")

        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

        # Esperar un momento para que se conecte
        import time
        time.sleep(2)

        logger.info("\n✅ Bot activo. Presiona Ctrl+C para detener...")
        logger.info("📨 Esperando mensajes...")
        logger.info("🔒 Envia un self-message (mensaje a ti mismo) para probar\n")

        # Mantener corriendo
        running = True
        try:
            while running:
                time.sleep(0.5)
                if not thread.is_alive():
                    logger.warning("⚠️ La conexión de WhatsApp terminó inesperadamente")
                    running = False
        except (KeyboardInterrupt, SystemExit):
            logger.info("\n⚠️  Interrumpido")
            running = False

        logger.info("👋 Cerrando sesión...")
        if self.client:
            self.client.stop()
            logger.info("✅ Cliente detenido correctamente")


if __name__ == "__main__":
    try:
        bot = WhatsAppBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("\n👋 Programa terminado")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
