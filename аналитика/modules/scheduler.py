"""
Модуль для планирования задач
"""
import schedule
import threading
import time
from datetime import datetime

class TaskScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        self.tasks = {}
    
    def add_task(self, task_id, task_type, schedule_time, callback, **kwargs):
        """Добавление задачи в расписание"""
        if task_id in self.tasks:
            self.remove_task(task_id)

        self.tasks[task_id] = {
            'type': task_type,
            'schedule_time': schedule_time,
            'callback': callback,
            'kwargs': kwargs,
            'enabled': True
        }

        job = None
        if task_type == 'daily':
            job = schedule.every().day.at(schedule_time).do(self._execute_task, task_id)
        elif task_type == 'hourly':
            job = schedule.every(int(schedule_time)).hours.do(self._execute_task, task_id)
        elif task_type == 'weekly':
            day, time_str = schedule_time.split(' ', 1)
            job = getattr(schedule.every(), day.lower()).at(time_str).do(self._execute_task, task_id)
        else:
            raise ValueError(f"Неизвестный тип задачи: {task_type}")

        if job is not None:
            job.tag(task_id)
            self.tasks[task_id]['job'] = job
    
    def _execute_task(self, task_id):
        """Выполнение задачи"""
        if task_id in self.tasks and self.tasks[task_id]['enabled']:
            task = self.tasks[task_id]
            try:
                task['callback'](**task['kwargs'])
            except Exception as e:
                print(f"Ошибка при выполнении задачи {task_id}: {e}")
    
    def remove_task(self, task_id):
        """Удаление задачи"""
        if task_id in self.tasks:
            self.tasks[task_id]['enabled'] = False
            schedule.clear(task_id)
            del self.tasks[task_id]
    
    def start(self):
        """Запуск планировщика"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Остановка планировщика"""
        self.running = False
        schedule.clear()
        self.tasks.clear()
    
    def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.running:
            schedule.run_pending()
            time.sleep(30)
    
    def get_tasks_list(self):
        """Получение списка задач"""
        return list(self.tasks.keys())
