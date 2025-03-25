import asyncio
import traceback
import os
import time
from datetime import datetime
from flow import create_discussion_flow
from utils import print_summary, save_discussion_record

MAX_RETRIES = 3
DISCUSSION_TIMEOUT = int(os.getenv("TIMEOUT", "900"))  # 默認15分鐘

def validate_question(question: str) -> bool:
    """驗證問題是否有效"""
    if not question or not question.strip():
        return False
    if len(question.strip()) < 10:
        return False
    return True

async def main():
    """主函數"""
    # 歡迎信息
    print("\n=== AI 圓桌會議系統 ===")
    print("請輸入您想要討論的問題（至少10個字符）：")
    
    # 獲取並驗證問題
    question = input("> ").strip()
    retry_count = 0
    while not validate_question(question) and retry_count < 3:
        retry_count += 1
        print(f"錯誤: 問題太短或為空！請輸入更詳細的問題（嘗試 {retry_count}/3）：")
        question = input("> ").strip()
        
    if not validate_question(question):
        print("錯誤: 提供的問題不符合要求，程序結束")
        return
    
    # 準備日誌目錄
    os.makedirs("logs", exist_ok=True)
    log_file = f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 初始化共享數據
    shared = {
        "question": question,
        "moderator": None,
        "agents": None,
        "discussion_history": [],
        "observer_inputs": [],
        "summary": None,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "initializing",
        "start_time": time.time()
    }
    
    # 記錄基本信息
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 開始討論: {question}\n")
    
    overall_start_time = time.time()
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            # 更新狀態
            shared["status"] = "running"
            if retry_count > 0:
                print(f"\n正在重試討論流程 (嘗試 {retry_count+1}/{MAX_RETRIES})...")
                
            # 創建流程
            flow = create_discussion_flow()
            
            # 運行流程（帶超時）
            try:
                print("\n正在開始討論流程...\n")
                await asyncio.wait_for(flow.run_async(shared), timeout=DISCUSSION_TIMEOUT)
                
                # 流程完成，檢查結果
                if shared.get("status") == "completed" and shared.get("summary"):
                    break  # 成功完成
                    
            except asyncio.TimeoutError:
                print(f"\n警告: 討論流程超時（{DISCUSSION_TIMEOUT}秒），系統將嘗試生成部分摘要")
                shared["error"] = f"討論流程超時（{DISCUSSION_TIMEOUT}秒）"
                shared["status"] = "timeout"
                
                # 記錄超時信息
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 討論超時\n")
            
            # 檢查專家和主持人是否生成
            if not shared.get("moderator"):
                print("\n警告: 未能生成主持人")
                shared["error"] = "未能生成主持人"
                retry_count += 1
                continue
                
            if not shared.get("agents") or len(shared.get("agents", [])) < 2:
                print("\n警告: 未能生成足夠的專家")
                shared["error"] = "未能生成足夠的專家"
                retry_count += 1
                continue
            
            # 檢查討論歷史
            if not shared.get("discussion_history") or len(shared.get("discussion_history", [])) < 1:
                print("\n警告: 討論未能產生有效內容")
                shared["error"] = "討論未能產生有效內容"
                retry_count += 1
                continue
                
            # 如果沒有生成摘要，但有討論歷史，則嘗試生成摘要
            if not shared.get("summary") and shared.get("discussion_history"):
                from nodes import SummaryNode
                try:
                    print("\n嘗試從討論歷史生成摘要...")
                    summary_node = SummaryNode()
                    await summary_node.run_async(shared)
                    if shared.get("summary"):
                        shared["status"] = "completed"
                        break  # 成功生成摘要
                except Exception as e:
                    print(f"\n生成摘要時發生錯誤: {str(e)}")
                    shared["error"] = f"生成摘要錯誤: {str(e)}"
            
            # 增加重試次數
            retry_count += 1
            
            # 如果還有重試機會，等待短暫時間後重試
            if retry_count < MAX_RETRIES:
                wait_time = 5 * retry_count  # 每次重試增加等待時間
                print(f"\n將在 {wait_time} 秒後重試...")
                await asyncio.sleep(wait_time)
                
        except Exception as e:
            error_message = f"討論流程錯誤: {str(e)}"
            print(f"\n{error_message}")
            print("\n詳細錯誤信息:")
            traceback.print_exc()
            
            # 記錄錯誤信息
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_message}\n")
                f.write(traceback.format_exc())
            
            shared["error"] = error_message
            shared["status"] = "error"
            
            # 增加重試次數
            retry_count += 1
            
            # 如果還有重試機會，等待短暫時間後重試
            if retry_count < MAX_RETRIES:
                wait_time = 5 * retry_count
                print(f"\n將在 {wait_time} 秒後重試...")
                await asyncio.sleep(wait_time)
    
    # 計算總時間
    total_time = time.time() - overall_start_time
    shared["total_time"] = f"{total_time:.1f}秒"
    
    # 檢查最終結果
    if shared.get("summary"):
        shared["status"] = "completed" if shared.get("status") != "timeout" else "partial"
        print_summary(shared)
        print(f"\n討論共花費了 {shared['total_time']}")
    else:
        print("\n錯誤: 經過多次嘗試，討論仍未能生成摘要")
        shared["status"] = "failed"
    
    # 保存記錄
    record_file = save_discussion_record(shared)
    if record_file:
        print(f"\n完整討論記錄已保存，您可以查看 Markdown 格式文件了解詳細內容。")
    else:
        print("\n警告: 無法保存完整討論記錄")
    
    # 記錄完成信息
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 討論結束，狀態: {shared.get('status')}\n")

if __name__ == "__main__":
    asyncio.run(main())