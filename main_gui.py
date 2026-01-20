# main_gui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import re

from fun_class_logic import run_fun_class
from normal_full_logic import run_normal_full
from normal_logic import run_normal_class


class XKHelperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("西电选课脚本")
        self.root.geometry("650x850")  # 稍微增高以容纳新控件

        self.create_paste_parse_section()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        self.tab3 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="普通/体育自动选课")
        self.notebook.add(self.tab2, text="普通/体育补选监控")
        self.notebook.add(self.tab3, text="通识选修补选监控")

        # 全局配置变量
        self.global_ua = tk.StringVar(value="UA")
        self.global_lang = tk.StringVar(value="Languaga")
        self.global_batch = tk.StringVar(value="Batch")
        self.global_cookie = tk.StringVar(value="cookie")

        self.create_normal_tab()
        self.create_full_tab()
        self.create_fun_tab()

        self.log_text = scrolledtext.ScrolledText(root, height=10)
        self.log_text.pack(fill='both', padx=10, pady=(0, 10))
        self.running = False
        self.stop_flag = lambda: not self.running

        self.task_active = False  # 标记是否有任务正在运行（用于 UI 控制）

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def _create_polling_controls_normal(self, parent, try_times_var, between_time_var):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=5)
        # 轮询次数
        ttk.Label(frame, text="尝试次数：").pack(side='left')
        try_entry = ttk.Entry(frame, textvariable=try_times_var, width=8)
        try_entry.pack(side='left', padx=(5, 15))
        try_entry.bind("<FocusIn>", lambda e: self._clear_placeholder_int(try_times_var, "2"))
        try_entry.bind("<FocusOut>", lambda e: self._restore_placeholder_int(try_times_var, "2"))
        # 轮询间隔
        ttk.Label(frame, text="轮询间隔（秒）：").pack(side='left')
        time_entry = ttk.Entry(frame, textvariable=between_time_var, width=8)
        time_entry.pack(side='left', padx=(5, 0))
        time_entry.bind("<FocusIn>", lambda e: self._clear_placeholder_float(between_time_var, "1"))
        time_entry.bind("<FocusOut>", lambda e: self._restore_placeholder_float(between_time_var, "1"))

    def _create_polling_controls_abnormal(self, parent, try_times_var, between_time_var):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=5)
        # 轮询间隔
        ttk.Label(frame, text="轮询间隔（秒）：").pack(side='left')
        time_entry = ttk.Entry(frame, textvariable=between_time_var, width=8)
        time_entry.pack(side='left', padx=(5, 0))
        time_entry.bind("<FocusIn>", lambda e: self._clear_placeholder_float(between_time_var, "5"))
        time_entry.bind("<FocusOut>", lambda e: self._restore_placeholder_float(between_time_var, "5"))


    def _clear_placeholder_int(self, var, placeholder):
        if var.get() == placeholder:
            var.set("")

    def _restore_placeholder_int(self, var, placeholder):
        val = var.get().strip()
        if not val.isdigit():
            var.set(placeholder)

    def _clear_placeholder_float(self, var, placeholder):
        if var.get() == placeholder:
            var.set("")

    def _restore_placeholder_float(self, var, placeholder):
        val = var.get().strip()
        # 允许空、整数、小数
        if val == "":
            var.set(placeholder)
        else:
            try:
                float(val)
            except ValueError:
                var.set(placeholder)

    # ==================== 【新增】最顶部：粘贴解析区 ====================
    def create_paste_parse_section(self):
        paste_frame = ttk.LabelFrame(self.root, text="📌 粘贴完整配置字符串（可选）")
        paste_frame.pack(fill='x', padx=10, pady=(10, 5))

        self.paste_var = tk.StringVar()
        entry = ttk.Entry(paste_frame, textvariable=self.paste_var, width=100)
        entry.pack(fill='x', padx=5, pady=5)
        btn = ttk.Button(paste_frame, text="自动解析并填充全局配置", command=self.parse_and_fill)
        btn.pack(pady=(0, 5))

    def parse_and_fill(self):
        text = self.paste_var.get().strip()
        if not text:
            messagebox.showwarning("提示", "请先粘贴配置字符串！")
            return

        ua_match = re.search(r'UserAgentTypeIn\s*=\s*"([^"]+)"', text)
        lang_match = re.search(r'AcceptLanguage\s*=\s*"([^"]+)"', text)
        batch_match = re.search(r'BatchID\s*=\s*"([^"]+)"', text)
        cookie_match = re.search(r'CookieIsHere\s*=\s*"([^"]+)"', text)

        updated = False
        if ua_match:
            self.global_ua.set(ua_match.group(1))
            updated = True
        if lang_match:
            self.global_lang.set(lang_match.group(1))
            updated = True
        if batch_match:
            self.global_batch.set(batch_match.group(1))
            updated = True
        if cookie_match:
            self.global_cookie.set(cookie_match.group(1))
            updated = True

        if updated:
            messagebox.showinfo("成功", "全局配置已自动填充！")
            self.paste_var.set("")  # 清空粘贴框
        else:
            messagebox.showwarning("警告", "未识别到有效字段，请检查格式是否匹配：\nUserAgentTypeIn=\"...\"\nAcceptLanguage=\"...\"\nBatchID=\"...\"\nCookieIsHere=\"...\"")

    # ==================== 普通课 Tab（支持增删） ====================
    def create_normal_tab(self):
        frame = self.tab1
        self._create_global_inputs(frame)

        # 轮询参数
        self.normal_try = tk.StringVar(value="2")
        self.normal_between = tk.StringVar(value="1")
        self._create_polling_controls_normal(frame, self.normal_try, self.normal_between)

        # >>> 定时启动功能 <<<
        self.normal_set_time = tk.IntVar(value=0)  # 0 = 关闭, 1 = 启用
        time_frame = ttk.LabelFrame(frame, text="🕒 定时启动（可选）")
        time_frame.pack(fill='x', padx=5, pady=5)

        check_btn = ttk.Checkbutton(
            time_frame,
            text="启用定时启动（到达指定时间自动开始）",
            variable=self.normal_set_time,
            command=self.toggle_time_inputs
        )
        check_btn.pack(anchor='w', padx=5, pady=5)

        # 时间输入容器
        self.time_input_frame = ttk.Frame(time_frame)
        self.time_input_frame.pack(fill='x', padx=10, pady=(0, 10))
        self.time_input_frame.pack_forget()  # 初始隐藏

        # 时分秒输入
        self.target_hour = tk.StringVar(value="09")
        self.target_minute = tk.StringVar(value="00")
        self.target_second = tk.StringVar(value="00")

        time_row = ttk.Frame(self.time_input_frame)
        time_row.pack()
        ttk.Label(time_row, text="目标时间：").pack(side='left')
        ttk.Entry(time_row, textvariable=self.target_hour, width=5).pack(side='left', padx=(5, 2))
        ttk.Label(time_row, text="时").pack(side='left')
        ttk.Entry(time_row, textvariable=self.target_minute, width=5).pack(side='left', padx=(5, 2))
        ttk.Label(time_row, text="分").pack(side='left')
        ttk.Entry(time_row, textvariable=self.target_second, width=5).pack(side='left', padx=(5, 2))
        ttk.Label(time_row, text="秒").pack(side='left')

        # 课程区域
        course_frame = ttk.LabelFrame(frame, text="课程列表（可添加多门）")
        course_frame.pack(fill='x', pady=10, padx=5)

        self.normal_courses = []
        self.course_container = ttk.Frame(course_frame)
        self.course_container.pack(fill='x', padx=5, pady=5)

        btn_frame = ttk.Frame(course_frame)
        btn_frame.pack(fill='x', pady=5)
        ttk.Button(btn_frame, text="添加课程", command=self.add_normal_course).pack(side='left')
        ttk.Button(btn_frame, text="清空所有课程", command=self.clear_normal_courses).pack(side='left', padx=(5, 0))

        btn_frame_actions = ttk.Frame(frame)
        btn_frame_actions.pack(pady=10)

        self.normal_start_btn = ttk.Button(btn_frame_actions, text="开始抢课", command=self.start_normal)
        self.normal_start_btn.pack(side='left', padx=(0, 5))

        self.normal_stop_btn = ttk.Button(btn_frame_actions, text="停止抢课", command=self.stop_task, state='disabled')
        self.normal_stop_btn.pack(side='left')

    def toggle_time_inputs(self):
        if self.normal_set_time.get() == 1:
            self.time_input_frame.pack()
        else:
            self.time_input_frame.pack_forget()

    def add_normal_course(self):
        idx = len(self.normal_courses) + 1
        course_frame = ttk.Frame(self.course_container)
        course_frame.pack(fill='x', pady=2)

        campus_var = tk.StringVar(value="S")
        type_var = tk.StringVar(value="TJKC")
        key_var = tk.StringVar(value="请输入课程关键词")

        row = ttk.Frame(course_frame)
        row.pack(fill='x')

        ttk.Label(row, text=f"课程{idx} 校区：").pack(side='left')
        ttk.Entry(row, textvariable=campus_var, width=5).pack(side='left', padx=(5, 5))

        ttk.Label(row, text="类型：").pack(side='left')
        ttk.Entry(row, textvariable=type_var, width=12).pack(side='left', padx=(5, 5))

        ttk.Label(row, text="关键词：").pack(side='left')
        entry_key = ttk.Entry(row, textvariable=key_var, width=25)
        entry_key.pack(side='left', padx=(5, 5))

        # 删除按钮
        del_btn = ttk.Button(row, text="删除", command=lambda f=course_frame, c=(campus_var, type_var,
                                                                                 key_var): self.remove_normal_course(f,
                                                                                                                     c))
        del_btn.pack(side='right')

        # 绑定焦点事件
        entry_key.bind("<FocusIn>", lambda e, v=key_var: self._clear_placeholder(v, "请输入课程关键词"))
        entry_key.bind("<FocusOut>", lambda e, v=key_var: self._restore_placeholder(v, "请输入课程关键词"))

        self.normal_courses.append({
            "frame": course_frame,
            "campus_var": campus_var,
            "type_var": type_var,
            "key_var": key_var
        })

    def remove_normal_course(self, frame, vars_tuple):
        frame.destroy()
        self.normal_courses = [c for c in self.normal_courses if c["frame"] != frame]

    def clear_normal_courses(self):
        for c in self.normal_courses:
            c["frame"].destroy()
        self.normal_courses.clear()

    def stop_task(self):
        if self.task_active:
            self.log("正在请求停止任务...")
            self.running = False  # 触发 stop_flag
            # 注意：不要在这里恢复按钮！等 _mark_task_finished 统一处理

    def _update_all_start_buttons(self, state):
        for btn in [self.normal_start_btn, self.full_start_btn, self.fun_start_btn]:
            if hasattr(btn, 'config'):
                btn.config(state=state)

    def _update_all_stop_buttons(self, state):
        for btn in [self.normal_stop_btn, self.full_stop_btn, self.fun_stop_btn]:
            if hasattr(btn, 'config'):
                btn.config(state=state)

    def start_normal(self):
        if self.running:
            messagebox.showwarning("警告", "已在运行中！")
            return

        # 验证课程
        courses = []
        for c in self.normal_courses:
            key = c["key_var"].get().strip()
            if key and key != "请输入课程关键词":
                courses.append({
                    "campus": c["campus_var"].get().strip() or "S",  # 默认 S
                    "teachingClassType": c["type_var"].get(),
                    "KEY": key,
                    "clazzType": c["type_var"].get()
                })
        if not courses:
            messagebox.showwarning("警告", "请至少添加一门有效课程！")
            return

        # 验证轮询参数
        try:
            try_times = int(self.normal_try.get())
            between_time = float(self.normal_between.get())
            if try_times <= 0:
                messagebox.showerror("错误", "尝试次数必须为正整数！")
                return
            if between_time <= 0:
                messagebox.showerror("错误", "轮询间隔必须为大于 0 的正数（可为小数，如 0.5）！")
                return
        except ValueError as e:
            # 捕获 int/float 转换失败
            messagebox.showerror("错误", "请确保尝试次数为整数，轮询间隔为有效数字！")
            return

        config = {
            "UserAgent": self.global_ua.get(),
            "AcceptLanguage": self.global_lang.get(),
            "BatchID": self.global_batch.get(),
            "Cookie": self.global_cookie.get(),
            "campus": "S",
            "TryTimes": try_times,
            "BetweenTime": between_time,
            "courses": courses,
            "SetTimeAndStart": self.normal_set_time.get()
        }

        if config["SetTimeAndStart"] == 1:
            try:
                h = int(self.target_hour.get())
                m = int(self.target_minute.get())
                s = int(self.target_second.get())
                if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
                    raise ValueError
                config["target_hour"] = h
                config["target_minute"] = m
                config["target_second"] = s
            except:
                messagebox.showerror("错误", "请正确设置目标时间（时:0-23, 分/秒:0-59）！")
                return

        if self.task_active:
            messagebox.showwarning("警告", "已有任务正在运行，请先停止或等待其结束。")
            return

        self.clear_log()
        self.running = True
        self.task_active = True  # ← 新增
        self._update_all_start_buttons('disabled')
        self._update_all_stop_buttons('normal')
        threading.Thread(
            target=self._run_task_with_cleanup,
            args=(run_normal_class, config),
            daemon=True
        ).start()

    # ==================== 补选 & 通识 Tab（保持不变，略作简化） ====================
    def create_full_tab(self):
        frame = self.tab2
        self._create_global_inputs(frame)

        self.full_try = tk.StringVar(value="1000")
        self.full_between = tk.StringVar(value="5")
        self._create_polling_controls_abnormal(frame, self.full_try, self.full_between)

        self._create_single_course_ui(frame, attr_prefix="full", title="监控课程", start_cmd=self.start_full)

        btn_frame_actions = ttk.Frame(frame)
        btn_frame_actions.pack(pady=10)

        self.full_start_btn = ttk.Button(btn_frame_actions, text="开始监控", command=self.start_full)
        self.full_start_btn.pack(side='left', padx=(0, 5))

        self.full_stop_btn = ttk.Button(btn_frame_actions, text="停止监控", command=self.stop_task, state='disabled')
        self.full_stop_btn.pack(side='left')

    def create_fun_tab(self):
        frame = self.tab3
        self._create_global_inputs(frame)

        self.fun_try = tk.StringVar(value="1000")
        self.fun_between = tk.StringVar(value="5")
        self._create_polling_controls_abnormal(frame, self.fun_try, self.fun_between)

        self._create_single_course_ui(frame, attr_prefix="fun", title="通识课程", start_cmd=self.start_fun)

        btn_frame_actions = ttk.Frame(frame)
        btn_frame_actions.pack(pady=10)

        self.fun_start_btn = ttk.Button(btn_frame_actions, text="开始监控", command=self.start_fun)
        self.fun_start_btn.pack(side='left', padx=(0, 5))

        self.fun_stop_btn = ttk.Button(btn_frame_actions, text="停止监控", command=self.stop_task, state='disabled')
        self.fun_stop_btn.pack(side='left')

    def _create_single_course_ui(self, parent, attr_prefix, title, start_cmd):
        course_frame = ttk.LabelFrame(parent, text=title)
        course_frame.pack(fill='x', pady=10, padx=5)

        campus_var = tk.StringVar(value="S")
        type_var = tk.StringVar(value="TJKC" if attr_prefix != "fun" else "XGKC")  # ← Fun tab 默认 XGKC
        key_var = tk.StringVar()

        self.__dict__[f"{attr_prefix}_campus"] = campus_var
        self.__dict__[f"{attr_prefix}_type"] = type_var
        self.__dict__[f"{attr_prefix}_key"] = key_var

        row = ttk.Frame(course_frame)
        row.pack(fill='x', padx=5, pady=5)

        ttk.Label(row, text="校区：").pack(side='left')
        ttk.Entry(row, textvariable=campus_var, width=5).pack(side='left', padx=(5, 5))

        ttk.Label(row, text="课程类型：").pack(side='left')
        ttk.Entry(row, textvariable=type_var, width=15).pack(side='left', padx=(5, 10))

        placeholder = "请输入课程关键词"
        if attr_prefix == "fun":
            placeholder = "请输入通识课关键词"
        key_var.set(placeholder)

        ttk.Label(row, text="关键词：").pack(side='left')
        entry_key = ttk.Entry(row, textvariable=key_var, width=30)
        entry_key.pack(side='left', padx=(5, 0))

        entry_key.bind("<FocusIn>", lambda e, v=key_var, ph=placeholder: self._clear_placeholder(v, ph))
        entry_key.bind("<FocusOut>", lambda e, v=key_var, ph=placeholder: self._restore_placeholder(v, ph))

    def start_full(self):
        self._start_single_monitor("full")

    def start_fun(self):
        self._start_single_monitor("fun")

    def _start_single_monitor(self, prefix):
        key = self.__dict__[f"{prefix}_key"].get().strip()
        placeholder = "请输入课程关键词"
        if prefix == "fun":
            placeholder = "请输入通识课关键词"
        if key == placeholder or not key:
            messagebox.showwarning("警告", "请输入有效的课程关键词！")
            return
        if self.running:
            messagebox.showwarning("警告", "已在运行中！")
            return

        try:
            try_times = int(self.__dict__[f"{prefix}_try"].get())
            between_time = float(self.__dict__[f"{prefix}_between"].get())
            if try_times <= 0:
                messagebox.showerror("错误", "尝试次数必须为正整数！")
                return
            if between_time <= 0:
                messagebox.showerror("错误", "轮询间隔必须为大于 0 的正数（可为小数，如 0.5）！")
                return
        except ValueError:
            messagebox.showerror("错误", "请确保尝试次数为整数，轮询间隔为有效数字！")
            return

        config = {
            "UserAgent": self.global_ua.get(),
            "AcceptLanguage": self.global_lang.get(),
            "BatchID": self.global_batch.get(),
            "Cookie": self.global_cookie.get(),
            "campus": (self.__dict__[f"{prefix}_campus"].get().strip() or "S"),  # ← 新增 campus
            "teachingClassType": self.__dict__[f"{prefix}_type"].get(),
            "KEY": key,
            "ClazzType": self.__dict__[f"{prefix}_type"].get(),
            "TryTimes": try_times,
            "BetweenTime": between_time,
            "SetTimeAndStart": 0
        }

        if self.task_active:
            messagebox.showwarning("警告", "已有任务正在运行，请先停止或等待其结束。")
            return

        self.clear_log()
        self.running = True
        self.task_active = True
        self._update_all_start_buttons('disabled')
        self._update_all_stop_buttons('normal')

        target = run_normal_full if prefix == "full" else run_fun_class
        threading.Thread(target=self._run_task_with_cleanup, args=(target, config), daemon=True).start()

    # ==================== 公共UI组件 ====================
    def _create_global_inputs(self, parent):
        global_frame = ttk.LabelFrame(parent, text="🌐 全局配置（UA / AcceptLanguage / BatchID / Cookie）")
        global_frame.pack(fill='x', padx=5, pady=5)

        fields = [
            ("User-Agent:", self.global_ua),
            ("Accept-Language:", self.global_lang),
            ("BatchID:", self.global_batch),
            ("Cookie:", self.global_cookie),
        ]

        for label_text, var in fields:
            row = ttk.Frame(global_frame)
            row.pack(fill='x', padx=5, pady=2)
            ttk.Label(row, text=label_text, width=15, anchor='w').pack(side='left')
            entry = ttk.Entry(row, textvariable=var, width=80)
            entry.pack(side='left', fill='x', expand=True, padx=(5, 0))

    def _clear_placeholder(self, var, placeholder):
        if var.get() == placeholder:
            var.set("")

    def _restore_placeholder(self, var, placeholder):
        if not var.get().strip():
            var.set(placeholder)

    def _mark_task_finished(self):
        """标记任务结束，并恢复 UI"""
        self.task_active = False
        self.running = False  # 确保 stop_flag 返回 True
        self._update_all_start_buttons(state='normal')
        self._update_all_stop_buttons(state='disabled')

    def _run_task_with_cleanup(self, target_func, config):
        """运行任务，并在结束后自动恢复按钮"""
        try:
            target_func(config, self.log, self.stop_flag)
        finally:
            # 无论成功/失败/停止，任务已结束
            self.root.after(0, self._mark_task_finished)

    def _restore_buttons_after_task(self):
        """恢复所有开始/停止按钮的状态"""
        if not self.running:  # 只有在非运行状态才恢复（防止冲突）
            self._update_all_start_buttons(state='normal')
            self._update_all_stop_buttons(state='disabled')


if __name__ == "__main__":
    root = tk.Tk()
    app = XKHelperApp(root)
    root.mainloop()