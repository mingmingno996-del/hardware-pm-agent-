import json
import os
from google import genai
from google.genai import types

os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

# ==========================================
# 1. 核心配置
# ==========================================
API_KEY = "AIzaSyAAr8Y4ykaR_8JfLUpl_wh5sAaYprM-NU0"  # 替换为你的真实 Key
client = genai.Client(api_key=API_KEY)
# 2. 硬件工程师的 System Prompt
HW_SYSTEM_PROMPT = """
你是一个严谨且极其专业的资深嵌入式硬件工程师。你的任务是接收标准 JSON 格式的硬件需求文档（PRD），并将其转化为“硬件小白”能直接购买、拼装并烧录运行的工程交付物。

【选型与设计原则】（极其重要）：
1. 模块化优先：绝不让小白去画复杂的原理图。必须选用市面上极其常见、成熟的现成电子模块（如支持直接插杜邦线的模块）。如果涉及到未来进阶的 PCB 走线需求，推荐使用的元器件应在常见的 EDA 工具（如嘉立创EDA）中拥有现成的标准封装。
2. 主控选型：根据 JSON 中的联网需求精准选择。如果有 WiFi/蓝牙，优先 ESP32/ESP8266；如果没有，选用经典的 STM32 最小系统板，确保生成的 C 代码能在 Keil5 等主流 IDE 中顺利编译和调试。
3. 物理定律与防烧毁：引脚分配必须绝对准确。如 I2C 对应 SCL/SDA，模拟量接 ADC 引脚。注意 5V 执行器与 3.3V 主控之间的电平匹配和隔离保护。

【输出格式】
请严格按照以下 Markdown 格式输出方案：

### 1. 🛒 物料清单 (BOM)
（列出主控板、各模块的具体型号、工作电压。推荐容易采购的现成模块）

### 2. 🔌 傻瓜式接线图
（用 Markdown 表格精确列出：外设模块名称 | 模块引脚 | 连线方向 | 开发板引脚。加粗强调 VCC 和 GND 的正确接法）

### 3. 💻 基础驱动代码
（提供一份结构清晰、带详细中文注释的 C/C++ 代码。包含引脚宏定义、外设初始化和主循环逻辑。）
"""


def run_hardware_agent_v2(prd_json_string):
    print("\n" + "=" * 50)
    print("🛠️ Hardware Agent (新架构版) 已接收需求，正在输出落地工程方案...")
    print("=" * 50 + "\n")

    # 3. 使用 types.GenerateContentConfig 配置指令和温度
    config = types.GenerateContentConfig(
        system_instruction=HW_SYSTEM_PROMPT,
        temperature=0.1,  # 极低温度，确保硬件引脚和代码逻辑严密，不产生幻觉
    )

    prompt = f"这是产品经理交接的 JSON 需求文档，请出具完整的硬件落地方案：\n\n{prd_json_string}"

    # 4. 单次内容生成调用 (One-Shot)
    response = client.models.generate_content(
        model="gemini-2.5-flash",  # 硬件逻辑推理推荐使用 Pro 模型
        contents=prompt,
        config=config
    )

    print(response.text)
    return response.text


if __name__ == "__main__":
    # 模拟 PM Agent 传过来的结构化数据
    mock_json = """
    {
      "project_name": "Smart_Plant_Waterer",
      "power_supply": {
        "type": "plug-in",
        "voltage_hint": "5V USB供电"
      },
      "connectivity": ["WiFi"],
      "inputs": [
        {"type": "sensor", "function": "检测土壤湿度"}
      ],
      "outputs": [
        {"type": "actuator", "function": "抽水电机"}
      ],
      "constraints": {
        "budget": "low",
        "size_requirement": "尽量小巧"
      }
    }
    """

    run_hardware_agent_v2(mock_json)