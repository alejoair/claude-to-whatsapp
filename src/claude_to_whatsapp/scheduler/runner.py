"""Task scheduler runner."""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
from pathlib import Path

try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False

from .models import Task, TaskType, ScheduleType, create_reminder_task, create_action_task

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Scheduler que ejecuta tareas programadas."""

    def __init__(self, tasks_dir: str, on_task_execute: Optional[Callable[[Task], None]] = None):
        """Inicializa el scheduler.

        Args:
            tasks_dir: Directorio donde se guardan las tareas (JSON files).
            on_task_execute: Callback cuando una tarea debe ejecutarse.
                            Recibe la tarea como argumento.
        """
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.on_task_execute = on_task_execute
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tasks: Dict[str, Task] = {}
        self._task_mtimes: Dict[str, float] = {}  # Track file modification times
        self._check_interval = 60  # Verificar cada 60 segundos

    def start(self) -> None:
        """Inicia el scheduler en un thread separado."""
        if self._running:
            return

        self._running = True
        self._load_all_tasks()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"📅 Scheduler iniciado - {len(self._tasks)} tareas cargadas")

    def stop(self) -> None:
        """Detiene el scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("📅 Scheduler detenido")

    def _load_all_tasks(self) -> None:
        """Carga todas las tareas del directorio."""
        self._tasks.clear()
        self._task_mtimes.clear()
        for task_file in self.tasks_dir.glob("*.json"):
            try:
                task_id = task_file.stem
                mtime = task_file.stat().st_mtime
                with open(task_file, "r", encoding="utf-8") as f:
                    task = Task.from_json(f.read())
                if task.enabled:
                    self._tasks[task.id] = task
                    self._task_mtimes[task_id] = mtime
                    self._calculate_next_run(task)
                    logger.debug(f"📅 Tarea cargada: {task.id} - next: {task.next_run}")
            except Exception as e:
                logger.error(f"❌ Error cargando tarea {task_file}: {e}")

    def _run_loop(self) -> None:
        """Loop principal del scheduler."""
        while self._running:
            try:
                self._check_tasks()
                self._check_for_new_tasks()
            except Exception as e:
                logger.error(f"❌ Error en scheduler loop: {e}")

            time.sleep(self._check_interval)

    def _check_for_new_tasks(self) -> None:
        """Verifica si hay tareas nuevas, eliminadas o modificadas."""
        current_files = {}

        # Escanear archivos actuales
        for task_file in self.tasks_dir.glob("*.json"):
            task_id = task_file.stem
            current_files[task_id] = task_file.stat().st_mtime

        # Detectar tareas eliminadas
        for task_id in list(self._tasks.keys()):
            if task_id not in current_files:
                del self._tasks[task_id]
                self._task_mtimes.pop(task_id, None)
                logger.info(f"📅 Tarea eliminada: {task_id}")

        # Detectar tareas nuevas o modificadas
        for task_id, mtime in current_files.items():
            old_mtime = self._task_mtimes.get(task_id)

            if task_id not in self._tasks or (old_mtime and mtime > old_mtime):
                # Tarea nueva o modificada
                try:
                    task_file = self.tasks_dir / f"{task_id}.json"
                    with open(task_file, "r", encoding="utf-8") as f:
                        task = Task.from_json(f.read())

                    self._task_mtimes[task_id] = mtime

                    if task.enabled:
                        self._tasks[task.id] = task
                        self._calculate_next_run(task)

                        if old_mtime:
                            logger.info(f"📅 Tarea modificada: {task.id}")
                        else:
                            logger.info(f"📅 Nueva tarea detectada: {task.id}")
                    elif task_id in self._tasks:
                        # Tarea deshabilitada, remover de memoria
                        del self._tasks[task_id]
                        logger.info(f"📅 Tarea deshabilitada: {task_id}")

                except Exception as e:
                    logger.error(f"❌ Error cargando tarea {task_id}: {e}")

    def _check_tasks(self) -> None:
        """Verifica qué tareas deben ejecutarse."""
        now = datetime.now()

        for task_id, task in list(self._tasks.items()):
            if not task.enabled:
                continue

            if task.next_run:
                try:
                    next_run = datetime.fromisoformat(task.next_run)
                    if now >= next_run:
                        self._execute_task(task)
                        self._update_after_run(task)
                except Exception as e:
                    logger.error(f"❌ Error verificando tarea {task_id}: {e}")

    def _execute_task(self, task: Task) -> None:
        """Ejecuta una tarea."""
        logger.info(f"⏰ Ejecutando tarea: {task.id} ({task.type.value})")

        try:
            if self.on_task_execute:
                self.on_task_execute(task)
            else:
                # Default: solo log
                if task.type == TaskType.REMINDER:
                    logger.info(f"📢 Reminder: {task.payload.get('message')}")
                elif task.type == TaskType.ACTION:
                    logger.info(f"🤖 Action: {task.payload.get('prompt')}")
        except Exception as e:
            logger.error(f"❌ Error ejecutando tarea {task.id}: {e}")

    def _update_after_run(self, task: Task) -> None:
        """Actualiza la tarea después de ejecutarse."""
        now = datetime.now()
        task.last_run = now.isoformat()

        if task.schedule.type == ScheduleType.ONCE:
            # Tareas de una sola vez: eliminar archivo y de memoria
            task_file = self.tasks_dir / f"{task.id}.json"
            try:
                if task_file.exists():
                    task_file.unlink()
                if task.id in self._tasks:
                    del self._tasks[task.id]
                self._task_mtimes.pop(task.id, None)
                logger.info(f"📅 Tarea {task.id} completada y eliminada (once)")
            except Exception as e:
                logger.error(f"❌ Error eliminando tarea {task.id}: {e}")
        else:
            self._calculate_next_run(task)
            # Guardar cambios
            self._save_task(task)

    def _calculate_next_run(self, task: Task) -> None:
        """Calcula la próxima ejecución de una tarea."""
        now = datetime.now()

        if task.schedule.type == ScheduleType.CRON:
            if not HAS_CRONITER:
                logger.error("❌ croniter no instalado. Instala con: pip install croniter")
                return

            try:
                cron = croniter(task.schedule.expression, now)
                task.next_run = cron.get_next(datetime).isoformat()
            except Exception as e:
                logger.error(f"❌ Error parseando cron expression: {e}")

        elif task.schedule.type == ScheduleType.ONCE:
            # Ya tiene el datetime establecido
            if task.schedule.datetime:
                task.next_run = task.schedule.datetime

        elif task.schedule.type == ScheduleType.INTERVAL:
            every = task.schedule.every or 1
            unit = task.schedule.unit or "minutes"

            if unit == "seconds":
                delta = timedelta(seconds=every)
            elif unit == "minutes":
                delta = timedelta(minutes=every)
            elif unit == "hours":
                delta = timedelta(hours=every)
            elif unit == "days":
                delta = timedelta(days=every)
            else:
                delta = timedelta(minutes=every)

            if task.last_run:
                last = datetime.fromisoformat(task.last_run)
                task.next_run = (last + delta).isoformat()
            else:
                task.next_run = (now + delta).isoformat()

    def _save_task(self, task: Task) -> None:
        """Guarda una tarea en disco."""
        task_file = self.tasks_dir / f"{task.id}.json"
        try:
            with open(task_file, "w", encoding="utf-8") as f:
                f.write(task.to_json())
        except Exception as e:
            logger.error(f"❌ Error guardando tarea {task.id}: {e}")

    def add_task(self, task: Task) -> bool:
        """Agrega una nueva tarea."""
        try:
            self._calculate_next_run(task)
            self._save_task(task)
            self._tasks[task.id] = task
            logger.info(f"📅 Tarea agregada: {task.id} - next: {task.next_run}")
            return True
        except Exception as e:
            logger.error(f"❌ Error agregando tarea: {e}")
            return False

    def remove_task(self, task_id: str) -> bool:
        """Elimina una tarea."""
        try:
            task_file = self.tasks_dir / f"{task_id}.json"
            if task_file.exists():
                task_file.unlink()
            if task_id in self._tasks:
                del self._tasks[task_id]
            logger.info(f"📅 Tarea eliminada: {task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error eliminando tarea: {e}")
            return False

    def list_tasks(self) -> list[Task]:
        """Lista todas las tareas."""
        return list(self._tasks.values())

    def get_task(self, task_id: str) -> Optional[Task]:
        """Obtiene una tarea por ID."""
        return self._tasks.get(task_id)
