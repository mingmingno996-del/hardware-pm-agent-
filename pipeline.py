import os
import json
from google import genai
from google.genai import types

# ==========================================
# 0. 网络代理配置
# ==========================================
os.environ['HTTP_PROXY'] = '[http://127.0.0.1:7890](http://127.0.0.1:7890)'
os.environ['HTTPS_PROXY'] = '[http://127.0.0.1:7890](http://127.0.0.1:7890)'

# ==========================================
# 1. 核心配置
# ==========================================
API_KEY =  # 替换为你的真实 Key
client = genai.Client(api_key=API_KEY)

# ==========================================
# 2. System Prompts (整合两个 Agent 的人设)
# ==========================================
PM_INSTRUCTION = """
[Role]
你是一名就职于嘉立创的资深智能硬件产品经理（PM）。你的任务是接待不懂硬件技术的“小白用户”，将他们天马行空的模糊想法，一步步转化为严谨的、可执行的硬件工程需求说明书（PRD）。

[Workflow - 工作流]
1. 倾听与分析：接收用户的想法，迅速在脑海中建立硬件拓扑，分析缺失的关键工程参数（最核心的是：供电方式、尺寸/形态限制、交互方式、是否需要联网）。
2. 启发式提问：以专业、亲和的口吻向用户提问。为了不吓到用户，每次回复最多只问 2 个最关键的选择题或简单问题。
3. 需求收敛与总结：当你认为收集到了足够支撑绘制原理图的信息，或者用户明确表示“你看着办/由你决定”时，停止提问。

[Output Constraints - 最终输出约束]
当你决定收敛需求时，必须输出一份标准化的 JSON 格式硬件规格书，并严格用 ```json 包裹。JSON 必须包含以下字段：
- "Project_Name": 项目名称
- "Power_Supply": 明确的供电方案 (如 "5V Type-C", "3.7V 18650锂电池")
- "Core_Modules": 核心模块列表 (如 ["ESP32主控", "光敏传感器", "继电器"])
- "User_Interaction": 交互方式 (如 "物理按键", "手机蓝牙App")
- "Size_Constraint": 尺寸限制预估 (如 "5cm x 5cm 内")
"""

HW_SYSTEM_PROMPT = """
你是一个严谨且极其专业的资深嵌入式硬件工程师。你的任务是接收标准 JSON 格式的硬件需求文档（PRD），并将其转化为“硬件小白”能直接购买、拼装并烧录运行的工程交付物。

【选型与设计原则】（极其重要）：
1. 模块化优先：绝不让小白去画复杂的原理图。必须选用市面上极其常见、成熟的现成电子模块（如支持直接插杜邦线的模块）。如果涉及到未来进阶的 PCB 走线需求，推荐使用的元器件应在常见的 EDA 工具（如嘉立创EDA）中拥有现成的标准封装。
2. 主控选型：根据 JSON 中的联网需求精准选择。如果有 WiFi/蓝牙，优先 ESP32/ESP8266；如果没有，选用经典的 STM32 最小系统板，确保生成的 C 代码能在 Keil5 等主流 IDE 中顺利编译和调试。
3. 物理定律与防烧毁：引脚分配必须绝对准确。如 I2C 对应 SCL/SDA，模拟量接 ADC 引脚。注意 5V 执行器与 3.3V 主控之间的电平匹配和隔离保护。

【输出格式】
请严格按照以下 Markdown 格式输出方案：

### 1. 🛒 物料清单 (BOM)
### 2. 🔌 傻瓜式接线图
### 3. 💻 基础驱动代码
"""


# ==========================================
# 3. 硬件 Agent (流式生成)
# ==========================================
def run_hardware_agent_stream(prd_json_string):
    print("\n" + "=" * 50)
    print("🛠️ Hardware Agent 已接收 JSON 需求，正在流式输出落地工程方案...")
    print("=" * 50 + "\n")

    config = types.GenerateContentConfig(
        system_instruction=HW_SYSTEM_PROMPT,
        temperature=0.1,  # 极低温度，确保严密逻辑
    )

    prompt = f"这是产品经理交接的 JSON 需求文档，请出具完整的硬件落地方案：\n\n{prd_json_string}"

    # 修改点：使用 generate_content_stream 实现流式输出
    response = client.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config
    )

    # 循环遍历 response，实时打印每个 chunk
    for chunk in response:
        print(chunk.text, end="", flush=True)
    print("\n")


# ==========================================
# 4. PM Agent 对话引擎及总控流水线
# ==========================================
def run_full_pipeline():
    print("==================================================")
    print("🧠 嘉立创 AI 硬件产品经理 (PM Agent) 已上线！")
    print("💡 提示：输入 '退出' 或 'exit' 结束对话。")
    print("==================================================\n")

    chat = client.chats.create(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(
            system_instruction=PM_INSTRUCTION,
            temperature=0.6
        )
    )

    initial_idea = "你好，我想自己做个天黑了就会自动亮的小夜灯，你能帮我规划一下吗？"
    print(f"👤 用户 (你): {initial_idea}")

    try:
        response = chat.send_message(initial_idea)
        print(f"\n👔 PM Agent: \n{response.text}\n")
    except Exception as e:
        print(f"\n❌ 网络通信发生错误，请检查代理设置和 API Key: {e}")
        return

    while True:
        user_input = input("👤 用户 (你): ")

        if user_input.lower() in ['退出', 'exit', 'quit']:
            print("👋 结束会话，期待您的下一个伟大创意！")
            break

        if not user_input.strip():
            continue

        print("⏳ PM 正在思考...")
        try:
            response = chat.send_message(user_input)
            print(f"\n👔 PM Agent: \n{response.text}\n")

            # 修改点：一旦探测到 JSON 格式输出，立即提取并交接给硬件 Agent
            if "```json" in response.text:
                print("✨ 监测到 PM Agent 已输出结构化需求，正在自动交接给硬件工程师...")
                try:
                    # 提取 JSON 字符串
                    json_str = response.text.split("```json")[1].split("```")[0].strip()

                    # 保存文档（可选）
                    parsed_json = json.loads(json_str)
                    with open("PM_Requirement_Spec.json", "w", encoding="utf-8") as f:
                        json.dump(parsed_json, f, indent=4, ensure_ascii=False)
                    print("💾 需求规格书已自动保存。")

                    # 将 JSON 喂给硬件 Agent，并触发流式生成
                    run_hardware_agent_stream(json_str)

                    print("✅ 硬件方案生成完毕，流水线执行结束！")
                    # 修改点：截断对话，退出循环
                    break

                except Exception as e:
                    print(f"⚠️ 数据处理失败，无法完成交接: {e}")

        except Exception as e:
            print(f"\n❌ 网络通信发生错误: {e}")


if __name__ == "__main__":
    run_full_pipeline()