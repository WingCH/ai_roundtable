import os
from typing import Dict, List, Optional
from openai import AsyncOpenAI
import yaml
import json
from datetime import datetime
from dotenv import load_dotenv
import time
import asyncio
from rich.console import Console
from rich.markdown import Markdown

# 載入環境變數
load_dotenv()

# 獲取環境變數
API_KEY = os.getenv("OPENROUTER_API_KEY")
TIMEOUT = int(os.getenv("TIMEOUT", "900"))  # 默認900秒
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))  # 默認0.7

if not API_KEY:
    print("警告: 未設置 OPENROUTER_API_KEY 環境變數")

# 初始化 OpenAI 客戶端（使用異步版本）
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
    timeout=TIMEOUT
)

# 可用的模型列表
AVAILABLE_MODELS = [
    # "deepseek/deepseek-r1",
    # "openai/chatgpt-4o-latest",
    # "anthropic/claude-3.7-sonnet",
    "deepseek/deepseek-chat-v3-0324"
]

# 模型輪詢計數器
model_counter = 0

def get_next_model() -> str:
    """輪詢選擇下一個模型"""
    global model_counter
    model = AVAILABLE_MODELS[model_counter]
    model_counter = (model_counter + 1) % len(AVAILABLE_MODELS)
    return model

async def call_llm(
    messages: List[Dict[str, str]],
    temperature: float = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
    retries: int = 3
) -> str:
    """調用 LLM API，支持自動重試"""
    if temperature is None:
        temperature = TEMPERATURE
        
    current_retry = 0
    
    while current_retry <= retries:
        try:
            if model is None:
                model = get_next_model()
            
            print(f"正在使用模型: {model}")
            
            # 使用異步方法創建聊天補全
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 更安全的結果提取方式
            if not response or not hasattr(response, 'choices') or not response.choices:
                raise ValueError("API 返回無效響應，缺少 choices")
                
            if len(response.choices) == 0:
                raise ValueError("API 返回空的 choices 列表")
                
            first_choice = response.choices[0]
            if not hasattr(first_choice, 'message') or not first_choice.message:
                raise ValueError("API 返回無效的 choice，缺少 message")
                
            if not hasattr(first_choice.message, 'content'):
                raise ValueError("API 返回無效的 message，缺少 content")
            
            content = first_choice.message.content
            if content is None or content.strip() == "":
                raise ValueError("收到空回應")
                
            return content
            
        except Exception as e:
            current_retry += 1
            error_msg = f"API 調用錯誤 (重試 {current_retry}/{retries}): {str(e)}"
            print(error_msg)
            
            # 捕獲特定的錯誤類型並提供更多詳細信息
            if "list index out of range" in str(e):
                print("可能是 API 返回了空響應或響應格式異常")
                if current_retry == retries:
                    # 最後一次嘗試不同的模型
                    print("嘗試切換到不同的模型...")
                    model_index = AVAILABLE_MODELS.index(model) if model in AVAILABLE_MODELS else -1
                    if model_index >= 0:
                        model = AVAILABLE_MODELS[(model_index + 1) % len(AVAILABLE_MODELS)]
            
            if current_retry > retries:
                print(f"API 調用失敗 ({retries}次重試後): {str(e)}")
                # 返回一個應急回應而不是拋出異常
                return f"無法從 AI 模型獲取有效回應。請稍後再試。錯誤: {str(e)}"
            
            # 指數退避重試
            retry_delay = 2 ** current_retry
            print(f"等待 {retry_delay} 秒後重試...")
            await asyncio.sleep(retry_delay)

def save_discussion_record(shared: Dict) -> str:
    """保存討論記錄（YAML 和 Markdown 格式）"""
    try:
        # 確保記錄目錄存在
        os.makedirs("records", exist_ok=True)
        
        # 檢查必要的字段是否存在
        if not shared.get("question"):
            print("警告：缺少討論問題，將使用'未提供問題'替代")
            shared["question"] = "未提供問題"
        
        if not shared.get("moderator"):
            print("警告：缺少主持人信息，將創建默認主持人")
            shared["moderator"] = {"name": "未知主持人", "background": "未提供", "style": "未提供"}
        
        if not shared.get("agents") or len(shared.get("agents", [])) == 0:
            print("警告：缺少專家信息，將創建默認專家")
            shared["agents"] = [{"name": "未知專家", "expertise": "未提供", "background": "未提供", "stance": "未提供"}]
        
        # 設置時間戳（如果不存在）
        if not shared.get("timestamp"):
            shared["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 生成檔案名稱
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        question_slug = shared["question"][:20].replace(" ", "_").replace("/", "_").replace("\\", "_")
        filename_base = f"records/discussion_{question_slug}_{timestamp}"
        yaml_filename = f"{filename_base}.yaml"
        md_filename = f"{filename_base}.md"
        
        # 準備記錄數據
        record = {
            "timestamp": shared["timestamp"],
            "question": shared["question"],
            "moderator": shared["moderator"],
            "agents": shared["agents"],
            "discussion_history": shared.get("discussion_history", []),
            "observer_inputs": shared.get("observer_inputs", []),
            "summary": shared.get("summary", "未生成摘要"),
            "status": shared.get("status", "未知"),
            "error": shared.get("error"),
            "progress": {
                "total_rounds": len(shared.get("discussion_history", [])),
                "completed_rounds": len([r for r in shared.get("discussion_history", []) if r.get("summary") is not None]),
                "has_summary": shared.get("summary") is not None and shared.get("summary") != "未生成摘要"
            }
        }
        
        # 保存為 YAML 檔案
        with open(yaml_filename, "w", encoding="utf-8") as f:
            yaml.dump(record, f, allow_unicode=True, sort_keys=False)
        
        # 生成 Markdown 格式記錄
        md_content = []
        
        # 標題和基本信息
        md_content.append("# AI 圓桌會議完整記錄")
        md_content.append(f"**時間**：{shared['timestamp']}")
        md_content.append(f"**問題**：{shared['question']}")
        md_content.append(f"**狀態**：{shared.get('status', '未知')}")
        
        # 主持人信息
        md_content.append("\n## 主持人")
        moderator = shared["moderator"]
        md_content.append(f"**姓名**：{moderator.get('name', '未知')}")
        md_content.append(f"**背景**：{moderator.get('background', '未提供')}")
        md_content.append(f"**風格**：{moderator.get('style', '未提供')}")
        
        # 專家信息
        md_content.append("\n## 專家團隊")
        for agent in shared["agents"]:
            md_content.append(f"\n### {agent.get('name', '未知專家')}")
            md_content.append(f"- **專業**：{agent.get('expertise', '未提供')}")
            md_content.append(f"- **背景**：{agent.get('background', '未提供')}")
            md_content.append(f"- **立場**：{agent.get('stance', '未提供')}")
        
        # 詳細討論過程
        md_content.append("\n## 討論過程")
        
        for round_data in shared.get("discussion_history", []):
            round_num = round_data.get("round_number", "?")
            md_content.append(f"\n### 第 {round_num} 輪討論")
            
            # 開場白
            opening = round_data.get("opening", {})
            if opening:
                md_content.append("\n#### 主持人開場")
                md_content.append(f"{opening.get('opening', '未提供')}")
                md_content.append(f"\n**討論重點**：{opening.get('focus', '未提供')}")
            
            # 專家發言
            responses = round_data.get("responses", [])
            if responses:
                md_content.append("\n#### 專家發言")
                for resp in responses:
                    if isinstance(resp, dict):
                        agent_name = resp.get("agent", {}).get("name", "未知專家")
                        content = resp.get("content", "未提供發言")
                        md_content.append(f"\n##### {agent_name}")
                        md_content.append(content)
            
            # 本輪總結
            summary = round_data.get("summary", {})
            if summary:
                md_content.append("\n#### 本輪總結")
                md_content.append(f"{summary.get('summary', '未提供總結')}")
        
        # 觀察者輸入
        observer_inputs = shared.get("observer_inputs", [])
        if observer_inputs:
            md_content.append("\n## 觀察者輸入")
            for i, input_data in enumerate(observer_inputs, 1):
                md_content.append(f"\n### 輸入 {i}")
                md_content.append(f"{input_data}")
        
        # 最終總結
        md_content.append("\n## 最終結論")
        md_content.append(shared.get("summary", "未生成摘要"))
        
        # 保存 Markdown 文件
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))
            
        print(f"討論記錄已保存至：\n- YAML: {yaml_filename}\n- Markdown: {md_filename}")
        return yaml_filename
    except Exception as e:
        print(f"保存記錄時發生錯誤：{str(e)}")
        try:
            # 嘗試緊急保存到簡單文件
            emergency_file = f"records/emergency_backup_{int(time.time())}.json"
            with open(emergency_file, "w", encoding="utf-8") as f:
                json.dump(shared, f, ensure_ascii=False, default=str)
            print(f"已創建緊急備份：{emergency_file}")
        except:
            print("無法創建緊急備份")
        return None

def print_summary(shared: Dict) -> None:
    """格式化並打印會議摘要（使用 Rich 庫渲染 Markdown）"""
    try:
        # 創建 Rich Console 對象
        console = Console()
        
        # 構建 Markdown 格式的摘要字符串
        markdown_content = []
        
        # 標題和基本信息
        markdown_content.append("# AI 圓桌會議摘要")
        
        # 獲取基本信息，使用安全的訪問方式
        timestamp = shared.get('timestamp', '未記錄')
        question = shared.get('question', '未提供討論主題')
        markdown_content.append(f"**會議時間**：{timestamp}")
        markdown_content.append(f"**討論主題**：{question}")
        
        # 處理主持人信息
        markdown_content.append("\n## 主持人")
        moderator = shared.get("moderator", {})
        if isinstance(moderator, dict):
            markdown_content.append(f"- **姓名**：{moderator.get('name', '未知')}")
            markdown_content.append(f"- **專業背景**：{moderator.get('background', '未提供')}")
            markdown_content.append(f"- **主持風格**：{moderator.get('style', '未提供')}")
        else:
            markdown_content.append("- 主持人信息無效")
        
        # 處理專家信息
        agents = shared.get("agents", [])
        if agents and isinstance(agents, list):
            markdown_content.append("\n## 專家")
            for agent in agents:
                if not isinstance(agent, dict):
                    continue
                markdown_content.append(f"\n### {agent.get('name', '未知專家')}")
                markdown_content.append(f"- **專業領域**：{agent.get('expertise', '未提供')}")
                markdown_content.append(f"- **專業背景**：{agent.get('background', '未提供')}")
                markdown_content.append(f"- **觀點立場**：{agent.get('stance', '未提供')}")
        
        # 處理討論歷史
        discussion_history = shared.get("discussion_history", [])
        if discussion_history and isinstance(discussion_history, list):
            markdown_content.append("\n## 討論重點")
            for round_data in discussion_history:
                if not isinstance(round_data, dict):
                    continue
                markdown_content.append(f"\n### 第 {round_data.get('round_number', '?')} 輪")
                opening = round_data.get('opening', {})
                if opening and isinstance(opening, dict):
                    markdown_content.append(f"- **開場**：{opening.get('opening', '未提供')}")
                    markdown_content.append(f"- **重點**：{opening.get('focus', '未提供')}")
                
                round_summary = round_data.get('summary', {})
                if round_summary and isinstance(round_summary, dict):
                    markdown_content.append(f"- **總結**：{round_summary.get('summary', '未提供')}")
        
        # 處理總結
        summary = shared.get("summary")
        if summary:
            markdown_content.append("\n## 最終結論")
            markdown_content.append(summary)
        else:
            markdown_content.append("\n## 最終結論")
            markdown_content.append("未生成最終結論")
            
        # 討論狀態
        status = shared.get("status", "未知")
        markdown_content.append(f"\n**討論狀態**：{status}")
        
        # 顯示錯誤（如果有）
        error = shared.get("error")
        if error:
            markdown_content.append(f"\n**討論錯誤**：{error}")
        
        # 轉換為 Markdown 字符串
        markdown_string = "\n".join(markdown_content)
        
        # 保存 Markdown 文件
        os.makedirs("records", exist_ok=True)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_filename = f"records/summary_{current_time}.md"
        
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(markdown_string)
        
        # 使用 Rich 庫渲染 Markdown
        markdown = Markdown(markdown_string)
        console.print(markdown)
        
        # 顯示保存信息
        print(f"\n摘要已保存為 Markdown 文件：{md_filename}")
            
    except Exception as e:
        print(f"打印摘要時發生錯誤：{str(e)}") 