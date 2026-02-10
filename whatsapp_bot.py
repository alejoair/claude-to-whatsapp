#!/usr/bin/env python3
"""WhatsApp Bot con Neonize + Claude CLI Integration"""

import logging
import os
import sys
import subprocess
import json
import sqlite3
import signal
import atexit
import time

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
BOT_DB = os.path.join(CONFIG_DIR, "bot_data.db")  # DB adicional para datos del bot

# Header estético para todos los mensajes del bot (una sola línea)
BOT_PREFIX = "━━━🤖✨ CLAUDE BOT ✨🤖━━━\n\n"


class WhatsAppBot:
    """Bot de WhatsApp con integración a Claude"""

    def __init__(self):
        self.client = None
        self.my_number = None
        self.my_jid = None  # JID completo para enviar mensajes a uno mismo
        self.pending_requests = {}  # chat_key -> {'start_time': timestamp, 'prompt': str, 'chat': chat_obj}
        self._notification_thread = None
        self._notification_running = False
        self._notification_lock = None  # Lock para thread safety

        # Inicializar DB del bot
        self._init_bot_db()

        # Verificar si es un reinicio para enviar notificación
        reload_flag = os.path.join(CONFIG_DIR, ".reload_flag")
        self._reload_notification_sent = os.path.exists(reload_flag)
        if self._reload_notification_sent:
            try:
                os.remove(reload_flag)
            except:
                pass

        # Cargar datos guardados si existen
        self.my_jid = self._load_my_jid()
        self.my_number = self._load_my_number()  # Cargar número guardado

    def _start_notification_thread(self):
        """Inicia el thread de notificaciones periódicas"""
        if self._notification_running:
            return

        import threading
        self._notification_lock = threading.Lock()
        self._notification_running = True

        def notification_loop():
            while self._notification_running:
                try:
                    time.sleep(30)  # Verificar cada 30 segundos
                    if not self._notification_running:
                        break

                    current_time = time.time()
                    with self._notification_lock:
                        expired_keys = []
                        for chat_key, req_data in self.pending_requests.items():
                            elapsed = int(current_time - req_data['start_time'])
                            if elapsed >= 30:  # Enviar notificación cada 30s
                                minutes = elapsed // 60
                                seconds = elapsed % 60

                                if minutes > 0:
                                    time_msg = f"{BOT_PREFIX}BOTSYS:⏳ Tiempo transcurrido: {minutes}m {seconds}s"
                                else:
                                    time_msg = f"{BOT_PREFIX}BOTSYS:⏳ Tiempo transcurrido: {seconds}s"

                                try:
                                    req_data['client'].send_message(req_data['chat'], time_msg)
                                    logger.info(f"📤 Notificación de tiempo enviada a {chat_key}: {time_msg}")
                                except Exception as e:
                                    logger.error(f"❌ Error enviando notificación: {e}")

                except Exception as e:
                    logger.error(f"❌ Error en thread de notificaciones: {e}")

        self._notification_thread = threading.Thread(target=notification_loop, daemon=True)
        self._notification_thread.start()
        logger.info("✅ Thread de notificaciones iniciado")

    def _stop_notification_thread(self):
        """Detiene el thread de notificaciones"""
        self._notification_running = False

    def _init_bot_db(self):
        """Inicializa la base de datos del bot"""
        try:
            conn = sqlite3.connect(BOT_DB)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Error inicializando DB del bot: {e}")

    def _save_my_jid(self, jid):
        """Guarda el JID del propio usuario"""
        try:
            conn = sqlite3.connect(BOT_DB)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO bot_config (key, value)
                VALUES ('my_jid', ?)
            """, (str(jid),))
            conn.commit()
            conn.close()
            logger.info(f"💾 JID guardado: {jid}")
        except Exception as e:
            logger.error(f"❌ Error guardando JID: {e}")

    def _save_my_number(self, number):
        """Guarda el número del propio usuario"""
        try:
            conn = sqlite3.connect(BOT_DB)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO bot_config (key, value)
                VALUES ('my_number', ?)
            """, (str(number),))
            conn.commit()
            conn.close()
            logger.info(f"💾 Número guardado: {number}")
        except Exception as e:
            logger.error(f"❌ Error guardando número: {e}")

    def _load_my_jid(self):
        """Carga el JID del propio usuario"""
        try:
            conn = sqlite3.connect(BOT_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM bot_config WHERE key = 'my_jid'")
            result = cursor.fetchone()
            conn.close()
            if result:
                logger.info(f"📱 JID cargado: {result[0]}")
                return result[0]
        except Exception as e:
            logger.error(f"❌ Error cargando JID: {e}")
        return None

    def _load_my_number(self):
        """Carga el número del propio usuario"""
        try:
            conn = sqlite3.connect(BOT_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM bot_config WHERE key = 'my_number'")
            result = cursor.fetchone()
            conn.close()
            if result:
                logger.info(f"📱 Número cargado: {result[0]}")
                return result[0]
        except Exception as e:
            logger.error(f"❌ Error cargando número: {e}")
        return None

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
                timeout=300,  # Aumentado a 5 minutos
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

    def ask_claude_async(self, chat, client, prompt, session_id, chat_key):
        """
        Ejecuta ask_claude en un thread separado y envía la respuesta.
        También envía mensajes de estado periódicos cada 30 segundos.
        """
        import threading

        # Registrar la solicitud como pendiente
        self.pending_requests[chat_key] = {
            'start_time': time.time(),
            'prompt': prompt,
            'chat': chat,
            'client': client
        }

        def _process():
            try:
                response, new_session_id = self.ask_claude(prompt, session_id)

                # Guardar session_id si cambió
                if new_session_id and new_session_id != session_id:
                    sessions = self.load_sessions()
                    sessions[chat_key] = new_session_id
                    self.save_sessions(sessions)
                    logger.info(f"💾 Session ID guardada para chat: {chat_key}")

                # Mostrar respuesta de Claude
                logger.info(f"🤖 Claude: {response[:200]}...")

                # Enviar respuesta a WhatsApp con prefijo del bot
                try:
                    client.send_message(chat, f"{BOT_PREFIX}{response}")
                    logger.info(f"📤 Respuesta enviada a WhatsApp")
                except Exception as e:
                    logger.error(f"❌ Error enviando a WhatsApp: {e}")
            except Exception as e:
                logger.error(f"❌ Error en thread de Claude: {e}")
            finally:
                # Limpiar solicitud pendiente (siempre ejecutar, incluso si hay error)
                with self._notification_lock:
                    if chat_key in self.pending_requests:
                        del self.pending_requests[chat_key]
                        logger.info(f"✅ Solicitud completada y eliminada para {chat_key}")

        # Iniciar thread de procesamiento de Claude
        thread = threading.Thread(target=_process, daemon=True)
        thread.start()

    def on_connected(self, client: NewClient, _: ConnectedEv):
        """Evento cuando se conecta a WhatsApp"""
        logger.info("⚡ ¡Conectado a WhatsApp!")

        # Enviar mensaje de confirmación si es un reinicio y tenemos el JID
        if self._reload_notification_sent and self.my_jid:
            try:
                # Crear JID desde el string guardado
                from neonize.proto.wa import JID
                jid_obj = JID()
                jid_obj.ParseFromString(bytes.fromhex(self.my_jid.split('@')[0]))

                client.send_message(jid_obj, f"{BOT_PREFIX}✅ Bot reiniciado exitosamente")
                logger.info("📤 Mensaje de reinicio enviado")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar mensaje de reinicio: {e}")
            self._reload_notification_sent = False

    def on_pair_status(self, _: NewClient, message: PairStatusEv):
        """Evento cuando se completa el emparejamiento"""
        self.my_number = str(message.ID.User)
        self.my_jid = str(message.ID)  # Guardar JID completo

        # Guardar en DB para futuros reinicios
        self._save_my_number(self.my_number)
        self._save_my_jid(self.my_jid)

        logger.info(f"✅ Sesión guardada exitosamente")
        logger.info(f"📱 Tu número: {self.my_number}")
        logger.info(f"📱 Tu JID completo: {self.my_jid}")
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
            logger.info(f"🔍 Filtro: my_number={self.my_number}, sender={sender_number}, chat={chat_number}")
            if self.my_number != sender_number or self.my_number != chat_number:
                logger.info(f"❌ Mensaje filtrado: No es un self-message")
                return
            logger.info(f"✅ Mensaje aceptado: Es un self-message")

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

            # Ignorar mensajes del sistema (evita bucles infinitos)
            if text.startswith("BOTSYS:"):
                logger.info(f"🔇 Mensaje del sistema ignorado: {text[:50]}...")
                return

            # Mostrar información del mensaje
            logger.info(f"📩 Self-message: {sender_number} → {chat_number}")
            logger.info(f"💬 Texto: {text}")

            # Procesar comandos del bot primero
            if self.process_bot_command(text, chat, client):
                return  # Si fue un comando, no procesar con Claude

            # Obtener o crear session_id para este chat
            chat_key = str(chat)
            sessions = self.load_sessions()
            session_id = sessions.get(chat_key)

            # Enviar a Claude de forma asíncrona (no bloquea el bot)
            self.ask_claude_async(chat, client, text, session_id, chat_key)

        except AttributeError:
            pass
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")

    def process_bot_command(self, text: str, chat, client) -> bool:
        """
        Procesa comandos especiales del bot.
        Retorna True si el mensaje fue un comando y fue procesado.
        """
        if not text.startswith("BOTSET:"):
            return False

        command = text[7:].strip().lower()  # Remover "BOTSET:" y obtener comando

        logger.info(f"🔧 Comando recibido: {command}")

        if command == "reload":
            logger.info("🔄 Comando de reinicio recibido. Reiniciando bot...")
            try:
                client.send_message(chat, f"{BOT_PREFIX}🔄 Reiniciando bot...")
            except:
                pass

            # Marcar que se debe enviar notificación al reconectar
            self._reload_notification_sent = True

            # Guardar marca de reinicio en archivo
            try:
                reload_flag = os.path.join(CONFIG_DIR, ".reload_flag")
                with open(reload_flag, 'w') as f:
                    f.write("reloading")
            except:
                pass

            # Detener notification thread
            self._stop_notification_thread()
            logger.info("🛑 Thread de notificaciones detenido")

            # Detener cliente de WhatsApp
            try:
                if self.client:
                    self.client.Disconnect()
                    logger.info("✅ Cliente WhatsApp detenido antes de reiniciar")
            except Exception as e:
                logger.warning(f"⚠️ Error deteniendo cliente: {e}")

            # Reiniciar el script
            os.execv(sys.executable, [sys.executable] + sys.argv)
            return True

        elif command == "logout":
            logger.info("🚪 Comando de cierre de sesión recibido...")
            try:
                client.send_message(chat, f"{BOT_PREFIX}🚪 Cerrando sesión de WhatsApp...")

                # Detener notification thread
                self._stop_notification_thread()

                # Detener y desconectar cliente
                if self.client:
                    self.client.Logout()
                    logger.info("✅ Sesión de WhatsApp cerrada")

                # Eliminar archivo de sesión para forzar nuevo pairing
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                    logger.info("🗑️ Archivo de sesión eliminado")

                # Eliminar también datos guardados
                if os.path.exists(BOT_DB):
                    conn = sqlite3.connect(BOT_DB)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM bot_config WHERE key IN ('my_jid', 'my_number')")
                    conn.commit()
                    conn.close()
                    logger.info("🗑️ Datos guardados eliminados")

                # Terminar el programa
                logger.info("👋 Saliendo...")
                os._exit(0)
            except Exception as e:
                logger.error(f"❌ Error cerrando sesión: {e}")
                client.send_message(chat, f"{BOT_PREFIX}❌ Error: {e}")
            return True

        elif command == "status":
            try:
                status_msg = f"{BOT_PREFIX}📊 Status del Bot:\n"
                status_msg += f"• Número: {self.my_number}\n"
                status_msg += f"• Sesiones: {len(self.load_sessions())}\n"
                status_msg += f"• DB Path: {DB_PATH}\n"
                status_msg += f"• Python: {sys.version.split()[0]}"
                client.send_message(chat, status_msg)
            except Exception as e:
                client.send_message(chat, f"{BOT_PREFIX}❌ Error obteniendo status: {e}")
            return True

        elif command == "help":
            help_msg = f"{BOT_PREFIX}🤖 Comandos disponibles:\n"
            help_msg += "• BOTSET:reload - Reinicia el bot\n"
            help_msg += "• BOTSET:logout - Cierra la sesión de WhatsApp\n"
            help_msg += "• BOTSET:status - Muestra el estado del bot\n"
            help_msg += "• BOTSET:help - Muestra esta ayuda\n\n"
            help_msg += "💡 Nota: Los mensajes que comienzan con BOTSYS: son del sistema y se ignoran automáticamente."
            try:
                client.send_message(chat, help_msg)
            except Exception as e:
                logger.error(f"❌ Error enviando ayuda: {e}")
            return True

        else:
            try:
                client.send_message(chat, f"{BOT_PREFIX}❌ Comando desconocido: {command}\nUsa BOTSET:help para ver comandos disponibles.")
            except:
                pass
            return True

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

        # Iniciar thread de notificaciones periódicas
        self._start_notification_thread()

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
            self.client.Disconnect()
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
