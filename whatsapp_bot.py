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
# SESSIONS_FILE eliminado - session_id ahora se guarda en DB SQLite
BOT_DB = os.path.join(CONFIG_DIR, "bot_data.db")  # DB adicional para datos del bot

# Separador para respuestas de Claude
BOT_PREFIX = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

# Separador para mensajes del sistema (BOTSYS)
SYS_PREFIX = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"


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
        self.system_prompt = None  # System prompt personalizado

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
                                    time_msg = f"{SYS_PREFIX}BOTSYS:⏳ Tiempo transcurrido: {minutes}m {seconds}s"
                                else:
                                    time_msg = f"{SYS_PREFIX}BOTSYS:⏳ Tiempo transcurrido: {seconds}s"

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

    def load_session_id(self):
        """Carga el session ID de Claude desde la base de datos"""
        try:
            conn = sqlite3.connect(BOT_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM bot_config WHERE key = 'claude_session_id'")
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"❌ Error cargando session_id de DB: {e}")
            return None

    def save_session_id(self, session_id):
        """Guarda el session ID de Claude en la base de datos"""
        try:
            conn = sqlite3.connect(BOT_DB)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO bot_config (key, value)
                VALUES ('claude_session_id', ?)
            """, (session_id,))
            conn.commit()
            conn.close()
            logger.info(f"💾 Session ID guardado en DB: {session_id[:20]}...")
        except Exception as e:
            logger.error(f"❌ Error guardando session_id en DB: {e}")

    def _load_system_prompt(self):
        """Carga el system_prompt.txt del directorio actual si existe"""
        try:
            # Buscar en el directorio actual del script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(script_dir, "system_prompt.txt")

            # También buscar en el directorio de trabajo actual
            if not os.path.exists(prompt_path):
                prompt_path = "system_prompt.txt"

            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    self.system_prompt = f.read().strip()
                logger.info(f"📜 System prompt cargado: {len(self.system_prompt)} caracteres")
            else:
                logger.info("📜 System prompt: no se encontró system_prompt.txt (opcional)")
                self.system_prompt = None
        except Exception as e:
            logger.warning(f"⚠️ Error cargando system_prompt.txt: {e}")
            self.system_prompt = None

    def ask_claude(self, prompt, session_id=None):
        """
        Envía un prompt a Claude usando el CLI y devuelve la respuesta y session_id
        Si session_id es inválido, reintenta automáticamente creando una nueva sesión.
        """
        # Primer intento: usar session_id si existe
        try:
            result, new_session_id = self._execute_claude_command(prompt, session_id)
            if result is not None:  # Éxito
                return result, new_session_id
            # Si result es None, el session_id era inválido, reintentar sin session_id
            logger.info("🔄 Reintentando con nueva sesión...")
        except Exception as e:
            logger.error(f"❌ Error en primer intento: {e}")

        # Segundo intento: crear nueva sesión (sin session_id)
        try:
            logger.info("🆕 Creando nueva sesión de Claude...")
            return self._execute_claude_command(prompt, None)
        except Exception as e:
            logger.error(f"❌ Error creando nueva sesión: {e}")
            return "Hubo un error al comunicarme con Claude.", None

    def _execute_claude_command(self, prompt, session_id):
        """Ejecuta el comando de Claude CLI y devuelve (respuesta, session_id)"""
        result = None
        try:
            # Recargar system_prompt.txt antes de cada mensaje
            self._load_system_prompt()

            # Construir comando base
            base_cmd = "claude"

            # Agregar --append-system-prompt si existe un system prompt personalizado
            if self.system_prompt:
                # Escapar comillas dobles en el prompt
                escaped_prompt = self.system_prompt.replace('"', '\\"')
                base_cmd += f' --append-system-prompt "{escaped_prompt}"'

            # Construir comando completo
            if session_id:
                ps_script = f'{base_cmd} -r "{session_id}" "{prompt}" --output-format json --dangerously-skip-permissions'
            else:
                ps_script = f'{base_cmd} -p "{prompt}" --output-format json --dangerously-skip-permissions'

            logger.info(f"🤖 Comando Claude: {ps_script[:100]}...")
            if not session_id:
                logger.info(f"🤖 Enviando a Claude: {prompt[:50]}...")

            # Ejecutar comando usando PowerShell
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=300,  # Aumentado a 5 minutos
                encoding='utf-8'
            )

            # Debug: Ver qué devolvió el comando
            logger.info(f"🔍 DEBUG - Return code: {result.returncode}")
            logger.info(f"🔍 DEBUG - stdout length: {len(result.stdout)}")
            logger.info(f"🔍 DEBUG - stderr length: {len(result.stderr)}")
            if result.stderr:
                logger.error(f"🔍 DEBUG - stderr: {result.stderr[:500]}")

            # Si el comando falló (return code != 0), verificar si es session inválido
            if result.returncode != 0:
                if "No conversation found" in result.stderr or "session" in result.stderr.lower():
                    logger.warning("⚠️ Session ID inválido o expirado")
                    return None, None  # Indica que debe reintentar sin session_id
                return f"Error del comando Claude: {result.stderr[:200]}", None

            # Parsear respuesta JSON
            response = json.loads(result.stdout)

            # Extraer respuesta y session_id
            response_text = response.get('result', '')
            new_session_id = response.get('session_id', '')

            return response_text, new_session_id

        except subprocess.TimeoutExpired:
            logger.error("⏱️ Timeout esperando respuesta de Claude")
            return "Lo siento, tardé demasiado en responder. Intenta de nuevo.", None
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON de Claude: {e}")
            logger.error(f"Output (stdout): {result.stdout[:500]}")
            logger.error(f"Output (stderr): {result.stderr[:500]}")
            # Si es un session_id inválido, devolver None para permitir reintento
            if result.stderr and "No conversation found" in result.stderr:
                logger.warning("🔄 Session ID inválido detectado.")
                return None, None
            return "Hubo un error procesando la respuesta de Claude.", None
        except Exception as e:
            logger.error(f"❌ Error ejecutando comando Claude: {e}")
            return "Hubo un error al comunicarme con Claude.", None

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
                    self.save_session_id(new_session_id)

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

        # Enviar mensaje de confirmación si es un reinicio y tenemos el número
        if self._reload_notification_sent and self.my_number:
            try:
                # Crear JID usando el número guardado
                from neonize.proto.Neonize_pb2 import JID
                jid_obj = JID()
                jid_obj.User = self.my_number
                jid_obj.RawAgent = 0
                jid_obj.Device = 0
                jid_obj.Integrator = 0
                jid_obj.Server = "s.whatsapp.net"

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
            sender = message.Info.MessageSource.Sender

            # Extraer el campo IsFromMe del MessageSource
            msg_source = message.Info.MessageSource
            is_from_me = msg_source.IsFromMe

            # Verificar si es un self-message: debe ser de mí Y sender debe ser igual a chat
            sender_str = str(sender.User)
            chat_str = str(chat.User)
            is_self_message = is_from_me and (sender_str == chat_str)

            logger.info(f"🔍 Filtro: IsFromMe={is_from_me}, sender==chat={sender_str == chat_str}, is_self_message={is_self_message}")

            if not is_self_message:
                logger.info(f"❌ Mensaje filtrado: No es un self-message (debe ser de ti mismo para ti mismo)")
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
            logger.info(f"💬 Texto: {text}")

            # Procesar comandos del bot primero
            if self.process_bot_command(text, chat, client):
                return  # Si fue un comando, no procesar con Claude

            # Obtener session_id de Claude (compartido para todos los mensajes)
            session_id = self.load_session_id()

            # Enviar a Claude de forma asíncrona (no bloquea el bot)
            self.ask_claude_async(chat, client, text, session_id, str(chat))

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
                    self.client.disconnect()
                    logger.info("✅ Cliente WhatsApp desconectado antes de reiniciar")
            except Exception as e:
                logger.debug(f"Nota: {e}")

            # Reiniciar el script
            try:
                time.sleep(0.2)
                script_full_path = os.path.abspath(sys.argv[0])

                # Comando directo: cambiar al directorio del script y ejecutar
                cmd = f'cd /d "{os.path.dirname(script_full_path)}" && "{sys.executable}" "{script_full_path}"'

                logger.info(f"🔄 Reiniciando...")

                # Ejecutar en una nueva ventana de cmd (más confiable)
                import subprocess
                subprocess.Popen(f'cmd /c {cmd}', creationflags=subprocess.CREATE_NEW_CONSOLE)

                # Salir del proceso actual
                os._exit(0)
            except Exception as e:
                logger.error(f"❌ Error reiniciando: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return True

        elif command == "logout":
            logger.info("🚪 Comando de cierre de sesión recibido...")
            try:
                client.send_message(chat, f"{BOT_PREFIX}🚪 Cerrando sesión de WhatsApp...")

                # Detener notification thread
                self._stop_notification_thread()

                # Primero hacer logout, luego disconnect para liberar el archivo
                if self.client:
                    try:
                        self.client.logout()
                        logger.info("✅ Sesión de WhatsApp cerrada")
                    except Exception as e:
                        logger.warning(f"⚠️ Error en logout: {e}")

                    try:
                        self.client.disconnect()
                        logger.info("✅ Cliente desconectado")
                    except Exception as e:
                        logger.warning(f"⚠️ Error en disconnect: {e}")

                # Pequeña pausa para asegurar que se liberen los recursos
                time.sleep(0.5)

                # Eliminar archivo de sesión para forzar nuevo pairing
                if os.path.exists(DB_PATH):
                    try:
                        os.remove(DB_PATH)
                        logger.info("🗑️ Archivo de sesión eliminado")
                    except PermissionError as e:
                        logger.error(f"❌ No se pudo eliminar {DB_PATH}: {e}")
                        logger.warning("⚠️ Es posible que el archivo esté siendo usado por otro proceso")

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
                client.send_message(chat, f"{SYS_PREFIX}❌ Error: {e}")
            return True

        elif command == "status":
            try:
                session_id = self.load_session_id()
                status_msg = f"📊 Status del Bot:\n"
                status_msg += f"• Número: {self.my_number}\n"
                status_msg += f"• Session ID: {'✅ Activa' if session_id else '❌ No existe'}\n"
                status_msg += f"• DB Path: {DB_PATH}\n"
                status_msg += f"• Python: {sys.version.split()[0]}"
                client.send_message(chat, status_msg)
            except Exception as e:
                client.send_message(chat, f"❌ Error obteniendo status: {e}")
            return True

        elif command == "help":
            help_msg = f"🤖 Comandos disponibles:\n"
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
                client.send_message(chat, f"❌ Comando desconocido: {command}\nUsa BOTSET:help para ver comandos disponibles.")
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
            try:
                self.client.disconnect()
                logger.info("✅ Cliente desconectado correctamente")
            except Exception as e:
                logger.debug(f"Nota: {e}")
        logger.info("✅ Programa terminado")


if __name__ == "__main__":
    try:
        bot = WhatsAppBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("\n👋 Programa terminado")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)
