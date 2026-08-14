"""
Вкладка «Видео»: список внешних .py скриптов, запуск и остановка.
Без встроенных перестановок — только абсолютные пути к скриптам.
"""
import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext


def create_video_tab(self):
    """Вкладка для запуска внешних video-скриптов."""
    video_frame = ttk.Frame(self.notebook)
    self.notebook.add(video_frame, text="🎬 Видео")

    control_frame = tk.Frame(video_frame, bg=self.colors['card_bg'], relief=tk.FLAT)
    control_frame.pack(fill=tk.X, padx=15, pady=15)

    actions = tk.Frame(control_frame, bg=self.colors['card_bg'])
    actions.pack(side=tk.LEFT, padx=5)

    self.video_start_btn = self.create_modern_button(
        actions, "▶️ Запустить", self.start_video_script, self.colors['accent']
    )
    self.video_start_btn.pack(side=tk.LEFT, padx=3)

    self.video_stop_btn = self.create_modern_button(
        actions, "⏹️ Остановить", self.stop_video_script, self.colors['danger']
    )
    self.video_stop_btn.pack(side=tk.LEFT, padx=3)
    self.video_stop_btn.config(state=tk.DISABLED)

    self.create_modern_button(
        actions, "➕ Добавить", self.add_video_script, self.colors['success']
    ).pack(side=tk.LEFT, padx=3)

    self.create_modern_button(
        actions, "➖ Удалить", self.remove_video_script, self.colors['text_secondary']
    ).pack(side=tk.LEFT, padx=3)

    list_content, _, _ = self.create_rounded_card(
        video_frame, "📜 Скрипты", self.colors['accent'], fill=tk.BOTH, expand=True
    )
    list_inner = tk.Frame(list_content, bg=self.colors['card_bg'])
    list_inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    tk.Label(
        list_inner,
        text="Дважды кликните по скрипту или выберите и нажмите «Запустить»",
        bg=self.colors['card_bg'],
        fg=self.colors['text_secondary'],
        font=('Segoe UI', 8)
    ).pack(anchor=tk.W, pady=(0, 6))

    list_wrap = tk.Frame(list_inner, bg=self.colors['card_bg'])
    list_wrap.pack(fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(list_wrap)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    self.video_scripts_listbox = tk.Listbox(
        list_wrap,
        font=('Consolas', 9),
        bg=self.colors.get('entry_bg', self.colors['card_bg']),
        fg=self.colors['fg'],
        selectbackground=self.colors['accent'],
        selectforeground='white',
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=self.colors['border'],
        activestyle='none',
        height=8,
        yscrollcommand=scrollbar.set
    )
    self.video_scripts_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=self.video_scripts_listbox.yview)
    self.video_scripts_listbox.bind("<Double-Button-1>", lambda e: self.start_video_script())

    progress_content, _, _ = self.create_rounded_card(
        video_frame, "📊 Статус", self.colors['success'], fill=tk.X
    )
    progress_inner = tk.Frame(progress_content, bg=self.colors['card_bg'])
    progress_inner.pack(fill=tk.X, padx=15, pady=12)

    self.video_progress = ttk.Progressbar(progress_inner, mode='indeterminate')
    self.video_progress.pack(fill=tk.X, pady=(0, 8))

    self.video_status_label = tk.Label(
        progress_inner,
        text="Готов к запуску",
        bg=self.colors['card_bg'],
        fg=self.colors['text_secondary'],
        font=('Segoe UI', 9)
    )
    self.video_status_label.pack(anchor=tk.W)

    log_content, _, _ = self.create_rounded_card(
        video_frame, "📝 Лог", self.colors['text_secondary'], fill=tk.BOTH, expand=True
    )
    self.video_log = scrolledtext.ScrolledText(
        log_content, height=12, wrap=tk.WORD,
        font=('Consolas', 9),
        bg=self.colors['card_bg'],
        fg=self.colors['fg'],
        relief=tk.FLAT
    )
    self.video_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
    self.video_log.config(state=tk.DISABLED)

    self.video_process = None
    self.video_thread = None
    self.video_stop_flag = False
    self.video_input_entry = None
    self.video_output_entry = None

    self._reload_video_scripts_list()


def _get_video_scripts(self):
    scripts = self.config.get('video_scripts')
    if not isinstance(scripts, list):
        scripts = []
        self.config['video_scripts'] = scripts
    return scripts


def _save_video_scripts(self, scripts):
    self.config['video_scripts'] = scripts
    self.save_config()


def _reload_video_scripts_list(self):
    if not hasattr(self, 'video_scripts_listbox'):
        return
    self.video_scripts_listbox.delete(0, tk.END)
    for path in self._get_video_scripts():
        name = os.path.basename(path)
        exists = os.path.isfile(path)
        mark = "" if exists else " ⚠ "
        self.video_scripts_listbox.insert(tk.END, f"{mark}{name}  —  {path}")


def add_video_script(self):
    path = filedialog.askopenfilename(
        title="Выберите Python-скрипт",
        filetypes=[("Python", "*.py"), ("Все файлы", "*.*")]
    )
    if not path:
        return
    path = os.path.abspath(path)
    if not path.lower().endswith('.py'):
        messagebox.showerror("Ошибка", "Нужен файл с расширением .py")
        return
    scripts = self._get_video_scripts()
    if path in scripts:
        messagebox.showinfo("Уже добавлен", "Этот скрипт уже есть в списке")
        return
    scripts.append(path)
    self._save_video_scripts(scripts)
    self._reload_video_scripts_list()
    self.set_status(f"Добавлен скрипт: {os.path.basename(path)}")


def remove_video_script(self):
    sel = self.video_scripts_listbox.curselection()
    if not sel:
        messagebox.showwarning("Внимание", "Выберите скрипт для удаления")
        return
    idx = sel[0]
    scripts = self._get_video_scripts()
    if idx >= len(scripts):
        return
    removed = scripts.pop(idx)
    self._save_video_scripts(scripts)
    self._reload_video_scripts_list()
    self.set_status(f"Удалён: {os.path.basename(removed)}")


def start_video_script(self):
    if self.video_process is not None and self.video_process.poll() is None:
        messagebox.showwarning("Занято", "Уже выполняется скрипт. Сначала остановите его.")
        return

    sel = self.video_scripts_listbox.curselection()
    if not sel:
        messagebox.showwarning("Внимание", "Выберите скрипт из списка")
        return

    scripts = self._get_video_scripts()
    idx = sel[0]
    if idx >= len(scripts):
        return
    script_path = scripts[idx]

    if not os.path.isfile(script_path):
        messagebox.showerror("Ошибка", f"Файл не найден:\n{script_path}")
        return

    self.video_stop_flag = False
    self.video_start_btn.config(state=tk.DISABLED)
    self.video_stop_btn.config(state=tk.NORMAL)
    self.video_progress.config(mode='indeterminate')
    self.video_progress.start(12)
    self.video_status_label.config(text=f"Запуск: {os.path.basename(script_path)}")

    self._append_video_log(f"{'=' * 50}")
    self._append_video_log(f"▶ {script_path}")
    self._append_video_log(f"{'=' * 50}")

    self.video_thread = threading.Thread(
        target=self._run_video_script_thread,
        args=(script_path,),
        daemon=True
    )
    self.video_thread.start()


def _run_video_script_thread(self, script_path):
    try:
        cwd = os.path.dirname(script_path) or None
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)

        self.video_process = subprocess.Popen(
            [sys.executable, '-u', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=cwd,
            bufsize=1,
            creationflags=creationflags
        )

        assert self.video_process.stdout is not None
        for line in self.video_process.stdout:
            if self.video_stop_flag:
                break
            line = line.rstrip('\n\r')
            if line:
                self.root.after(0, self._append_video_log, line)

        if not self.video_stop_flag and self.video_process.poll() is None:
            try:
                self.video_process.wait(timeout=5)
            except Exception:
                pass

        code = self.video_process.poll()
        if self.video_stop_flag:
            self.root.after(0, self._video_script_stopped)
        elif code == 0:
            self.root.after(0, self._video_script_finished, True, code)
        else:
            self.root.after(0, self._video_script_finished, False, code)

    except Exception as e:
        self.root.after(0, self._append_video_log, f"❌ Ошибка запуска: {e}")
        self.root.after(0, self._video_script_finished, False, -1)
    finally:
        self.video_process = None


def stop_video_script(self):
    self.video_stop_flag = True
    proc = self.video_process
    if proc is None or proc.poll() is not None:
        self._video_script_stopped()
        return

    self._append_video_log("⏹ Остановка процесса...")
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            self._append_video_log("⚠️ Процесс принудительно завершён (kill)")
    except Exception as e:
        self._append_video_log(f"⚠️ Ошибка остановки: {e}")
        try:
            proc.kill()
        except Exception:
            pass

    self._video_script_stopped()


def _video_script_finished(self, ok, code):
    self.video_progress.stop()
    self.video_progress.config(mode='determinate', value=100 if ok else 0)
    self.video_start_btn.config(state=tk.NORMAL)
    self.video_stop_btn.config(state=tk.DISABLED)
    if ok:
        self.video_status_label.config(text="Готово (код 0)")
        self._append_video_log("✅ Скрипт завершён успешно")
        self.set_status("Видео-скрипт завершён")
    else:
        self.video_status_label.config(text=f"Завершён с кодом {code}")
        self._append_video_log(f"❌ Скрипт завершён с кодом {code}")
        self.set_status(f"Видео-скрипт: код {code}")


def _video_script_stopped(self):
    self.video_progress.stop()
    self.video_progress.config(mode='determinate', value=0)
    self.video_start_btn.config(state=tk.NORMAL)
    self.video_stop_btn.config(state=tk.DISABLED)
    self.video_status_label.config(text="Остановлено")
    self._append_video_log("⏹ Остановлено пользователем")
    self.set_status("Видео-скрипт остановлен")


def _append_video_log(self, message):
    if not hasattr(self, 'video_log') or self.video_log is None:
        return
    try:
        self.video_log.config(state=tk.NORMAL)
        self.video_log.insert(tk.END, message + "\n")
        self.video_log.see(tk.END)
        self.video_log.config(state=tk.DISABLED)
    except Exception:
        pass


def start_video_creation(self):
    self.start_video_script()


def stop_video_creation(self):
    self.stop_video_script()


def select_video_input_folder(self):
    pass


def select_video_output_folder(self):
    pass


def install_video_scripts(app_cls):
    """Подменяет вкладку Видео на менеджер внешних скриптов."""
    app_cls.create_video_tab = create_video_tab
    app_cls._get_video_scripts = _get_video_scripts
    app_cls._save_video_scripts = _save_video_scripts
    app_cls._reload_video_scripts_list = _reload_video_scripts_list
    app_cls.add_video_script = add_video_script
    app_cls.remove_video_script = remove_video_script
    app_cls.start_video_script = start_video_script
    app_cls._run_video_script_thread = _run_video_script_thread
    app_cls.stop_video_script = stop_video_script
    app_cls._video_script_finished = _video_script_finished
    app_cls._video_script_stopped = _video_script_stopped
    app_cls._append_video_log = _append_video_log
    app_cls.start_video_creation = start_video_creation
    app_cls.stop_video_creation = stop_video_creation
    app_cls.select_video_input_folder = select_video_input_folder
    app_cls.select_video_output_folder = select_video_output_folder
    return app_cls
