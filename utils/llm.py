"""
LLM API調用功能
"""

import time
import asyncio
from typing import Dict, List, Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

from utils.config import client, AVAILABLE_MODELS, TEMPERATURE, model_counter

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

async def call_llm_streaming(
    messages: List[Dict[str, str]],
    temperature: float = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
    retries: int = 3,
    context_info: str = None,  # 添加上下文信息參數，例如"生成主持人中..."
    idle_timeout: int = 30  # 新增數據流空閒超時參數，默認 30 秒
) -> str:
    """調用 LLM API，支持串流響應和自動重試，並檢測長時間無數據的情況"""
    if temperature is None:
        temperature = TEMPERATURE
        
    current_retry = 0
    console = Console()
    tried_fallback = False
    
    while current_retry <= retries:
        try:
            if model is None:
                model = get_next_model()
            
            print(f"正在使用模型: {model}")
            
            # 使用串流模式創建聊天補全
            full_response = ""
            
            # 創建一個上下文標題
            title = context_info if context_info else "AI 正在思考中..."
            
            # 如果之前嘗試流式失敗，直接回退到普通 API 調用
            if tried_fallback:
                console.print(f"[yellow]使用普通 API 調用模式...[/yellow]")
                return await call_llm(messages, temperature, max_tokens, model, retries)
            
            # 創建一個 Live 顯示區域來實時更新內容
            with Live(Panel("正在連接 API...", title=title, border_style="blue"), refresh_per_second=10) as live:
                try:
                    # 初始化變量
                    stream = None
                    stream_task = None
                    idle_check_task = None
                    last_activity_time = time.time()
                    idle_timeout_occurred = False
                    
                    # 定義一個內部函數來檢查空閒狀態
                    async def check_idle_timeout():
                        nonlocal idle_timeout_occurred, stream_task
                        while True:
                            current_idle_time = time.time() - last_activity_time
                            if current_idle_time > idle_timeout:
                                print(f"數據流空閒超過 {idle_timeout} 秒")
                                idle_timeout_occurred = True
                                
                                # 取消主流程任務
                                if stream_task and not stream_task.done():
                                    stream_task.cancel()
                                    
                                # 結束檢查任務
                                return
                                
                            await asyncio.sleep(1)
                    
                    # 定義處理流數據的函數
                    async def process_stream():
                        nonlocal full_response, last_activity_time
                        
                        # 使用異步方法創建聊天補全，啟用串流模式
                        nonlocal stream
                        stream = await client.chat.completions.create(
                            model=model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stream=True  # 啟用串流模式
                        )
                        
                        # 顯示初始連接成功信息
                        live.update(Panel("", title=title, border_style="green"))
                        
                        # 逐步接收並顯示串流內容
                        async for chunk in stream:
                            # 重置空閒計時器
                            last_activity_time = time.time()
                                
                            if not chunk.choices:
                                continue
                                
                            content_delta = chunk.choices[0].delta.content
                            if content_delta is not None:
                                full_response += content_delta
                                # 更新顯示內容 (使用 Markdown 格式)
                                try:
                                    live.update(Panel(Markdown(full_response), title=title, border_style="green"))
                                except Exception:
                                    # 如果 Markdown 解析失敗，使用純文本顯示
                                    live.update(Panel(Text(full_response), title=title, border_style="green"))
                    
                    # 啟動空閒檢查任務
                    idle_check_task = asyncio.create_task(check_idle_timeout())
                    
                    # 啟動流處理任務
                    stream_task = asyncio.create_task(process_stream())
                    
                    # 等待兩個任務中的任何一個完成
                    done, pending = await asyncio.wait(
                        [stream_task, idle_check_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # 檢查是哪個任務完成了
                    for task in done:
                        if task == idle_check_task and idle_timeout_occurred:
                            # 如果是空閒檢查任務完成且檢測到空閒超時
                            raise asyncio.TimeoutError(f"數據流空閒超過 {idle_timeout} 秒")
                        elif task == stream_task:
                            # 如果是流處理任務完成，獲取結果或可能的異常
                            try:
                                await task
                            except Exception as e:
                                raise e
                    
                    # 取消所有尚未完成的任務
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                
                except asyncio.TimeoutError:
                    current_retry += 1
                    if current_retry < retries:
                        console.print(f"[yellow]API 數據流空閒超時 (重試 {current_retry}/{retries})")
                        console.print(f"等待 2 秒後重試...")
                        await asyncio.sleep(2)
                        continue
                    else:
                        raise Exception("API 數據流空閒超時，已達到最大重試次數")
                        
                except Exception as stream_error:
                    # 如果串流模式出錯，提供視覺反饋並在下次迭代嘗試普通 API
                    live.update(Panel(f"串流 API 出錯: {str(stream_error)}\n嘗試使用普通 API...", title=title, border_style="red"))
                    await asyncio.sleep(2)  # 顯示錯誤信息一會兒
                    tried_fallback = True
                    raise ValueError(f"串流模式失敗: {str(stream_error)}")
                finally:
                    # 確保所有任務都被正確取消
                    if 'idle_check_task' in locals() and idle_check_task and not idle_check_task.done():
                        idle_check_task.cancel()
                    if 'stream_task' in locals() and stream_task and not stream_task.done():
                        stream_task.cancel()
            
            # 確保響應不為空
            if not full_response or full_response.strip() == "":
                raise ValueError("收到空回應")
                
            return full_response
            
        except Exception as e:
            current_retry += 1
            error_msg = f"API 串流調用錯誤 (重試 {current_retry}/{retries}): {str(e)}"
            print(error_msg)
            
            # 檢查是否應該回退到普通 API
            if "stream" in str(e).lower() and not tried_fallback:
                print("串流模式不受支持，回退到普通 API 調用...")
                tried_fallback = True
                
            # 如果這是最後一次重試，且我們還沒有嘗試過回退
            if current_retry >= retries and not tried_fallback:
                print("嘗試最後一次使用普通 API 調用...")
                tried_fallback = True
                current_retry -= 1  # 給普通 API 一次機會
                
            # 如果已經嘗試過回退或最後一次重試
            if current_retry > retries:
                print(f"API 串流調用失敗 ({retries}次重試後): {str(e)}")
                # 返回一個應急回應而不是拋出異常
                return f"無法從 AI 模型獲取有效回應。請稍後再試。錯誤: {str(e)}"
            
            # 指數退避重試
            retry_delay = 2 ** current_retry
            print(f"等待 {retry_delay} 秒後重試...")
            await asyncio.sleep(retry_delay) 