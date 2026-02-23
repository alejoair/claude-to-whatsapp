"""Main WhatsAppBot class."""

import os
import sys
import logging
import threading
import glob
import json
import tempfile
import subprocess
import time
from typing import Optional

from neonize.events import ConnectedEv, PairStatusEv, MessageEv, HistorySyncEv
from neonize.proto.Neonize_pb2 import JID

from ..config import Config
from ..integration.whatsapp import WhatsAppClient
from ..integration.claude import ClaudeClient
from ..persistence.repositories import BotConfigRepository
from ..notifications.thread import NotificationThread
from ..events.filters import MessageFilter
from .commands import CommandRegistry, BOT_PREFIX

logger = logging.getLogger(__name__)


class WhatsAppBot:
    """Main bot class orchestrating all components."""

    def __init__(self, config: Config):
        """Initialize the bot.

        Args:
            config: Bot configuration.
        """
        self.config = config

        # Clientes
        self.whatsapp_client = WhatsAppClient(config.whatsapp.db_path)
        self.claude_client = ClaudeClient(config.claude.timeout)

        # Repositorio y notificaciones
        self.config_repo = BotConfigRepository(
            os.path.join(config.bot.data_dir, "bot_data.db")
        )
        self.notification_thread = NotificationThread(
            config.bot.notification_interval
        )

        # Comandos
        self.command_registry = CommandRegistry()
        self._register_commands()

        # Estado
        self.my_number: str | None = self._load_my_number()
        self.my_jid: str | None = None
        self._connect_thread: threading.Thread | None = None
        self._startup_message_sent = False  # Flag para mensaje de inicio

        # Cargar system_prompt y agentes del directorio actual
        self.system_prompt = self._load_system_prompt()
        self.agents = self._load_agents()

    def _register_commands(self) -> None:
        """Register bot commands."""
        from .commands import (
            reload_command, logout_command, status_command, help_command, workdir_command
        )

        self.command_registry.register("reload", reload_command, "Reinicia el bot")
        self.command_registry.register("logout", logout_command, "Cierra sesión de WhatsApp")
        self.command_registry.register("status", status_command, "Muestra estado del bot")
        self.command_registry.register("help", help_command, "Muestra ayuda")
        self.command_registry.register("workdir", workdir_command, "Cambia carpeta de trabajo")
        self.command_registry.register("cd", workdir_command, "Alias para workdir")

    def run(self) -> None:
        """Run the bot main loop."""
        logger.info("=" * 50)
        logger.info("claude-to-whatsapp v0.1.0")
        logger.info("=" * 50)
        logger.info(f"📂 DB WhatsApp: {self.config.whatsapp.db_path}")
        logger.info(f"📜 Dir trabajo: {self.config.work_dir}")

        # Configurar eventos de WhatsApp
        self.whatsapp_client.register_handler(ConnectedEv, self.on_connected)
        self.whatsapp_client.register_handler(PairStatusEv, self.on_pair_status)
        self.whatsapp_client.register_handler(HistorySyncEv, self.on_history_sync)
        self.whatsapp_client.register_handler(MessageEv, self.on_message)

        # Conectar en thread separado
        def connect_thread():
            try:
                self.whatsapp_client.connect()
                # El mensaje de inicio se envía desde _main_loop cuando esté conectado
            except Exception as e:
                logger.error(f"❌ Error al conectar: {e}")

        self._connect_thread = threading.Thread(target=connect_thread, daemon=True)
        self._connect_thread.start()

        # Iniciar thread de notificaciones
        self.notification_thread.start()

        # Main loop
        self._main_loop()

    def _main_loop(self) -> None:
        """Main bot loop."""
        logger.info("\n✅ Bot activo. Presiona Ctrl+C para detener...")
        logger.info("📨 Esperando mensajes...")

        running = True
        try:
            while running:
                time.sleep(0.5)

                # Enviar mensaje de inicio si está conectado y no se ha enviado
                if not self._startup_message_sent and self.whatsapp_client.is_connected():
                    self._send_startup_message()
                    # Nota: _startup_message_sent se marca True dentro del thread

                if self._connect_thread and not self._connect_thread.is_alive():
                    logger.warning("⚠️ La conexión de WhatsApp terminó")
                    running = False
        except (KeyboardInterrupt, SystemExit):
            logger.info("\n⚠️ Interrumpido")
            running = False

        self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown the bot."""
        logger.info("👋 Cerrando sesión...")
        self.notification_thread.stop()
        self.whatsapp_client.disconnect()
        logger.info("✅ Programa terminado")

    # ========== Eventos de WhatsApp ==========

    def on_connected(self, client: WhatsAppClient, _: ConnectedEv) -> None:
        """Evento cuando se conecta a WhatsApp."""
        # El mensaje de inicio se envía desde _main_loop cuando la conexión esté lista
        # No enviar aquí para evitar el error "usync query timed out"
        pass

    def on_pair_status(self, client: WhatsAppClient, message: PairStatusEv) -> None:
        """Evento cuando se completa el emparejamiento."""
        self.my_number = str(message.ID.User)
        self.my_jid = str(message.ID)

        # Guardar en DB
        self.config_repo.set("my_number", self.my_number)
        self.config_repo.set("my_jid", self.my_jid)

        logger.info(f"✅ Sesión guardada. Tu número: {self.my_number}")
        # El mensaje de inicio se envía desde _main_loop vía _send_startup_message()

    def on_history_sync(self, client: WhatsAppClient, history: HistorySyncEv) -> None:
        """Evento cuando se sincroniza el historial."""
        pass

    def _send_startup_message(self) -> None:
        """Envía mensaje de inicio a sí mismo en un thread separado con delay.
        Esto evita el error "failed to get device list: usync query timed out"
        """
        # Marcar flag ANTES de crear el thread para evitar múltiples envíos
        self._startup_message_sent = True

        my_number = self.config_repo.get("my_number")
        if not my_number:
            logger.warning("⚠️ No se encontró my_number en DB, no se puede enviar mensaje de inicio")
            return

        def send_startup():
            import time
            time.sleep(3)  # Esperar a que la conexión se estabilice
            try:
                from neonize.proto.Neonize_pb2 import JID
                chat_jid = JID()
                chat_jid.User = my_number
                chat_jid.Server = "s.whatsapp.net"
                chat_jid.Device = 0
                chat_jid.Integrator = 0
                chat_jid.RawAgent = 0

                msg = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                msg += f"✅ claude-to-whatsapp v0.1.0 iniciado\n\n"
                msg += f"📂 Dir trabajo: {self.config.work_dir}\n"
                msg += f"📁 DB WhatsApp: {self.config.whatsapp.db_path}\n"
                msg += f"📁 DB Bot: {os.path.join(self.config.bot.data_dir, 'bot_data.db')}\n"
                msg += f"📁 Logs: {os.path.join(self.config.work_dir, 'whatsapp.log')}\n\n"
                msg += f"ℹ️ Envíate un comando como BOTSET:help para más información"
                msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

                self.whatsapp_client.send_message(chat_jid, msg)
                logger.info("📤 Mensaje de inicio enviado")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar mensaje de inicio: {e}")

        threading.Thread(target=send_startup, daemon=True).start()

    def on_message(self, client: WhatsAppClient, message: MessageEv) -> None:
        """Evento cuando se recibe un mensaje."""
        try:
            # Extraer texto
            text = MessageFilter.extract_text(message)
            msg_source = message.Info.MessageSource

            logger.info(f"📥 Mensaje recibido - IsFromMe: {msg_source.IsFromMe}, Sender: {msg_source.Sender.User}, Chat: {msg_source.Chat.User}, Text: {text}")

            if not text:
                return

            text = text.strip()

            # Filtrar mensajes del sistema
            if MessageFilter.is_system_message(text):
                logger.info("⏭️ Ignorando mensaje del sistema")
                return

            # Filtrar: solo self-messages
            if not MessageFilter.is_self_message(msg_source):
                logger.info("⏭️ Ignorando mensaje (no es self-message)")
                return

            logger.info(f"💬 Mensaje procesado: {text}")

            # Procesar comandos del bot
            if MessageFilter.is_bot_command(text):
                # Pasar texto completo al comando (incluye argumentos)
                command_text = text[7:].strip()  # Remover "BOTSET:"
                # Obtener nombre del comando (primera palabra)
                command_name = command_text.split()[0].lower() if command_text.split() else ""
                # Pasar texto completo como último argumento
                result = self.command_registry.execute(command_name, self, message, client, command_text)
                if result:
                    client.send_message(message.Info.MessageSource.Chat, result)
                return

            # Enviar a Claude
            chat = message.Info.MessageSource.Chat
            self._ask_claude_async(chat, client, text, str(chat))

        except AttributeError:
            pass
        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")

    # ========== Claude ==========

    def _load_system_prompt(self) -> str | None:
        """Carga system_prompt.txt del directorio actual."""
        try:
            prompt_path = self.config.system_prompt_path
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                logger.info(f"📜 System prompt cargado: {len(content)} caracteres")
                return content
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error cargando system_prompt: {e}")
            return None

    def reload_resources(self) -> bool:
        """Recarga recursos (system_prompt, agents) del work_dir actual.

        Returns:
            True si los recursos se recargaron exitosamente, False si hubo errores.
        """
        try:
            new_prompt = self._load_system_prompt()
            new_agents = self._load_agents()
            # system_prompt.txt es opcional, permitir que no exista
            self.system_prompt = new_prompt or ""
            self.agents = new_agents
            logger.info("✅ Recursos recargados exitosamente")
            return True
        except Exception as e:
            logger.error(f"❌ Error recargando recursos: {e}")
            return False

    def _load_agents(self) -> str | None:
        """Carga agentes del directorio .claude/agents/."""
        try:
            agents_dir = self.config.agents_dir
            if not os.path.exists(agents_dir):
                return None

            agents = {}
            md_files = glob.glob(os.path.join(agents_dir, "*.md"))

            for md_file in md_files:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Parsear frontmatter YAML
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        yaml_content = parts[1]
                        markdown_content = parts[2].strip()

                        name = None
                        agent_def = {"prompt": markdown_content}

                        for line in yaml_content.split("\n"):
                            line = line.strip()
                            if line.startswith("name:"):
                                name = line.split(":", 1)[1].strip()
                            elif line.startswith("description:"):
                                agent_def["description"] = line.split(":", 1)[1].strip()
                            elif line.startswith("tools:"):
                                tools_str = line.split(":", 1)[1].strip()
                                if tools_str:
                                    agent_def["tools"] = [t.strip() for t in tools_str.split(",")]
                            elif line.startswith("skills:"):
                                skills_str = line.split(":", 1)[1].strip()
                                if skills_str:
                                    agent_def["skills"] = [s.strip() for s in skills_str.split(",")]
                            elif line.startswith("model:"):
                                agent_def["model"] = line.split(":", 1)[1].strip()

                        if name:
                            agents[name] = agent_def

            if agents:
                agents_json = json.dumps(agents)
                logger.info(f"📜 {len(agents)} agentes cargados")
                return agents_json

        except Exception as e:
            logger.warning(f"⚠️ Error cargando agentes: {e}")

        return None

    def _load_my_number(self) -> str | None:
        """Carga el número guardado."""
        return self.config_repo.get("my_number")

    def _ask_claude_async(self, chat, client: WhatsAppClient, prompt: str, chat_key: str) -> None:
        """Envía prompt a Claude de forma asíncrona."""
        import time

        # Registrar solicitud pendiente
        self.notification_thread.add_request(
            chat_key,
            {
                "chat": chat,
                "client": client,
                "start_time": time.time(),
                "prompt": prompt,
            }
        )

        def _process():
            try:
                # Cargar agentes frescos antes de enviar a Claude
                current_agents = self._load_agents()

                # Verificar si existe system_prompt.txt y pasar la ruta
                system_prompt_file = None
                if os.path.exists(self.config.system_prompt_path):
                    system_prompt_file = self.config.system_prompt_path

                # Primero intentar cargar session_id específico del work_dir actual
                from .commands import _get_session_key
                session_key = _get_session_key(self.config.work_dir)
                session_id = self.config_repo.get(session_key)

                # Si no hay session_id específico, usar el genérico
                if not session_id:
                    session_id = self.config_repo.get("claude_session_id")

                # Pasar agentes y system_prompt_file a Claude
                response, new_session_id = self.claude_client.ask(
                    prompt, session_id, agents=current_agents, system_prompt_file=system_prompt_file
                )

                # Guardar session_id en ambas claves
                if new_session_id:
                    session_key = _get_session_key(self.config.work_dir)
                    self.config_repo.set(session_key, new_session_id)
                    self.config_repo.set("claude_session_id", new_session_id)

                # Enviar respuesta
                client.send_message(chat, f"{BOT_PREFIX}{response}")
                logger.info(f"📤 Respuesta enviada")

            except Exception as e:
                logger.error(f"❌ Error en thread de Claude: {e}")
            finally:
                self.notification_thread.remove_request(chat_key)

        thread = threading.Thread(target=_process, daemon=True)
        thread.start()
