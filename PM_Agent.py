import os
import json
from google import genai
from google.genai import types

# ==========================================
# 0. 网络代理配置 (解决国内 400 报错)
# 注意：请将 7890 替换为你自己代理软件的实际本地端口！
# ==========================================
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

# ==========================================
# 1. 核心配置
# ==========================================
API_KEY = "AIzaSyAAr8Y4ykaR_8JfLUpl_wh5sAaYprM-NU0"  # 替换为你的真实 Key
client = genai.Client(api_key=API_KEY)

# ==========================================
# 2. 注入产品经理的灵魂 (System Prompt)
# ==========================================
pm_instruction = """
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


# ==========================================
# 3. 启动交互式聊天引擎
# ==========================================
def run_pm_agent():
    print("==================================================")
    print("🧠 嘉立创 AI 硬件产品经理 (PM Agent) 已上线！")
    print("💡 提示：输入 '退出' 或 'exit' 结束对话。")
    print("==================================================\n")

    # 创建带有记忆的多轮对话 Session
    chat = client.chats.create(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(
            system_instruction=pm_instruction,
            temperature=0.6
        )
    )

    # 模拟用户开启话题
    initial_idea = "你好，我想自己做个天黑了就会自动亮的小夜灯，你能帮我规划一下吗？"
    print(f"👤 用户 (你): {initial_idea}")

    try:
        response = chat.send_message(initial_idea)
        print(f"\n👔 PM Agent: \n{response.text}\n")
    except Exception as e:
        print(f"\n❌ 网络通信发生错误，请检查代理设置和 API Key: {e}")
        return

    # 进入持续交互循环
    while True:
        user_input = input("👤 用户 (你): ")

        if user_input.lower() in ['退出', 'exit', 'quit']:
            print("👋 结束会话，期待您的下一个伟大创意！")
            break

        if not user_input.strip():
            continue

        print("⏳ PM 正在思考...")
        try:
            # 这里的 try 是捕捉网络错误的（外层 try）
            response = chat.send_message(user_input)
            print(f"\n👔 PM Agent: \n{response.text}\n")

            # 如果 PM Agent 输出了最终的 JSON，就自动保存下来并生成 Prompt
            if "```json" in response.text:
                print("✨ 监测到 PM Agent 已输出结构化需求，正在提取并保存...")
                try:
                    # 这里的 try 是捕捉 JSON 解析错误的（内层 try）
                    json_str = response.text.split("```json")[1].split("```")[0].strip()
                    parsed_json = json.loads(json_str)

                    # 1. 保存结构化 PRD 文档
                    with open("PM_Requirement_Spec.json", "w", encoding="utf-8") as f:
                        json.dump(parsed_json, f, indent=4, ensure_ascii=False)
                    print("💾 需求规格书已成功保存至 PM_Requirement_Spec.json")

                    # 2. 自动将其转化为发给 main.py 的“完美提示词”
                    modules_str = "、".join(parsed_json.get("Core_Modules", []))
                    final_prompt = (
                        f"请帮我生成一个【{parsed_json.get('Project_Name', '智能硬件')}】的立创EDA网表。\n"
                        f"具体硬件工程需求如下：\n"
                        f"1. 供电方案：{parsed_json.get('Power_Supply', '常规供电')}\n"
                        f"2. 核心模块与元器件需包含：{modules_str}\n"
                        f"3. 用户交互：{parsed_json.get('User_Interaction', '无')}\n"
                        f"4. 物理尺寸限制：{parsed_json.get('Size_Constraint', '无限制')}\n\n"
                        "请你为上述需求分配合适的具体芯片型号（如低功耗MCU、充电管理IC等）及外围阻容，并输出标准的 Components 和 Nets 的 JSON 结构。"
                    )

                    print("\n==================================================")
                    print("🚀 自动生成的【底层架构师提示词】如下，请直接复制给 main.py 执行：")
                    print("--------------------------------------------------")
                    print(final_prompt)
                    print("--------------------------------------------------")
                    print("==================================================\n")

                except Exception as e:  # 结束内层 try
                    print(f"⚠️ 数据处理失败，可能是格式不标准: {e}")

        except Exception as e:  # 结束外层 try（你之前可能漏掉了这几行）
            print(f"\n❌ 网络通信发生错误: {e}")


if __name__ == "__main__":
    run_pm_agent()