import os
import json
import time
from google import genai
from google.genai import types, errors

# ==========================================
# 0. 网络代理与 API 配置
# ==========================================
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

API_KEY = "AIzaSyAAr8Y4ykaR_8JfLUpl_wh5sAaYprM-NU0"  # 你的真实 Key
client = genai.Client(api_key=API_KEY)


# ==========================================
# 增强模块：带自动重试的发送函数
# ==========================================
def safe_send_message(chat_session, prompt_text):
    """安全地发送消息，遇到 429 报错会自动等待 60 秒后重试"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return chat_session.send_message(prompt_text)
        except errors.ClientError as e:
            if e.code == 429:
                print(
                    f"\n⚠️ [警告] 触发 API 频率限制 (429)。程序将暂停 60 秒后自动重试 ({attempt + 1}/{max_retries})...")
                time.sleep(60)
            else:
                print(f"\n❌ 发生不可恢复的 API 错误: {e}")
                raise e
    raise Exception("多次重试均失败，API 额度可能已耗尽。")


# ==========================================
# 1. 本地数据库查询函数
# ==========================================
def local_database_query(keywords: list) -> str:
    """本地模拟查库，返回格式化好的真实物料与引脚信息文本"""
    print(f"\n[⚙️ 本地脚本执行] 正在查询底层物料及引脚: {keywords} ...")

    mock_db = {
        "ESP32": {"c_code": "C2920153", "model": "ESP32-C3-MINI-1",
                  "pinout": "VDD:3.3V, GND:GND, IO4:ADC引脚, IO5:PWM引脚"},
        "光敏": {"c_code": "C123456", "model": "GL5528 (光敏电阻)",
                 "pinout": "Pin_1:VCC, Pin_2:GND, Pin_3:AO(模拟输出)"},
        "10k": {"c_code": "C25804", "model": "10KΩ ±1% 0603", "pinout": "无极性电阻"}
    }

    result_text = "【立创商城真实数据库返回结果】\n"
    for kw in keywords:
        found = False
        for key, value in mock_db.items():
            if key.lower() in kw.lower():
                result_text += f"- 关键词 '{kw}' 匹配成功: 型号={value['model']}, C编号={value['c_code']}, 引脚定义=[{value['pinout']}]\n"
                found = True
                break
        if not found:
            result_text += f"- 关键词 '{kw}' 未找到匹配项，请提示用户注意。\n"

    return result_text


# ==========================================
# 2. 核心工作流：Pipeline 版
# ==========================================
def run_hardware_agent_pipeline(prd_json_string):
    print("\n" + "=" * 50)
    print("🛠️ Hardware Agent (Pipeline版) 已启动，开始解析需求...")
    print("=" * 50)

    # --------------------------------------------------
    # 第一步：提取物料关键词
    # --------------------------------------------------
    extract_instruction = """
    你是一个需求分析助手。请阅读用户的 PRD JSON，提取出需要采购的核心元器件。
    你必须且只能输出一个包含元器件名称的 JSON 数组，并严格用 ```json 包裹。
    例如：["ESP32主控", "光敏传感器", "10k下拉电阻"]
    """

    chat_step1 = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=extract_instruction, temperature=0.1)
    )

    print("\n⏳ 正在让 AI 提取元器件清单...")
    # 使用安全的发送函数
    response_step1 = safe_send_message(chat_step1, f"PRD需求：\n{prd_json_string}")

    try:
        json_str = response_step1.text.split("```json")[1].split("```")[0].strip()
        keywords_list = json.loads(json_str)
    except Exception as e:
        print(f"❌ JSON 解析失败，AI 返回格式异常: {response_step1.text}")
        return

    # --------------------------------------------------
    # 第二步：本地执行查库
    # --------------------------------------------------
    db_result_text = local_database_query(keywords_list)
    print(db_result_text)

    # --------------------------------------------------
    # 第三步：生成最终工程报告
    # --------------------------------------------------
    final_instruction = """
    你是一个严谨的嵌入式硬件工程师。
    我会提供给你一份【原始 PRD 需求】和一份【真实数据库查询结果】。

    【强制要求】：
    1. 必须根据【真实数据库查询结果】里的 C编号和引脚定义来生成方案，绝不捏造！
    2. 如果数据库说某个器件没找到，就在 BOM 中标注“需人工核对”。

    【输出格式】
    ### 1. 🛒 经验证的物料清单 (BOM)
    ### 2. 🔌 傻瓜式接线图
    """

    chat_step2 = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(system_instruction=final_instruction, temperature=0.1)
    )

    final_prompt = f"【原始 PRD 需求】\n{prd_json_string}\n\n{db_result_text}\n\n请出具最终的硬件工程方案。"

    print("\n⏳ 正在根据真实物料生成 BOM 和接线图...")
    # 再次使用安全的发送函数
    response_step2 = safe_send_message(chat_step2, final_prompt)

    print("\n" + "=" * 50)
    print("✅ 最终输出的可靠工程方案：\n")
    print(response_step2.text)
    print("=" * 50 + "\n")


if __name__ == "__main__":
    mock_json = """
    {
      "Project_Name": "智能感光小夜灯",
      "Power_Supply": "5V Type-C",
      "Core_Modules": [
        "ESP32主控",
        "光敏传感器",
        "10k下拉电阻"
      ]
    }
    """
    run_hardware_agent_pipeline(mock_json)