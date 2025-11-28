import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import json
import os
import zipfile
import shutil
from datetime import datetime
import requests
# 导入用于处理Markdown的库
import re

class OPAIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OnPython AI (OPAI)")
        self.root.geometry("800x600")

        # 主题配置
        self.is_dark_theme = False

        # 配置文件路径
        self.config_file = "config.json"
        self.data_dir = "data"
        self.onpython_dir = os.path.join(self.data_dir, "OnPython")

        # 记忆库存储路径
        self.memory_dir = os.path.join(self.data_dir, "Memory")
        self.short_term_memory_file = os.path.join(self.memory_dir, "short_term_memory.json")
        self.long_term_memory_file = os.path.join(self.memory_dir, "long_term_memory.json")
        self.memory = {
            "programs": {},  # 已导入的程序
            "summaries": []  # 对话总结
        }

        # 加载配置
        self.config = self.load_config()

        # 检查是否启用暗色主题
        self.is_dark_theme = self.config.get("dark_theme", False)

        # 初始化记忆库
        self.load_memory()

        # 初始化对话历史记录
        self.conversation_history = []

        # 初始化上下文消息列表（用于API调用）
        self.context_messages = [
            {"role": "system", "content": self.config["system_prompt"]}
        ]

        # 创建主界面
        self.create_widgets()

    def get_theme_colors(self):
        """获取当前主题的颜色方案"""
        if self.is_dark_theme:
            return {
                "bg": "#2d2d2d",
                "fg": "#ffffff",
                "text_bg": "#1e1e1e",
                "text_fg": "#dcdcdc",
                "input_bg": "#3c3c3c",
                "input_fg": "#ffffff",
                "button_bg": "#3c3c3c",
                "button_fg": "#ffffff",
                "highlight_bg": "#4d4d4d",
                "highlight_fg": "#ffffff",
                "system_fg": "#4ec9b0",  # 青色
                "user_fg": "#9cdcfe",    # 浅蓝色
                "ai_fg": "#dcdcaa",      # 浅黄色
                "timestamp_fg": "#57a64a" # 绿色
            }
        else:
            return {
                "bg": "#f0f0f0",
                "fg": "#000000",
                "text_bg": "#ffffff",
                "text_fg": "#000000",
                "input_bg": "#ffffff",
                "input_fg": "#000000",
                "button_bg": "#e0e0e0",
                "button_fg": "#000000",
                "highlight_bg": "#d9d9d9",
                "highlight_fg": "#000000",
                "system_fg": "#008000",  # 深绿色
                "user_fg": "#0000ff",    # 蓝色
                "ai_fg": "#000000",      # 黑色
                "timestamp_fg": "#808080" # 灰色
            }

    def apply_theme(self):
        """应用当前主题到UI组件"""
        colors = self.get_theme_colors()

        # 应用到聊天显示区域
        self.chat_display.config(
            bg=colors["text_bg"],
            fg=colors["text_fg"],
            insertbackground=colors["fg"],  # 光标颜色
            selectbackground=colors["highlight_bg"],
            selectforeground=colors["highlight_fg"]
        )

        # 应用到输入区域
        self.user_input.config(
            bg=colors["input_bg"],
            fg=colors["input_fg"],
            insertbackground=colors["fg"],
            selectbackground=colors["highlight_bg"],
            selectforeground=colors["highlight_fg"]
        )

        # 设置窗口背景色（对于非ttk组件）
        self.root.config(bg=colors["bg"])

        # 应用到Frame组件（通过重新创建或更新）
        self.chat_frame.config()  # ttk组件主要受系统主题影响
        self.input_frame.config()

    def detect_system_theme(self):
        """检测系统主题"""
        try:
            # 尝试导入winreg来检测Windows系统主题
            import winreg
            # 检查注册表项来确定Windows主题
            reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path)

            # AppsUseLightTheme值：1为浅色，0为深色
            value, _ = winreg.QueryValueEx(reg_key, "AppsUseLightTheme")
            winreg.CloseKey(reg_key)

            # 如果值为0，表示使用深色主题
            return value == 0
        except:
            # 如果无法检测系统主题，返回默认值（浅色）
            return False
    
    def create_widgets(self):
        """创建主界面组件"""
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导入 .opai 文件", command=self.import_opai_file)
        file_menu.add_command(label="清除对话上下文", command=self.clear_context)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 创建对话记录框
        self.chat_frame = ttk.Frame(self.root)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.chat_display = scrolledtext.ScrolledText(
            self.chat_frame, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=("微软雅黑", 10)
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # 创建输入区域
        self.input_frame = ttk.Frame(self.root)
        self.input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 聊天输入框
        self.user_input = tk.Text(
            self.input_frame, 
            height=3,
            font=("微软雅黑", 10)
        )
        self.user_input.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))
        self.user_input.bind("<Return>", self.handle_enter_key)
        
        # 发送/停止按钮
        self.send_button = ttk.Button(
            self.input_frame,
            text="发送",
            command=self.send_message
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # 设置按钮
        self.settings_button = ttk.Button(
            self.input_frame,
            text="设置",
            command=self.open_settings
        )
        self.settings_button.pack(side=tk.RIGHT, padx=(0, 5))

        # 应用主题
        self.apply_theme()
        
        # 显示欢迎信息
        self.display_message("欢迎", "欢迎使用OnPython AI (OPAI)！我可以让AI帮助您编写程序、执行系统命令，或与您聊天。")
        
        # 启动记忆库定期总结任务
        self.start_memory_summarization()
    
    def clear_context(self):
        """清除对话上下文，开始新的对话"""
        # 保留系统提示词，清除用户和AI的消息
        system_prompt = self.config["system_prompt"]
        self.context_messages = [{"role": "system", "content": system_prompt}]
        self.display_message("系统", "对话上下文已清除，现在开始新的对话。")
    
    def import_opai_file(self):
        """导入 .opai 文件"""
        file_path = filedialog.askopenfilename(
            title="选择 .opai 文件",
            filetypes=[("OPAI files", "*.opai"), ("All files", "*.*")]
        )
        
        if not file_path:
            return  # 用户取消了选择
        
        try:
            self.process_opai_file(file_path)
        except Exception as e:
            messagebox.showerror("错误", f"导入 .opai 文件失败: {str(e)}")
    
    def process_opai_file(self, file_path):
        """处理 .opai 文件"""
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            # 获取所有文件名
            file_list = zip_file.namelist()
            
            # 查找 com.txt 文件 (根据规范，应该是 "程序名字"com.txt 格式)
            com_files = [f for f in file_list if f.endswith('com.txt')]
            
            if not com_files:
                raise FileNotFoundError("未在 .opai 文件中找到 com.txt 文件")
            
            # 使用第一个找到的 com.txt 文件
            com_file = com_files[0]
            
            # 提取并读取 com.txt 文件内容
            with zip_file.open(com_file) as txt_file:
                content = txt_file.read().decode('utf-8')
            
            # 提取程序名称 (从文件名中获取，去除 "com.txt")
            program_name = com_file.replace('com.txt', '').split('/')[-1]  # 获取文件名部分
            
            # 显示导入信息
            self.display_message("系统", f"正在导入程序: {program_name}")
            self.display_message("系统", f"命令行用法:\n{content}")
            
            # 复制 .py 或 .exe 文件到 data/OnPython 目录
            for file_name in file_list:
                if file_name.lower().endswith(('.py', '.exe')):
                    # 提取文件名
                    actual_file_name = file_name.split('/')[-1]
                    
                    # 创建目标路径
                    target_path = os.path.join(self.onpython_dir, actual_file_name)
                    
                    # 从压缩包中提取文件到目标路径
                    with zip_file.open(file_name) as source_file:
                        with open(target_path, 'wb') as target_file:
                            target_file.write(source_file.read())
                    
                    self.display_message("系统", f"已将 {actual_file_name} 复制到 {self.onpython_dir} 目录")
            
            # 将程序信息保存到记忆库
            self.memory["programs"][program_name] = {
                "name": program_name,
                "usage": content,
                "location": self.onpython_dir,
                "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 保存记忆库
            self.save_memory()
            
            self.display_message("系统", f"程序 {program_name} 导入完成，并已记录到记忆库中！")
    
    def start_memory_summarization(self):
        """启动记忆库定期总结任务"""
        # 使用配置文件中的对话保存时间间隔
        save_interval_minutes = self.config.get("conversation_save_interval", 30)  # 默认30分钟
        save_interval_ms = save_interval_minutes * 60 * 1000  # 转换为毫秒
        self.root.after(save_interval_ms, self.create_memory_summary)

        # 启动记忆库整理任务
        self.start_memory整理()

    def start_memory整理(self):
        """启动记忆库定期整理任务"""
        # 使用配置文件中的记忆整理时间间隔
        整理_interval_minutes = self.config.get("memory整理_interval", 60)  # 默认60分钟
        整理_interval_ms = 整理_interval_minutes * 60 * 1000  # 转换为毫秒
        self.root.after(整理_interval_ms, self.整理_memory)

    def 整理_memory(self):
        """整理短期记忆，使用AI来评估重要性并保存到长期记忆库"""
        # 分析对话历史，提取信息供AI评估
        reference_conversations = self.extract_important_conversations()

        if reference_conversations:
            # 使用AI来判断哪些对话是重要的，需要保存到长期记忆
            self.request_ai_memory_evaluation(reference_conversations)
        else:
            print("没有足够的对话历史来进行记忆评估")

        print(f"记忆库整理完成，当前长期记忆库大小: {len(self.memory['long_term_memory'])}")

        # 继续安排下一次整理任务（使用新配置的时间间隔）
        # 重新计算时间间隔以确保使用最新配置
        整理_interval_minutes = self.config.get("memory整理_interval", 60)  # 重新获取当前配置
        整理_interval_ms = 整理_interval_minutes * 60 * 1000
        self.root.after(整理_interval_ms, self.整理_memory)  # 重新安排任务

    def request_ai_memory_evaluation(self, reference_conversations):
        """请求AI评估哪些对话重要并需要保存到长期记忆"""
        # 构建AI请求，询问哪些对话是重要的
        memory_content = "请分析以下对话历史，识别出重要、有价值或需要长期记住的信息：\n\n"

        for idx, conv in enumerate(reference_conversations, 1):
            memory_content += f"{idx}. [{conv['timestamp']}] {conv['sender']}: {conv['message']}\n"

        memory_content += "\n请识别并总结出重要信息，这些信息应该具有长期价值，比如：\n"
        memory_content += "- 个人偏好和喜好\n"
        memory_content += "- 重要的事实和数据\n"
        memory_content += "- 重要的承诺或约定\n"
        memory_content += "- 技术知识和解决方案\n"
        memory_content += "- 重要的人生事件或经验\n\n"
        memory_content += "请按照JSON格式返回重要信息，格式如下：\n"
        memory_content += "[\n"
        memory_content += "  {\n"
        memory_content += "    \"content\": \"重要信息内容\",\n"
        memory_content += "    \"tags\": [\"标签1\", \"标签2\"]\n"
        memory_content += "  }\n"
        memory_content += "]"

        # 创建一个临时的消息列表用于API请求
        temp_messages = [
            {"role": "system", "content": self.config["system_prompt"]},
            {"role": "user", "content": memory_content}
        ]

        # 检查配置是否完整
        if not self.config.get("api_url") or not self.config.get("api_key") or not self.config.get("model"):
            print("无法评估记忆：API配置不完整")
            return

        try:
            # 准备API请求
            headers = {"Content-Type": "application/json"}

            # 对于OpenAI API风格的服务，使用Bearer认证
            if "openai.com" in self.config["api_url"] or "api.openai.com" in self.config["api_url"]:
                headers["Authorization"] = f"Bearer {self.config['api_key']}"
            # 对于Azure OpenAI
            elif "azure.com" in self.config["api_url"] or "openai.azure.com" in self.config["api_url"]:
                headers["api-key"] = self.config['api_key']
            # 对于其他API服务
            else:
                headers["Authorization"] = f"Bearer {self.config['api_key']}"

            data = {
                "model": self.config["model"],
                "messages": temp_messages,
                "temperature": 0.3  # 较低的temperature以获得更准确的分析
            }

            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # 创建不使用系统代理的会话
            session = requests.Session()
            session.trust_env = False

            response = session.post(
                self.config["api_url"],
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                try:
                    ai_response = result["choices"][0]["message"]["content"]

                    # 尝试解析AI返回的JSON格式
                    import json as json_module
                    import re

                    # 查找JSON部分
                    json_match = re.search(r'```json\n(.*?)```', ai_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1).strip()
                    else:
                        # 如果没有找到代码块，尝试直接解析响应
                        json_str = ai_response.strip()

                    try:
                        important_items = json_module.loads(json_str)

                        # 将AI识别的重要信息添加到长期记忆库
                        for item in important_items:
                            content = item.get("content")
                            tags = item.get("tags", [])
                            if content:
                                self.add_to_long_term_memory(content, tags)

                    except json_module.JSONDecodeError:
                        print(f"无法解析AI记忆评估结果为JSON: {ai_response}")

                except (KeyError, IndexError):
                    print(f"无法从API响应中提取AI评估结果: {result}")
            else:
                print(f"AI记忆评估请求失败：{response.status_code} - {response.text}")

        except Exception as e:
            print(f"AI记忆评估过程中发生错误: {str(e)}")

    def extract_important_conversations(self):
        """从对话历史中提取重要对话，仅作为AI总结的参考"""
        # 这个函数现在只用于提供给AI进行总结的参考信息
        # 不再自动将信息添加到长期记忆库
        important_items = []

        # 获取最近的对话历史作为AI总结的参考
        # 限制为最近的50条记录以避免上下文过长
        recent_history = self.conversation_history[-50:] if len(self.conversation_history) > 50 else self.conversation_history

        for entry in recent_history:
            important_items.append({
                "timestamp": entry.get("timestamp"),
                "sender": entry.get("sender"),
                "message": entry.get("message"),
                "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        return important_items

    def add_to_long_term_memory(self, content, tags=None):
        """手动将重要信息添加到长期记忆库 - 只能通过AI总结或特殊指令调用"""
        if tags is None:
            tags = []

        # 创建长期记忆条目
        memory_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": content,
            "tags": tags,
            "added_by": "AI_Summary"  # 标记为AI总结添加
        }

        # 将条目添加到长期记忆库
        self.memory["long_term_memory"].append(memory_entry)

        # 保存记忆库（不再限制条目数量）
        self.save_memory()

        print(f"已将信息添加到长期记忆库: {content[:50]}...")

        return True

    def calculate_similarity(self, text1, text2):
        """计算两个文本之间的相似度（百分比）"""
        # 导入difflib库用于计算文本相似度
        import difflib

        # 计算相似度比率（0-1之间的浮点数）
        similarity_ratio = difflib.SequenceMatcher(None, text1, text2).ratio()

        # 转换为百分比
        similarity_percentage = similarity_ratio * 100

        return similarity_percentage

    def find_relevant_memory(self, user_input):
        """根据用户输入查找相关的长期记忆"""
        relevant_memories = []

        # 获取相似度阈值
        similarity_threshold = self.config.get("memory_similarity_threshold", 85)

        # 遍历长期记忆库中的所有记忆
        for memory_item in self.memory.get("long_term_memory", []):
            # 对于新格式的记忆项，使用 'content' 字段
            # 对于旧格式的记忆项，使用 'message' 字段
            memory_text = memory_item.get("content", memory_item.get("message", ""))

            # 计算用户输入与记忆的相似度
            similarity = self.calculate_similarity(user_input, memory_text)

            # 如果相似度超过阈值，则认为是相关记忆
            if similarity >= similarity_threshold:
                # 新格式的记忆项
                if "content" in memory_item:
                    relevant_memories.append({
                        "timestamp": memory_item.get("timestamp"),
                        "sender": memory_item.get("added_by", "Unknown"),
                        "message": memory_item.get("content"),
                        "similarity": similarity
                    })
                # 旧格式的记忆项
                else:
                    relevant_memories.append({
                        "timestamp": memory_item.get("timestamp"),
                        "sender": memory_item.get("sender"),
                        "message": memory_item.get("message"),
                        "similarity": similarity
                    })

        # 按相似度降序排序
        relevant_memories.sort(key=lambda x: x["similarity"], reverse=True)

        # 返回最相关的前5条记忆，避免上下文过长
        return relevant_memories[:5]

    def create_memory_summary(self):
        """创建记忆库总结"""
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 分析对话历史
        user_messages = [entry for entry in self.conversation_history if entry["sender"] == "用户"]
        ai_messages = [entry for entry in self.conversation_history if entry["sender"] == "AI"]
        system_messages = [entry for entry in self.conversation_history if entry["sender"] == "系统"]

        # 生成总结内容
        summary_content = f"定期总结 - {current_time}\n"
        summary_content += f"- 本次会话期间，用户发送了 {len(user_messages)} 条消息\n"
        summary_content += f"- AI回复了 {len(ai_messages)} 条消息\n"
        summary_content += f"- 系统发送了 {len(system_messages)} 条消息\n"
        summary_content += f"- 当前已导入 {len(self.memory['programs'])} 个程序到记忆库\n"
        summary_content += f"- 长期记忆库中包含 {len(self.memory['long_term_memory'])} 条重要信息\n"

        # 如果有用户消息，添加最近的几条
        if user_messages:
            summary_content += "- 最近的用户请求:\n"
            # 显示最近的3条用户消息
            recent_user_msgs = user_messages[-3:]
            for msg in recent_user_msgs:
                msg_preview = msg["message"][:50] + "..." if len(msg["message"]) > 50 else msg["message"]
                summary_content += f"  * {msg_preview}\n"

        # 创建总结条目
        summary = {
            "date": current_time,
            "type": "periodic_summary",
            "content": summary_content
        }

        # 添加到记忆库的总结列表
        self.memory["summaries"].append(summary)

        # 限制总结数量，只保留最近的10条
        if len(self.memory["summaries"]) > 10:
            self.memory["summaries"] = self.memory["summaries"][-10:]

        # 保存记忆库
        self.save_memory()

        # 显示提示信息（不直接显示在聊天窗口中，以免打扰用户）
        print(f"记忆库总结已创建于 {current_time}")

        # 继续设置下一次的总结任务（使用新配置的时间间隔）
        # 重新计算时间间隔以确保使用最新配置
        save_interval_minutes = self.config.get("conversation_save_interval", 30)  # 重新获取当前配置
        save_interval_ms = save_interval_minutes * 60 * 1000
        self.root.after(save_interval_ms, self.create_memory_summary)  # 重新安排任务

    def create_memory_summary(self):
        """创建记忆库总结"""
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 分析对话历史
        user_messages = [entry for entry in self.conversation_history if entry["sender"] == "用户"]
        ai_messages = [entry for entry in self.conversation_history if entry["sender"] == "AI"]
        system_messages = [entry for entry in self.conversation_history if entry["sender"] == "系统"]

        # 生成总结内容
        summary_content = f"定期总结 - {current_time}\n"
        summary_content += f"- 本次会话期间，用户发送了 {len(user_messages)} 条消息\n"
        summary_content += f"- AI回复了 {len(ai_messages)} 条消息\n"
        summary_content += f"- 系统发送了 {len(system_messages)} 条消息\n"
        summary_content += f"- 当前已导入 {len(self.memory['programs'])} 个程序到记忆库\n"
        summary_content += f"- 长期记忆库中包含 {len(self.memory['long_term_memory'])} 条重要信息\n"

        # 如果有用户消息，添加最近的几条
        if user_messages:
            summary_content += "- 最近的用户请求:\n"
            # 显示最近的3条用户消息
            recent_user_msgs = user_messages[-3:]
            for msg in recent_user_msgs:
                msg_preview = msg["message"][:50] + "..." if len(msg["message"]) > 50 else msg["message"]
                summary_content += f"  * {msg_preview}\n"

        # 创建总结条目
        summary = {
            "date": current_time,
            "type": "periodic_summary",
            "content": summary_content
        }

        # 添加到记忆库的总结列表
        self.memory["summaries"].append(summary)

        # 限制总结数量，只保留最近的10条
        if len(self.memory["summaries"]) > 10:
            self.memory["summaries"] = self.memory["summaries"][-10:]

        # 保存记忆库
        self.save_memory()

        # 显示提示信息（不直接显示在聊天窗口中，以免打扰用户）
        print(f"记忆库总结已创建于 {current_time}")

        # 继续设置下一次的总结任务（使用新配置的时间间隔）
        # 重新计算时间间隔以确保使用最新配置
        save_interval_minutes = self.config.get("conversation_save_interval", 30)  # 重新获取当前配置
        save_interval_ms = save_interval_minutes * 60 * 1000
        self.root.after(save_interval_ms, self.create_memory_summary)  # 重新安排任务
    
    def handle_enter_key(self, event):
        """处理回车键事件，如果同时按下Shift则换行，否则发送消息"""
        if event.state & 0x1:  # Shift键被按下
            return  # 允许换行
        else:
            self.send_message()  # 发送消息
            return "break"  # 阻止默认换行行为
    
    def display_message(self, sender, message):
        """在对话记录框中显示消息"""
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 将Markdown格式转换为tkinter Text组件支持的格式
        formatted_message = self.convert_markdown_to_text(message)

        # 获取主题颜色
        colors = self.get_theme_colors()

        # 根据发送者选择颜色
        if sender == "系统":
            color = colors["system_fg"]
        elif sender == "用户":
            color = colors["user_fg"]
        elif sender == "AI":
            color = colors["ai_fg"]
        else:
            color = colors["fg"]  # 默认颜色

        # 获取起始位置，用于后续着色
        start_pos = self.chat_display.index("end-2c")

        # 插入时间戳
        timestamp_text = f"[{timestamp}] "
        self.chat_display.insert(tk.END, timestamp_text)

        # 设置时间戳颜色
        self.chat_display.tag_add("timestamp", start_pos, f"{start_pos}+{len(timestamp_text)}c")
        self.chat_display.tag_config("timestamp", foreground=colors["timestamp_fg"])

        # 插入发送者和消息
        sender_text = f"{sender}: "
        self.chat_display.insert(tk.END, sender_text)
        self.chat_display.tag_add("sender", f"{start_pos}+{len(timestamp_text)}c", f"{start_pos}+{len(timestamp_text+sender_text)}c")
        self.chat_display.tag_config("sender", foreground=color, font=("微软雅黑", 10, "bold"))

        # 插入消息内容
        message_start = f"{start_pos}+{len(timestamp_text+sender_text)}c"
        self.chat_display.insert(tk.END, f"{formatted_message}\n\n")
        self.chat_display.tag_add("message", message_start, f"{message_start}+{len(formatted_message)}c")
        self.chat_display.tag_config("message", foreground=color)

        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)  # 自动滚动到底部

        # 同时记录到对话历史
        self.conversation_history.append({
            "timestamp": timestamp,
            "sender": sender,
            "message": message
        })
    
    def convert_markdown_to_text(self, markdown_text):
        """将Markdown格式转换为普通文本（简化实现）"""
        # 处理代码块标记（保留内容但移除标记）
        text = re.sub(r'```.*?\n(.*?)```', r'\1', markdown_text, flags=re.DOTALL)
        # 处理行内代码标记
        text = re.sub(r'`(.*?)`', r'`\1`', text)
        # 处理粗体标记
        text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
        # 处理斜体标记
        text = re.sub(r'\*(.*?)\*', r'_\1_', text)
        # 处理标题标记（简化处理）
        text = re.sub(r'^### (.*?)$', r'\1', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.*?)$', r'\1', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.*?)$', r'\1', text, flags=re.MULTILINE)
        # 处理链接标记
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1(\2)', text)
        # 处理列表标记
        text = re.sub(r'^-\s+', r'* ', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s+', r'\g<0>', text, flags=re.MULTILINE)  # 保留数字列表格式
        
        return text

    def check_required_libs_and_tools(self):
        """检查必需的库和工具"""
        missing_items = []
        optional_items = []

        # 检查必需的第三方库
        try:
            import requests
        except ImportError:
            missing_items.append("requests")

        # 检查可选的库和工具（用于不同编程语言支持）
        # Python - 通常已经安装
        try:
            import subprocess
            result = subprocess.run(["python", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                optional_items.append("Python解释器")
        except:
            optional_items.append("Python解释器")

        # Node.js (用于JavaScript)
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                optional_items.append("Node.js")
        except FileNotFoundError:
            optional_items.append("Node.js")

        # Java
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                optional_items.append("Java运行时")
        except FileNotFoundError:
            optional_items.append("Java运行时")

        # GCC (用于C/C++)
        try:
            result = subprocess.run(["gcc", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                optional_items.append("GCC编译器")
        except FileNotFoundError:
            optional_items.append("GCC编译器")

        # 检查是否存在缺失的必需库
        if missing_items:
            # 弹窗询问用户是否安装缺失的库
            self.prompt_install_missing_libs(missing_items)
        elif optional_items:
            # 有可选功能无法使用，显示提示
            self.show_optional_features_unavailable(optional_items)

    def prompt_install_missing_libs(self, missing_libs):
        """提示用户安装缺失的库"""
        libs_str = ", ".join(missing_libs)
        message = f"检测到以下必需库未安装: {libs_str}\n是否要自动安装这些库？"

        # 创建确认窗口
        InstallConfirmWindow(self, message, missing_libs, "必需")

    def show_optional_features_unavailable(self, unavailable_features):
        """显示哪些可选功能无法使用"""
        features_str = ", ".join(unavailable_features)
        message = f"以下功能可能无法使用，因为缺少相关工具: {features_str}\n\nAI可能无法执行相关编程语言的代码。"

        # 创建提示窗口
        InstallConfirmWindow(self, message, unavailable_features, "可选")

# InstallConfirmWindow类结束

    def send_message(self):
        """发送用户消息"""
        user_text = self.user_input.get("1.0", tk.END).strip()
        if not user_text:
            return

        # 显示用户消息
        self.display_message("用户", user_text)

        # 清空输入框
        self.user_input.delete("1.0", tk.END)

        # 更新按钮为停止生成
        self.send_button.config(text="停止", command=self.stop_generation)

        # 在新线程中处理AI响应
        self.response_thread = threading.Thread(
            target=self.get_ai_response,
            args=(user_text,)
        )
        self.response_thread.start()

    def stop_generation(self):
        """停止AI生成"""
        # 这里可以实现停止逻辑
        self.display_message("系统", "已停止生成响应。")
        self.send_button.config(text="发送", command=self.send_message)

    def process_command(self, user_message):
        """处理系统命令"""
        # 检查是否为系统命令
        if user_message.lower().startswith('/create folder ') or user_message.lower().startswith('/create_dir '):
            # 提取文件夹路径
            folder_path = user_message[13:].strip()  # 移除 '/create folder ' 部分
            try:
                os.makedirs(folder_path, exist_ok=True)
                return f"文件夹 '{folder_path}' 创建成功！"
            except Exception as e:
                return f"创建文件夹失败：{str(e)}"
        elif user_message.lower().startswith('/create file '):
            # 提取文件路径和内容（格式：/create file path/to/file.txt content here）
            parts = user_message[13:].split(' ', 1)  # 移除 '/create file ' 部分
            if len(parts) >= 2:
                file_path, content = parts[0], parts[1]
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    return f"文件 '{file_path}' 创建成功！"
                except Exception as e:
                    return f"创建文件失败：{str(e)}"
            else:
                return "错误：命令格式不正确。请使用 /create file path/to/file.txt content 格式。"
        elif user_message.lower().startswith('/list dir ') or user_message.lower().startswith('/list files '):
            # 列出目录内容
            dir_path = user_message[10:].strip() if user_message.lower().startswith('/list files ') else user_message[10:].strip()
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                try:
                    items = os.listdir(dir_path)
                    if not items:
                        return f"目录 '{dir_path}' 为空。"
                    else:
                        items_str = '\n'.join(items)
                        return f"目录 '{dir_path}' 的内容：\n{items_str}"
                except Exception as e:
                    return f"列出目录内容失败：{str(e)}"
            else:
                return f"错误：目录 '{dir_path}' 不存在。"
        elif user_message.lower() == '/help':
            # 显示帮助信息
            help_text = """
可用的系统命令：
/create folder <路径> - 创建新文件夹
/create file <路径> <内容> - 创建新文件并写入内容
/list dir <路径> - 列出目录内容
/help - 显示此帮助信息
            """
            return help_text.strip()
        return None  # 不是系统命令，返回None
    
    def execute_json_commands(self, json_commands):
        """执行JSON格式的命令"""
        executed_commands = []
        for cmd in json_commands:
            cmd_type = cmd.get("type")
            cmd_params = cmd.get("params", {})
            
            if cmd_type == "create_file":
                # 格式: {"type": "create_file", "params": {"path": "file.py", "content": "print('hello')"}}
                file_path = cmd_params.get("path")
                content = cmd_params.get("content")
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    result = f"文件 '{file_path}' 创建成功！"
                except Exception as e:
                    result = f"创建文件失败：{str(e)}"
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "create_folder":
                # 格式: {"type": "create_folder", "params": {"path": "my_folder"}}
                folder_path = cmd_params.get("path")
                try:
                    os.makedirs(folder_path, exist_ok=True)
                    result = f"文件夹 '{folder_path}' 创建成功！"
                except Exception as e:
                    result = f"创建文件夹失败：{str(e)}"
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "run_python":
                # 格式: {"type": "run_python", "params": {"path": "script.py"}}
                file_path = cmd_params.get("path")
                result = self.run_python_file(f"/run python {file_path}")
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "run_javascript":
                # 格式: {"type": "run_javascript", "params": {"path": "script.js"}}
                file_path = cmd_params.get("path")
                result = self.run_javascript_file(file_path)
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "run_java":
                # 格式: {"type": "run_java", "params": {"path": "program.java"}}
                file_path = cmd_params.get("path")
                result = self.run_java_file(file_path)
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "run_cpp":
                # 格式: {"type": "run_cpp", "params": {"path": "program.cpp"}}
                file_path = cmd_params.get("path")
                result = self.run_cpp_file(file_path)
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "run_c":
                # 格式: {"type": "run_c", "params": {"path": "program.c"}}
                file_path = cmd_params.get("path")
                result = self.run_c_file(file_path)
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "run_bash":
                # 格式: {"type": "run_bash", "params": {"command": "ls -la"}}
                command = cmd_params.get("command")
                result = self.run_bash_command(command)
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "run_cmd":
                # 格式: {"type": "run_cmd", "params": {"command": "dir"}}
                command = cmd_params.get("command")
                # 检查是否为高危命令
                if self.is_high_risk_command(command):
                    # 需要用户确认
                    confirmed = self.ask_user_confirmation(f"检测到高危CMD命令，是否执行？\n命令: {command}")
                    if confirmed:
                        result = self.run_cmd_command(command)
                    else:
                        result = f"用户取消执行高危命令: {command}"
                else:
                    result = self.run_cmd_command(command)
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述

            elif cmd_type == "run_powershell":
                # 格式: {"type": "run_powershell", "params": {"command": "Get-Process"}}
                command = cmd_params.get("command")
                # 检查是否为高危命令
                if self.is_high_risk_powershell_command(command):
                    # 需要用户确认
                    confirmed = self.ask_user_confirmation(f"检测到高危PowerShell命令，是否执行？\n命令: {command}")
                    if confirmed:
                        result = self.run_powershell_command(command)
                    else:
                        result = f"用户取消执行高危PowerShell命令: {command}"
                else:
                    result = self.run_powershell_command(command)
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "read_file":
                # 格式: {"type": "read_file", "params": {"path": "file.py"}}
                file_path = cmd_params.get("path")
                result = self.read_file_content(f"/read file {file_path}")
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "list_dir":
                # 格式: {"type": "list_dir", "params": {"path": "directory"}}
                dir_path = cmd_params.get("path")
                result = self.process_command(f"/list dir {dir_path}")
                executed_commands.append(result)  # 只返回执行结果，不包含命令描述
                
            elif cmd_type == "message":
                # 格式: {"type": "message", "params": {"content": "This is a message"}}
                content = cmd_params.get("content")
                executed_commands.append(content)  # 返回消息内容
        
        return executed_commands

    def ask_user_confirmation(self, message):
        """弹出确认对话框，询问用户是否执行高危操作"""
        import tkinter as tk
        from tkinter import messagebox

        # 创建一个临时的根窗口，如果不存在的话
        temp_root = None
        if not self.root.winfo_exists():
            temp_root = tk.Tk()
            temp_root.withdraw()  # 隐藏临时根窗口

        try:
            # 显示确认对话框
            confirmed = messagebox.askyesno("高危命令确认", message)
            return confirmed
        finally:
            # 如果我们创建了临时根窗口，则销毁它
            if temp_root:
                temp_root.destroy()

    def is_high_risk_command(self, command):
        """检查是否为高危CMD命令"""
        high_risk_keywords = [
            'del', 'rd', 'rmdir', 'format', 'diskpart', 'cipher', 'sfc',
            'shutdown', 'logoff', 'taskkill', 'tasklist', 'net user',
            'net localgroup', 'reg', 'dism', 'bcdedit', 'reagentc'
        ]
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in high_risk_keywords)

    def is_high_risk_powershell_command(self, command):
        """检查是否为高危PowerShell命令"""
        high_risk_keywords = [
            'remove-item', 'del', 'rm', 'rmdir', 'format-volume', 'clear-disk',
            'remove-computer', 'restart-computer', 'stop-computer', 'logoff',
            'remove-aduser', 'disable-adaccount', 'set-service', 'remove-itemproperty',
            'clear-itemproperty', 'new-scheduledjoboption', 'invoke-wmimethod',
            'remove-process', 'kill', 'reg delete', 'fsutil behavior set'
        ]
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in high_risk_keywords)

    def run_javascript_file(self, file_path):
        """运行JavaScript文件"""
        import subprocess
        try:
            result = subprocess.run(
                ["node", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return f"JavaScript文件运行成功！\n输出:\n{result.stdout}"
            else:
                return f"JavaScript文件运行失败！\n错误:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "错误：JavaScript文件运行超时（超过30秒）"
        except FileNotFoundError:
            return "错误：未找到Node.js。请确保已安装Node.js并添加到系统PATH中。"
        except Exception as e:
            return f"执行JavaScript文件时发生错误: {str(e)}"

    def run_java_file(self, file_path):
        """运行Java文件"""
        import subprocess
        import os
        try:
            # 获取文件目录和文件名
            file_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            class_name = os.path.splitext(file_name)[0]
            
            # 编译Java文件
            compile_result = subprocess.run(
                ["javac", file_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=file_dir or '.'
            )
            
            if compile_result.returncode != 0:
                return f"Java文件编译失败！\n错误:\n{compile_result.stderr}"
            
            # 运行编译后的类
            run_result = subprocess.run(
                ["java", class_name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=file_dir or '.'
            )
            
            if run_result.returncode == 0:
                return f"Java程序运行成功！\n输出:\n{run_result.stdout}"
            else:
                return f"Java程序运行失败！\n错误:\n{run_result.stderr}"
        except subprocess.TimeoutExpired:
            return "错误：Java程序运行超时（超过30秒）"
        except FileNotFoundError:
            return "错误：未找到Java编译器或运行时。请确保已安装Java并添加到系统PATH中。"
        except Exception as e:
            return f"执行Java文件时发生错误: {str(e)}"

    def run_cpp_file(self, file_path):
        """运行C++文件"""
        import subprocess
        import os
        try:
            # 生成输出文件名
            output_path = os.path.splitext(file_path)[0] + '.exe' if os.name == 'nt' else os.path.splitext(file_path)[0]
            
            # 编译C++文件
            compile_result = subprocess.run(
                ["g++", "-o", output_path, file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if compile_result.returncode != 0:
                return f"C++文件编译失败！\n错误:\n{compile_result.stderr}"
            
            # 运行编译后的程序
            run_result = subprocess.run(
                [output_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # 删除编译后的可执行文件
            try:
                os.remove(output_path)
            except:
                pass  # 忽略删除失败
            
            if run_result.returncode == 0:
                return f"C++程序运行成功！\n输出:\n{run_result.stdout}"
            else:
                return f"C++程序运行失败！\n错误:\n{run_result.stderr}"
        except subprocess.TimeoutExpired:
            return "错误：C++程序运行超时（超过30秒）"
        except FileNotFoundError:
            return "错误：未找到g++编译器。请确保已安装GCC编译器并添加到系统PATH中。"
        except Exception as e:
            return f"执行C++文件时发生错误: {str(e)}"

    def run_c_file(self, file_path):
        """运行C文件"""
        import subprocess
        import os
        try:
            # 生成输出文件名
            output_path = os.path.splitext(file_path)[0] + '.exe' if os.name == 'nt' else os.path.splitext(file_path)[0]
            
            # 编译C文件
            compile_result = subprocess.run(
                ["gcc", "-o", output_path, file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if compile_result.returncode != 0:
                return f"C文件编译失败！\n错误:\n{compile_result.stderr}"
            
            # 运行编译后的程序
            run_result = subprocess.run(
                [output_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # 删除编译后的可执行文件
            try:
                os.remove(output_path)
            except:
                pass  # 忽略删除失败
            
            if run_result.returncode == 0:
                return f"C程序运行成功！\n输出:\n{run_result.stdout}"
            else:
                return f"C程序运行失败！\n错误:\n{run_result.stderr}"
        except subprocess.TimeoutExpired:
            return "错误：C程序运行超时（超过30秒）"
        except FileNotFoundError:
            return "错误：未找到gcc编译器。请确保已安装GCC编译器并添加到系统PATH中。"
        except Exception as e:
            return f"执行C文件时发生错误: {str(e)}"
    
    def run_bash_command(self, command):
        """运行bash命令"""
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return f"Bash命令执行成功！\n输出:\n{result.stdout}"
            else:
                return f"Bash命令执行失败！\n错误:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "错误：Bash命令执行超时（超过30秒）"
        except Exception as e:
            return f"执行Bash命令时发生错误: {str(e)}"
    
    def run_cmd_command(self, command):
        """运行cmd命令"""
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return f"CMD命令执行成功！\n输出:\n{result.stdout}"
            else:
                return f"CMD命令执行失败！\n错误:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "错误：CMD命令执行超时（超过30秒）"
        except Exception as e:
            return f"执行CMD命令时发生错误: {str(e)}"
    
    def run_powershell_command(self, command):
        """运行PowerShell命令"""
        import subprocess
        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return f"PowerShell命令执行成功！\n输出:\n{result.stdout}"
            else:
                return f"PowerShell命令执行失败！\n错误:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "错误：PowerShell命令执行超时（超过30秒）"
        except FileNotFoundError:
            return "错误：未找到PowerShell。请确保系统支持PowerShell。"
        except Exception as e:
            return f"执行PowerShell命令时发生错误: {str(e)}"

    def extract_json_commands(self, ai_response):
        """从AI响应中提取JSON格式的命令"""
        import json
        import re
        
        # 尝试从响应中提取JSON部分
        json_match = re.search(r'```json\n(.*?)```', ai_response, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(1).strip()
                commands = json.loads(json_str)
                # 确保是列表格式
                if isinstance(commands, dict):
                    commands = [commands]
                return commands
            except json.JSONDecodeError:
                pass
        
        # 如果没有找到JSON块，尝试直接解析整个响应
        try:
            commands = json.loads(ai_response.strip())
            # 确保是列表格式
            if isinstance(commands, dict):
                commands = [commands]
            return commands
        except json.JSONDecodeError:
            pass
        
        return []

    def run_python_file(self, command):
        """运行Python文件命令"""
        import subprocess
        try:
            # 提取文件路径
            file_path = command[12:].strip()  # 移除 '/run python ' 部分
            
            # 运行Python文件
            result = subprocess.run(
                ["python", file_path],
                capture_output=True,
                text=True,
                timeout=30  # 30秒超时
            )
            
            if result.returncode == 0:
                return f"Python文件运行成功！\n输出:\n{result.stdout}"
            else:
                return f"Python文件运行失败！\n错误:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "错误：Python文件运行超时（超过30秒）"
        except Exception as e:
            return f"执行Python文件时发生错误: {str(e)}"

    def analyze_and_fix_code(self, file_path, error_message):
        """分析代码错误并尝试自动修复（AI辅助）"""
        try:
            # 读取原始文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                original_code = f.read()
            
            # 构建AI请求来修复错误
            fix_request = f"以下Python代码在运行时出现错误：\n错误信息：{error_message}\n代码内容：\n{original_code}\n\n请分析错误并提供修复后的代码。"
            
            # 使用AI API来获取修复建议
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['api_key']}"
            }
            
            # 构建消息历史
            messages = self.context_messages + [{"role": "user", "content": fix_request}]
            
            data = {
                "model": self.config["model"],
                "messages": messages,
                "temperature": 0.3  # 降低温度以获得更准确的修复
            }
            
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # 创建不使用系统代理的会话
            session = requests.Session()
            session.trust_env = False
            
            response = session.post(
                self.config["api_url"],
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                try:
                    ai_fix_suggestion = result["choices"][0]["message"]["content"]
                    
                    # 这里可以进一步解析AI的修复建议并应用
                    # 简单实现：返回AI建议
                    return ai_fix_suggestion
                except (KeyError, IndexError):
                    return f"无法解析AI修复建议: {result}"
            else:
                return f"AI修复请求失败：{response.status_code} - {response.text}"
        except Exception as e:
            return f"自动修复过程中发生错误: {str(e)}"

    def read_file_content(self, command):
        """读取文件内容命令"""
        try:
            # 提取文件路径
            file_path = command[11:].strip()  # 移除 '/read file ' 部分
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"文件 '{file_path}' 的内容:\n{content[:1000]}..." if len(content) > 1000 else f"文件 '{file_path}' 的内容:\n{content}"
        except Exception as e:
            return f"读取文件时发生错误: {str(e)}"

    def get_ai_response(self, user_message):
        """获取AI的响应"""
        # 首先检查是否为系统命令
        command_result = self.process_command(user_message)
        if command_result:
            self.root.after(0, lambda: self.display_message("系统", command_result))
            self.root.after(0, lambda: self.send_button.config(text="发送", command=self.send_message))
            return

        # 检查配置是否完整
        if not self.config.get("api_url") or not self.config.get("api_key") or not self.config.get("model"):
            error_msg = "错误：请先在设置中配置API URL、API Key和模型名称！"
            self.root.after(0, lambda: self.display_message("系统", error_msg))
            self.root.after(0, lambda: self.send_button.config(text="发送", command=self.send_message))
            return

        # 检查是否为编程请求
        programming_keywords = ['编程', '代码', '写一个', '创建', '开发', '实现', '程序', '脚本', 'project', 'code', '开发', '编写', '函数', '类', '模块', '算法', '功能', '运行', '测试', '调试', '错误', 'bug', '修复', '检查', '执行']
        is_programming_request = any(keyword in user_message.lower() for keyword in programming_keywords)

        # 首先，向AI询问是否需要查询记忆库
        self.assess_memory_need(user_message, is_programming_request)

    def assess_memory_need(self, user_message, is_programming_request):
        """第一阶段：询问AI是否需要查询记忆库"""
        # 构建一个消息询问AI是否需要查询记忆库
        assessment_prompt = f"""
请评估用户的问题 '{user_message}' 是否可能需要查询历史记忆来提供更好的回答。
请按照以下JSON格式返回您的评估：
```json
{{
  "requires_memory": true/false,
  "reason": "为什么需要或不需要查询记忆"
}}
```
如果用户询问之前提到过的事情、历史信息、个人偏好、之前创建的内容等，则很可能会需要查询记忆库。
"""

        # 构建评估消息
        assessment_messages = self.context_messages + [{"role": "user", "content": assessment_prompt}]

        # 发送评估请求
        try:
            headers = {"Content-Type": "application/json"}

            # 根据API URL确定认证方式
            api_url = self.config["api_url"]
            if "openai.com" in api_url or "api.openai.com" in api_url:
                headers["Authorization"] = f"Bearer {self.config['api_key']}"
            elif "azure.com" in api_url or "openai.azure.com" in api_url:
                headers["api-key"] = self.config['api_key']
            else:
                headers["Authorization"] = f"Bearer {self.config['api_key']}"

            data = {
                "model": self.config["model"],
                "messages": assessment_messages,
                "temperature": 0.1  # 低温度获得更准确的评估
            }

            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            session = requests.Session()
            session.trust_env = False

            response = session.post(
                self.config["api_url"],
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                try:
                    assessment_response = result["choices"][0]["message"]["content"]

                    # 解析AI的评估
                    requires_memory = self.parse_memory_assessment(assessment_response)

                    if requires_memory:
                        # 如果AI认为需要查询记忆库，执行查询
                        self.query_memory_then_respond(user_message, is_programming_request)
                    else:
                        # 如果不需要，直接生成回复
                        self.generate_direct_response(user_message, is_programming_request)

                except (KeyError, IndexError):
                    print(f"无法从评估响应中提取信息: {result}")
                    # 如果解析失败，仍然尝试查询记忆库（更安全的做法）
                    self.query_memory_then_respond(user_message, is_programming_request)
            else:
                print(f"记忆需求评估请求失败: {response.status_code} - {response.text}")
                # 如果评估失败，仍然执行查询
                self.query_memory_then_respond(user_message, is_programming_request)

        except Exception as e:
            print(f"记忆需求评估过程中发生错误: {str(e)}")
            # 如果评估失败，仍然执行查询
            self.query_memory_then_respond(user_message, is_programming_request)

    def parse_memory_assessment(self, assessment_response):
        """解析AI的记忆需求评估"""
        import json
        import re

        # 尝试从响应中提取JSON
        json_match = re.search(r'```json\n(.*?)```', assessment_response, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(1).strip()
                parsed = json.loads(json_str)
                return parsed.get("requires_memory", False)
            except json.JSONDecodeError:
                pass

        # 如果没有JSON块，尝试直接解析
        try:
            parsed = json.loads(assessment_response.strip())
            return parsed.get("requires_memory", False)
        except json.JSONDecodeError:
            pass

        # 如果都失败了，返回False，让系统继续查询
        return True  # 在解析失败时，默认查询记忆以确保不遗漏重要信息

    def query_memory_then_respond(self, user_message, is_programming_request):
        """查询记忆库，然后生成最终回复"""
        # 查找相关记忆
        relevant_memory = self.find_relevant_memory(user_message)

        # 生成最终回复
        self.generate_response_with_memory(user_message, is_programming_request, relevant_memory)

    def generate_direct_response(self, user_message, is_programming_request):
        """直接生成回复（不需要记忆库信息）"""
        # 按原逻辑处理
        if is_programming_request:
            enhanced_prompt = f"{user_message}\n\n请按照以下步骤完成任务：\n1. 首先，提供一个To Do列表，详细说明需要完成的步骤\n2. 然后，按照To Do列表逐步执行\n\n你需要使用以下JSON格式输出所有命令：\n```json\n[\n  {{\n    \"type\": \"message\",\n    \"params\": {{ \"content\": \"任务说明\" }}\n  }},\n  {{\n    \"type\": \"create_file\",\n    \"params\": {{ \"path\": \"文件路径\", \"content\": \"文件内容\" }}\n  }},\n  {{\n    \"type\": \"create_folder\",\n    \"params\": {{ \"path\": \"文件夹路径\" }}\n  }},\n  {{\n    \"type\": \"run_python\",\n    \"params\": {{ \"path\": \"Python文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_javascript\",\n    \"params\": {{ \"path\": \"JavaScript文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_java\",\n    \"params\": {{ \"path\": \"Java文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_cpp\",\n    \"params\": {{ \"path\": \"C++文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_c\",\n    \"params\": {{ \"path\": \"C文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_cmd\",\n    \"params\": {{ \"command\": \"CMD命令\" }}\n  }},\n  {{\n    \"type\": \"run_powershell\",\n    \"params\": {{ \"command\": \"PowerShell命令\" }}\n  }},\n  {{\n    \"type\": \"read_file\",\n    \"params\": {{ \"path\": \"文件路径\" }}\n  }},\n  {{\n    \"type\": \"list_dir\",\n    \"params\": {{ \"path\": \"目录路径\" }}\n  }}\n]\n```"
            messages = self.context_messages + [{"role": "user", "content": enhanced_prompt}]
        else:
            # 使用原始消息
            messages = self.context_messages + [{"role": "user", "content": user_message}]

        # 发送API请求
        self.send_api_request(messages, user_message)

    def generate_response_with_memory(self, user_message, is_programming_request, relevant_memory):
        """使用记忆信息生成回复"""
        if relevant_memory:
            # 创建一个包含相关记忆的系统消息
            memory_context = "以下是与当前对话相关的长期记忆，供您参考：\n\n"
            for idx, mem in enumerate(relevant_memory, 1):
                memory_context += f"记忆 {idx}: [{mem['timestamp']}] {mem['sender']}: {mem['message']}\n"
            memory_context += f"\n原始用户消息: {user_message}"

            if is_programming_request:
                enhanced_prompt = f"{memory_context}\n\n请按照以下步骤完成任务：\n1. 首先，提供一个To Do列表，详细说明需要完成的步骤\n2. 然后，按照To Do列表逐步执行\n\n你需要使用以下JSON格式输出所有命令：\n```json\n[\n  {{\n    \"type\": \"message\",\n    \"params\": {{ \"content\": \"任务说明\" }}\n  }},\n  {{\n    \"type\": \"create_file\",\n    \"params\": {{ \"path\": \"文件路径\", \"content\": \"文件内容\" }}\n  }},\n  {{\n    \"type\": \"create_folder\",\n    \"params\": {{ \"path\": \"文件夹路径\" }}\n  }},\n  {{\n    \"type\": \"run_python\",\n    \"params\": {{ \"path\": \"Python文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_javascript\",\n    \"params\": {{ \"path\": \"JavaScript文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_java\",\n    \"params\": {{ \"path\": \"Java文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_cpp\",\n    \"params\": {{ \"path\": \"C++文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_c\",\n    \"params\": {{ \"path\": \"C文件路径\" }}\n  }},\n  {{\n    \"type\": \"run_cmd\",\n    \"params\": {{ \"command\": \"CMD命令\" }}\n  }},\n  {{\n    \"type\": \"run_powershell\",\n    \"params\": {{ \"command\": \"PowerShell命令\" }}\n  }},\n  {{\n    \"type\": \"read_file\",\n    \"params\": {{ \"path\": \"文件路径\" }}\n  }},\n  {{\n    \"type\": \"list_dir\",\n    \"params\": {{ \"path\": \"目录路径\" }}\n  }}\n]\n```"
                messages = self.context_messages + [{"role": "user", "content": enhanced_prompt}]
            else:
                # 对于非编程请求，也将相关记忆包含在内
                messages = self.context_messages + [{"role": "user", "content": memory_context}]
        else:
            # 没有相关记忆，但长期记忆库非空，通知AI
            messages = self.context_messages + [{"role": "user", "content": f"注意：长期记忆库中有 {len(self.memory['long_term_memory'])} 条记忆记录，但与当前查询的相似度未达到 {self.config.get('memory_similarity_threshold', 85)}% 的阈值。如果您觉得相关信息可能在记忆库中，请告知用户。\n\n{user_message}"}]

        # 发送API请求
        self.send_api_request(messages, user_message)

    def send_api_request(self, messages, original_user_message):
        """发送API请求并处理响应"""
        try:
            # 根据API URL确定认证方式和请求格式
            api_url = self.config["api_url"]
            headers = {"Content-Type": "application/json"}

            # 对于OpenAI API风格的服务，使用Bearer认证
            if "openai.com" in api_url or "api.openai.com" in api_url:
                headers["Authorization"] = f"Bearer {self.config['api_key']}"
            # 对于Azure OpenAI，可能需要不同的认证
            elif "azure.com" in api_url or "openai.azure.com" in api_url:
                headers["api-key"] = self.config['api_key']
            # 对于其他API服务，也可以添加特定的处理
            else:
                headers["Authorization"] = f"Bearer {self.config['api_key']}"

            data = {
                "model": self.config["model"],
                "messages": messages,  # 使用上面已经定义的messages
                "stream": False,  # 简单实现，不使用流式传输
                "temperature": 0.7  # 添加温度参数，提高API兼容性
            }

            # 发送API请求
            print(f"正在向 {self.config['api_url']} 发送请求...")  # 调试信息
            print(f"Headers: {headers}")  # 调试信息
            print(f"Data: {data}")  # 调试信息

            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # 禁用SSL警告

                # 创建不使用系统代理的会话
                session = requests.Session()
                session.trust_env = False

                response = session.post(
                    self.config["api_url"],
                    headers=headers,
                    json=data,
                    timeout=60,  # 增加超时时间到60秒
                    verify=False  # 禁用SSL验证（仅用于测试）
                )

                print(f"收到响应，状态码: {response.status_code}")  # 调试信息
                print(f"响应内容: {response.text}")  # 调试信息

                if response.status_code in [200, 201]:  # 一些API可能返回201
                    try:
                        result = response.json()
                        # 尝试不同的响应格式
                        try:
                            ai_response = result["choices"][0]["message"]["content"]
                        except (KeyError, IndexError):
                            # 如果上面的路径失败，尝试其他常见的API响应格式
                            try:
                                ai_response = result["choices"][0]["text"]
                            except (KeyError, IndexError):
                                # 一些API可能有不同的结构
                                try:
                                    # 尝试Ollama或其他API的响应格式
                                    ai_response = result["response"] if "response" in result else result.get("content", str(result))
                                except:
                                    # 如果还是失败，返回完整响应以帮助调试
                                    ai_response = f"无法解析API响应: {result}"

                        # 从AI响应中提取JSON命令
                        json_commands = self.extract_json_commands(ai_response)

                        # 判断是否只包含message类型命令（纯对话）或包含实际执行命令
                        only_message_commands = True
                        if json_commands:
                            for cmd in json_commands:
                                cmd_type = cmd.get("type", "")
                                if cmd_type != "message":  # 如果存在非message类型的命令
                                    only_message_commands = False
                                    break

                        # 根据命令类型决定如何显示AI的回复
                        if json_commands and only_message_commands:
                            # 如果只包含message命令，提取message内容显示，不显示JSON格式
                            message_contents = []
                            for cmd in json_commands:
                                if cmd.get("type") == "message":
                                    content = cmd.get("params", {}).get("content", "")
                                    if content:
                                        message_contents.append(content)

                            if message_contents:
                                # 将所有message内容合并显示
                                ai_message = "\n".join(message_contents)
                                self.root.after(0, lambda msg=ai_message: self.display_message("AI", msg))
                                self.context_messages.append({"role": "assistant", "content": ai_message})
                            else:
                                # 如果没有有效的message内容但有JSON，仍需处理
                                self.root.after(0, lambda: self.display_message("AI", ai_response))
                                self.context_messages.append({"role": "assistant", "content": ai_response})
                        elif json_commands and not only_message_commands:
                            # 如果包含非message命令，先提取并显示message内容
                            message_contents = []
                            for cmd in json_commands:
                                if cmd.get("type") == "message":
                                    content = cmd.get("params", {}).get("content", "")
                                    if content:
                                        message_contents.append(content)

                            if message_contents:
                                # 将所有message内容合并显示
                                ai_message = "\n".join(message_contents)
                                self.root.after(0, lambda msg=ai_message: self.display_message("AI", msg))

                            # 显示用户的原始请求
                            self.root.after(0, lambda: self.display_message("用户", original_user_message))

                            # 逐步执行JSON命令，只显示执行结果
                            executed_commands = self.execute_json_commands(json_commands)

                            for idx, cmd in enumerate(json_commands):
                                cmd_type = cmd.get("type", "")

                                # 只对非message类型的命令显示执行结果
                                if cmd_type != "message" and idx < len(executed_commands):
                                    cmd_result = executed_commands[idx]
                                    # 只显示执行结果，不显示AI的意图
                                    self.root.after(0, lambda result=cmd_result: self.display_message("系统", result.split('\n', 1)[1] if '\n' in result else result))  # 显示执行结果，但去掉命令描述

                                    # 将命令执行结果添加到上下文中，以保持对话连贯性
                                    self.context_messages.append({"role": "system", "content": f"命令执行结果: {cmd_result}"})

                                    # 如果命令执行结果包含错误信息，考虑添加一个提示给AI
                                    if "错误" in cmd_result or "失败" in cmd_result:
                                        # 这里可以触发AI的错误修复逻辑
                                        # 简单实现：只记录错误，实际的AI错误修复需要模型支持
                                        pass
                        else:
                            # 如果没有JSON命令，正常显示AI的响应
                            self.root.after(0, lambda: self.display_message("AI", ai_response))
                            self.context_messages.append({"role": "assistant", "content": ai_response})

                        # 更新上下文消息列表
                        self.context_messages.append({"role": "user", "content": original_user_message})

                        # 限制上下文长度为最近的10条消息（系统消息+9轮对话 = 10条）
                        if len(self.context_messages) > 10:  # 系统消息(1) + 9轮对话(用户+AI各1条 = 9)
                            self.context_messages = self.context_messages[:1] + self.context_messages[-9:]  # 保留系统消息+最近9轮对话
                    except ValueError:  # JSON解析错误
                        error_msg = f"无法解析API响应（非JSON格式）: {response.text}"
                        self.root.after(0, lambda: self.display_message("系统", error_msg))
                else:
                    error_msg = f"API请求失败：{response.status_code} - {response.text}"
                    self.root.after(0, lambda: self.display_message("系统", error_msg))
            except requests.exceptions.RequestException as e:
                print(f"请求异常: {e}")  # 调试信息
                error_msg = f"API请求异常: {str(e)}"
                self.root.after(0, lambda: self.display_message("系统", error_msg))
            except Exception as e:
                print(f"其他异常: {e}")  # 调试信息
                error_msg = f"发生未知错误: {str(e)}"
                self.root.after(0, lambda: self.display_message("系统", error_msg))

        except requests.exceptions.Timeout:
            error_msg = "错误：API请求超时，请检查网络连接或API地址是否正确。"
            self.root.after(0, lambda: self.display_message("系统", error_msg))
        except requests.exceptions.ConnectionError:
            error_msg = "错误：无法连接到API服务器，请检查API地址是否正确、网络连接是否正常。"
            self.root.after(0, lambda: self.display_message("系统", error_msg))
        except requests.exceptions.RequestException as e:
            error_msg = f"错误：网络请求失败 - {str(e)}"
            self.root.after(0, lambda: self.display_message("系统", error_msg))
        except KeyError:
            error_msg = "错误：API响应格式不正确，请检查API配置。"
            self.root.after(0, lambda: self.display_message("系统", error_msg))
        except Exception as e:
            error_msg = f"错误：获取AI响应时发生未知错误 - {str(e)}"
            self.root.after(0, lambda: self.display_message("系统", error_msg))

        # 恢复发送按钮
        self.root.after(0, lambda: self.send_button.config(text="发送", command=self.send_message))
    
    def open_settings(self):
        """打开设置页面"""
        SettingsWindow(self)
    
    def load_config(self):
        """加载配置文件"""
        default_config = {
            "api_url": "",
            "api_key": "",
            "model": "",
            "conversation_save_interval": 30,  # 对话保存时间（分钟）
            "memory整理_interval": 60,  # 记忆整理时间（分钟）
            "memory_similarity_threshold": 85,  # 记忆相似度阈值（百分比）
            "system_prompt": "你是这台Windows电脑的AI助手。你的职责是：\n" +
                             "1. 首先生成一个详细的任务To Do列表\n" +
                             "2. 然后按步骤执行任务\n" +
                             "3. 检查程序执行情况并自动修正错误\n\n" +
                             "你是一个拥有系统访问权限的AI，可以对电脑进行任何操作，包括：\n" +
                             "- 文件操作：创建、读取、修改、删除文件\n" +
                             "- 目录操作：创建、删除文件夹，列出目录内容\n" +
                             "- 程序执行：运行多种编程语言的代码\n" +
                             "- 系统命令：执行CMD和PowerShell命令\n\n" +
                             "对于高危命令（如删除文件、格式化、系统修改等），必须在执行前请求用户确认。\n\n" +
                             "你必须使用JSON格式输出命令，格式如下：\n" +
                             "```json\n" +
                             "[\n" +
                             "  {\n" +
                             "    \"type\": \"message\",\n" +
                             "    \"params\": { \"content\": \"任务说明\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"create_file\",\n" +
                             "    \"params\": { \"path\": \"文件路径\", \"content\": \"文件内容\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"create_folder\",\n" +
                             "    \"params\": { \"path\": \"文件夹路径\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"run_python\",\n" +
                             "    \"params\": { \"path\": \"Python文件路径\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"run_javascript\",\n" +
                             "    \"params\": { \"path\": \"JavaScript文件路径\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"run_java\",\n" +
                             "    \"params\": { \"path\": \"Java文件路径\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"run_cpp\",\n" +
                             "    \"params\": { \"path\": \"C++文件路径\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"run_c\",\n" +
                             "    \"params\": { \"path\": \"C文件路径\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"run_bash\",\n" +
                             "    \"params\": { \"command\": \"bash命令\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"run_cmd\",\n" +
                             "    \"params\": { \"command\": \"cmd命令\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"run_powershell\",\n" +
                             "    \"params\": { \"command\": \"PowerShell命令\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"read_file\",\n" +
                             "    \"params\": { \"path\": \"文件路径\" }\n" +
                             "  },\n" +
                             "  {\n" +
                             "    \"type\": \"list_dir\",\n" +
                             "    \"params\": { \"path\": \"目录路径\" }\n" +
                             "  }\n" +
                             "]\n" +
                             "```\n\n" +
                             "作为AI助手，你需要：\n" +
                             "1. 分析需求并生成To Do列表\n" +
                             "2. 按To Do 列表逐步执行任务\n" +
                             "3. 通过run_*命令测试程序\n" +
                             "4. 如果发现错误，使用read_file命令检查文件内容\n" +
                             "5. 使用create_file命令自动修正错误\n" +
                             "6. 对于高危命令，请求用户确认\n" +
                             "7. 持续测试直到程序正常运行"
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置和现有配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception:
                pass
                
        return default_config
    
    def save_config(self, config):
        """保存配置文件"""
        # 保存之前的配置用于比较
        old_config = self.config.copy() if self.config else {}

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.config = config

            # 如果系统提示词被修改，更新上下文消息
            if config.get("system_prompt") != self.context_messages[0]["content"]:
                # 保留其他上下文消息，只更新系统消息
                old_context = self.context_messages[1:]  # 保留除系统消息外的所有消息
                self.context_messages = [{"role": "system", "content": config["system_prompt"]}] + old_context

            # 如果记忆相关配置被修改，重新启动记忆整理任务
            if (config.get("memory整理_interval") != old_config.get("memory整理_interval") or
                config.get("conversation_save_interval") != old_config.get("conversation_save_interval")):

                # 重新启动记忆整理任务以应用新配置
                self.start_memory整理()

                # 重新启动对话保存任务以应用新配置
                # 为了做到这一点，我们需要重新启动主记忆整理任务
                # 但要确保不会重复启动，所以我们重新设置计时器
                try:
                    # 停止之前的定期总结任务
                    pass  # Tkinter的after任务无法直接取消，但新设置会覆盖它
                except:
                    pass

                # 重新开始定期总结任务
                save_interval_minutes = config.get("conversation_save_interval", 30)
                save_interval_ms = save_interval_minutes * 60 * 1000
                self.root.after(save_interval_ms, self.create_memory_summary)

            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
            return False
    
    def load_memory(self):
        """加载记忆库"""
        # 创建记忆目录
        os.makedirs(self.memory_dir, exist_ok=True)

        # 加载短期记忆（对话历史）
        if os.path.exists(self.short_term_memory_file):
            try:
                with open(self.short_term_memory_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)

                # 加载对话历史
                self.conversation_history = saved_data.get("conversation_history", [])
            except Exception as e:
                print(f"加载短期记忆时出错: {e}")
                self.conversation_history = []
        else:
            self.conversation_history = []

        # 加载长期记忆
        if os.path.exists(self.long_term_memory_file):
            try:
                with open(self.long_term_memory_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)

                # 加载程序信息和摘要
                self.memory = saved_data.get("memory", {
                    "programs": {},
                    "summaries": []
                })

                # 加载长期记忆（直接作为独立列表）
                self.memory["long_term_memory"] = saved_data.get("long_term_memory", [])
            except Exception as e:
                print(f"加载长期记忆时出错: {e}")
                self.memory = {
                    "programs": {},
                    "summaries": [],
                    "long_term_memory": []
                }
        else:
            self.memory = {
                "programs": {},
                "summaries": [],
                "long_term_memory": []
            }

        # 创建其他必要目录
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.onpython_dir, exist_ok=True)
    
    def save_memory(self):
        """保存记忆库和对话历史"""
        try:
            # 保存短期记忆（对话历史）
            short_term_data = {
                "conversation_history": self.conversation_history
            }

            with open(self.short_term_memory_file, 'w', encoding='utf-8') as f:
                json.dump(short_term_data, f, ensure_ascii=False, indent=2)

            # 保存长期记忆
            long_term_data = {
                "memory": {
                    "programs": self.memory.get("programs", {}),
                    "summaries": self.memory.get("summaries", [])
                },
                "long_term_memory": self.memory.get("long_term_memory", [])
            }

            with open(self.long_term_memory_file, 'w', encoding='utf-8') as f:
                json.dump(long_term_data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存记忆库失败: {str(e)}")

class InstallConfirmWindow:
    """安装确认窗口"""
    def __init__(self, app, message, items, item_type):
        self.app = app
        self.items = items
        self.item_type = item_type
        
        self.window = tk.Toplevel(app.root)
        self.window.title("库/工具检查" if item_type == "可选" else "必需库检查")
        self.window.geometry("500x200")
        self.window.resizable(False, False)
        
        # 模态窗口
        self.window.transient(app.root)
        self.window.grab_set()
        
        # 创建界面
        self.create_ui(message)
    
    def create_ui(self, message):
        """创建界面"""
        # 消息标签
        msg_label = tk.Label(self.window, text=message, wraplength=450, justify=tk.LEFT)
        msg_label.pack(pady=20, padx=20)
        
        # 按钮框架
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=20)
        
        if self.item_type == "必需":
            # 对于必需库，提供安装选项
            install_btn = tk.Button(button_frame, text="安装", command=self.start_installation, width=10)
            install_btn.pack(side=tk.LEFT, padx=10)
        
        # 关闭按钮
        close_btn = tk.Button(button_frame, text="关闭", command=self.window.destroy, width=10)
        close_btn.pack(side=tk.LEFT, padx=10)
    
    def start_installation(self):
        """开始安装过程"""
        # 更改UI显示安装进度
        for widget in self.window.winfo_children():
            widget.destroy()
        
        # 显示安装进度
        progress_label = tk.Label(self.window, text="正在安装库，请稍候...", font=("微软雅黑", 10))
        progress_label.pack(pady=30)
        
        # 创建进度条
        self.progress_var = tk.StringVar(value="准备安装...")
        progress_detail = tk.Label(self.window, textvariable=self.progress_var, font=("微软雅黑", 9))
        progress_detail.pack(pady=10)
        
        # 启动安装线程
        install_thread = threading.Thread(target=self.install_packages)
        install_thread.start()
    
    def install_packages(self):
        """安装包"""
        try:
            import subprocess
            import sys
            
            for i, item in enumerate(self.items):
                self.progress_var.set(f"正在安装 {item} ({i+1}/{len(self.items)})...")
                
                # 更新GUI
                self.app.root.update()
                
                if item == "requests":
                    # 安装requests库
                    result = subprocess.run([sys.executable, "-m", "pip", "install", "requests"],
                                          capture_output=True, text=True)
                
                if result.returncode != 0:
                    # 安装失败
                    self.app.root.after(0, lambda: self.show_installation_result(f"安装 {item} 失败:\\n{result.stderr}", False))
                    return
            
            # 所有安装完成
            self.app.root.after(0, lambda: self.show_installation_result("所有库安装完成！", True))
            
        except Exception as e:
            self.app.root.after(0, lambda: self.show_installation_result(f"安装过程中出现错误: {str(e)}", False))
    
    def show_installation_result(self, message, success):
        """显示安装结果"""
        # 清空窗口
        for widget in self.window.winfo_children():
            widget.destroy()
        
        # 显示结果消息
        result_label = tk.Label(self.window, text=message, wraplength=450, justify=tk.LEFT)
        result_label.pack(pady=30, padx=20)
        
        # 根据结果决定按钮
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=20)
        
        if success:
            ok_btn = tk.Button(button_frame, text="确定", command=self.restart_app, width=10)
            ok_btn.pack(side=tk.LEFT, padx=10)
        else:
            retry_btn = tk.Button(button_frame, text="重试", command=self.retry_installation, width=10)
            retry_btn.pack(side=tk.LEFT, padx=10)
        
        close_btn = tk.Button(button_frame, text="关闭", command=self.window.destroy, width=10)
        close_btn.pack(side=tk.LEFT, padx=10)
    
    def restart_app(self):
        """重启应用"""
        self.window.destroy()
        self.app.root.destroy()
        
        # 重启应用
        import subprocess
        import sys
        subprocess.Popen([sys.executable] + sys.argv)
    
    def retry_installation(self):
        """重试安装"""
        # 重新开始安装
        self.start_installation()

class SettingsWindow:
    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.title("设置")
        self.window.geometry("500x400")
        self.window.resizable(False, False)
        
        # 模态窗口 - 阻止主窗口交互
        self.window.transient(app.root)
        self.window.grab_set()
        
        self.create_settings_ui()
    
    def create_settings_ui(self):
        """创建设置界面"""
        # 创建笔记本控件用于分页
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # API设置页面
        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="API设置")

        ttk.Label(api_frame, text="API地址:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        self.api_url_var = tk.StringVar(value=self.app.config.get("api_url", ""))
        self.api_url_entry = ttk.Entry(api_frame, textvariable=self.api_url_var, width=50)
        self.api_url_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(api_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        self.api_key_var = tk.StringVar(value=self.app.config.get("api_key", ""))
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=50, show="*")
        self.api_key_entry.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(api_frame, text="模型名称:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
        self.model_var = tk.StringVar(value=self.app.config.get("model", ""))
        self.model_entry = ttk.Entry(api_frame, textvariable=self.model_var, width=50)
        self.model_entry.grid(row=2, column=1, padx=10, pady=10)

        # 对话设置页面
        conversation_frame = ttk.Frame(notebook)
        notebook.add(conversation_frame, text="对话设置")

        ttk.Label(conversation_frame, text="对话保存时间:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        self.conversation_save_interval_var = tk.StringVar(value=str(self.app.config.get("conversation_save_interval", 30)))
        self.conversation_save_interval_spinbox = tk.Spinbox(conversation_frame, from_=1, to=1440, textvariable=self.conversation_save_interval_var, width=10)
        self.conversation_save_interval_spinbox.grid(row=0, column=1, sticky=tk.W, padx=10, pady=10)
        ttk.Label(conversation_frame, text="分钟 (范围: 1-1440，即1分钟到24小时)").grid(row=0, column=2, sticky=tk.W, padx=5, pady=10)

        # 记忆库设置页面
        memory_frame = ttk.Frame(notebook)
        notebook.add(memory_frame, text="记忆库设置")

        ttk.Label(memory_frame, text="记忆整理时间:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        self.memory整理_interval_var = tk.StringVar(value=str(self.app.config.get("memory整理_interval", 60)))
        self.memory整理_interval_spinbox = tk.Spinbox(memory_frame, from_=1, to=10080, textvariable=self.memory整理_interval_var, width=10)  # 最大值为一周的分钟数
        self.memory整理_interval_spinbox.grid(row=0, column=1, sticky=tk.W, padx=10, pady=10)
        ttk.Label(memory_frame, text="分钟 (范围: 1-10080，即1分钟到7天)").grid(row=0, column=2, sticky=tk.W, padx=5, pady=10)

        ttk.Label(memory_frame, text="记忆相似度阈值:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
        self.memory_similarity_threshold_var = tk.StringVar(value=str(self.app.config.get("memory_similarity_threshold", 85)))
        self.memory_similarity_threshold_spinbox = tk.Spinbox(memory_frame, from_=1, to=100, textvariable=self.memory_similarity_threshold_var, width=10)
        self.memory_similarity_threshold_spinbox.grid(row=1, column=1, sticky=tk.W, padx=10, pady=10)
        ttk.Label(memory_frame, text="% (范围: 1-100)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=10)

        # 系统提示词设置页面
        prompt_frame = ttk.Frame(notebook)
        notebook.add(prompt_frame, text="提示词设置")

        ttk.Label(prompt_frame, text="系统提示词:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.system_prompt_text = tk.Text(prompt_frame, height=15, width=60)
        self.system_prompt_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 设置当前值
        self.system_prompt_text.insert("1.0", self.app.config.get("system_prompt", ""))

        # 主题设置页面
        theme_frame = ttk.Frame(notebook)
        notebook.add(theme_frame, text="主题设置")

        # 主题选择
        ttk.Label(theme_frame, text="主题选择:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)

        # 创建主题选择变量
        self.dark_theme_var = tk.BooleanVar(value=self.app.config.get("dark_theme", False))

        # 主题选择单选按钮
        light_theme_radio = ttk.Radiobutton(theme_frame, text="浅色主题", variable=self.dark_theme_var, value=False)
        dark_theme_radio = ttk.Radiobutton(theme_frame, text="深色主题", variable=self.dark_theme_var, value=True)

        light_theme_radio.grid(row=0, column=1, sticky=tk.W, padx=(10, 20), pady=10)
        dark_theme_radio.grid(row=0, column=2, sticky=tk.W, padx=10, pady=10)

        # 自动检测系统主题选项
        self.auto_detect_theme_var = tk.BooleanVar(value=self.app.config.get("auto_detect_theme", False))
        auto_detect_check = ttk.Checkbutton(
            theme_frame,
            text="根据系统主题自动调整",
            variable=self.auto_detect_theme_var
        )
        auto_detect_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=10, pady=5)

        # 按钮框架
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # 保存按钮
        save_button = ttk.Button(
            button_frame,
            text="保存",
            command=self.save_settings
        )
        save_button.pack(side=tk.RIGHT, padx=(5, 0))

        # 取消按钮
        cancel_button = ttk.Button(
            button_frame,
            text="取消",
            command=self.window.destroy
        )
        cancel_button.pack(side=tk.RIGHT)
    
    def save_settings(self):
        """保存设置"""
        # 获取系统提示词
        system_prompt = self.system_prompt_text.get("1.0", tk.END).strip()

        # 检测系统主题（如果启用自动检测）
        dark_theme = self.dark_theme_var.get()
        auto_detect_theme = self.auto_detect_theme_var.get()

        if auto_detect_theme:
            # 根据系统主题自动设置
            dark_theme = self.app.detect_system_theme()

        # 创建新的配置字典
        new_config = {
            "api_url": self.api_url_var.get(),
            "api_key": self.api_key_var.get(),
            "model": self.model_var.get(),
            "conversation_save_interval": int(self.conversation_save_interval_var.get()),
            "memory整理_interval": int(self.memory整理_interval_var.get()),
            "memory_similarity_threshold": int(self.memory_similarity_threshold_var.get()),
            "system_prompt": system_prompt,
            "dark_theme": dark_theme,
            "auto_detect_theme": auto_detect_theme
        }

        # 保存配置
        if self.app.save_config(new_config):
            # 应用主题更改
            self.app.is_dark_theme = dark_theme
            self.app.apply_theme()
            messagebox.showinfo("成功", "设置已保存！")
            self.window.destroy()


if __name__ == "__main__":
    try:
        print("正在启动OnPython AI (OPAI)...")
        root = tk.Tk()
        print("Tkinter根窗口已创建")
        app = OPAIApp(root)

        # 检查是否需要根据系统主题自动设置
        if app.config.get("auto_detect_theme", False):
            system_theme = app.detect_system_theme()
            if app.is_dark_theme != system_theme:
                app.is_dark_theme = system_theme
                app.apply_theme()

        # 检查必要库和工具 - 在单独的线程中运行以避免阻塞UI
        check_thread = threading.Thread(target=app.check_required_libs_and_tools)
        check_thread.daemon = True  # 设置为守护线程
        check_thread.start()

        print("OPAI应用实例已创建")
        print("进入主事件循环...")
        root.mainloop()
        print("主事件循环已退出，程序结束")
    except Exception as e:
        print(f"启动OPAI时发生错误: {e}")
        import traceback
        traceback.print_exc()
