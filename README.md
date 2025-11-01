# OnPython AI (OPAI) - V0.1 Beta1

**OnPython AI**（简称OPAI）是一个通过调用用户自行填写的API地址、API key与模型名字调用AI，帮助用户编写程序的智能助手软件。它不仅可以与用户对话，帮忙做事情（如编程），还可以在闲时与用户聊天。

## 功能特点

1. **AI对话功能** - 与AI进行自然语言对话，获取编程帮助
2. **系统控制命令** - 支持创建文件夹、文件等系统操作
3. **.opai文件导入** - 可导入.opai文件，自动提取程序命令行用法
4. **记忆库功能** - 记录已导入的程序和对话历史
5. **定期对话总结** - 自动总结对话历史与事件
6. **智能编程助手** - 自动生成To Do列表并按步骤执行
7. **多语言支持** - 支持Python、JavaScript、Java、C++、C等编程语言
8. **系统命令支持** - 支持CMD和PowerShell命令执行
9. **上下文管理** - 保持最近10轮对话的上下文
10. **JSON命令格式** - AI使用JSON格式输出命令，确保准确执行

## 主要界面

- **对话记录框** - 显示与AI的对话历史（占用面积最大的区域）
- **聊天框** - 用户输入消息的区域
- **发送/停止按钮** - 右下角的发送按钮，AI生成时会变成停止生成框
- **设置按钮** - 左下角的设置按钮，点击后弹出设置页面

## 使用方法

### 1. 配置API设置
1. 点击"设置"按钮
2. 在API设置页面填写：
   - API地址（如：https://api.openai.com/v1/chat/completions）
   - API Key
   - 模型名称（如：gpt-3.5-turbo）
3. 在提示词设置页面可以自定义系统提示词
4. 点击"保存"按钮保存配置

### 2. 与AI对话
1. 在聊天框中输入消息
2. 点击"发送"按钮或按Enter发送消息
3. 与AI进行对话，AI会按JSON格式输出命令并执行

### 3. 使用系统命令
支持以下系统命令（AI会自动使用）：
- `create_file` - 创建新文件
- `create_folder` - 创建新文件夹
- `run_python` - 运行Python文件
- `run_javascript` - 运行JavaScript文件
- `run_java` - 运行Java文件
- `run_cpp` - 运行C++文件
- `run_c` - 运行C文件
- `run_cmd` - 运行CMD命令
- `run_powershell` - 运行PowerShell命令
- `read_file` - 读取文件内容
- `list_dir` - 列出目录内容

### 4. 导入.opai文件
1. 点击菜单栏的"文件" -> "导入 .opai 文件"
2. 选择要导入的.opai文件
3. 程序会自动读取com.txt文件了解命令行用法
4. 将.py或.exe文件复制到data/OnPython文件夹
5. 记录在记忆库中供后续使用

### 5. 记忆库功能
程序会自动记录导入的工具和定期总结对话历史，便于后续查找和使用。

## 文件说明

- `config.json` - 存储API配置信息
- `memory.json` - 存储记忆库信息（导入的程序和对话总结）
- `data/OnPython/` - 存储导入的Python或exe程序文件

## 运行要求

- Python 3.6+
- requests库
- tkinter（通常Python内置）

## 常见问题

**Q: 程序无法启动GUI界面？**
A: 请确保运行环境支持GUI显示。在某些服务器或纯命令行环境中可能无法显示界面。

**Q: API调用失败？**
A: 检查API地址、API Key和模型名称是否正确配置，确保网络连接正常。

**Q: 如何使用不同的AI服务（如Ollama、自定义API等）？**
- 对于OpenAI API: API地址使用 https://api.openai.com/v1/chat/completions
- 对于Ollama: API地址使用 http://localhost:11434/v1/chat/completions，模型名称使用 ollama的模型名
- 对于Azure OpenAI: API地址使用你的Azure端点
- 注意不同API提供商的认证方式可能不同

## 安全说明

- 程序会检查高危命令（如删除文件、格式化等）并提示用户
- 高危命令会在执行前显示确认信息
- 建议仅用于可信任的AI模型和可接受的风险范围内