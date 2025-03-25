import asyncio
from utils import call_llm, call_llm_streaming
import time

async def test_streaming_vs_normal():
    """測試串流 API 與普通 API 的差異"""
    
    # 測試問題
    prompt = "請提供一個 800 字左右的關於人工智能在教育領域應用的詳細分析，包括優勢、挑戰和未來展望。"
    
    print("\n===== 測試普通 API 調用 =====")
    start_time = time.time()
    
    # 普通 API 調用
    normal_response = await call_llm([{"role": "user", "content": prompt}])
    
    normal_time = time.time() - start_time
    print(f"\n完成時間: {normal_time:.2f} 秒")
    print(f"回應長度: {len(normal_response)} 字符")
    
    # 等待一段時間，讓使用者可以查看結果
    await asyncio.sleep(2)
    
    print("\n\n===== 測試串流 API 調用 =====")
    start_time = time.time()
    
    # 串流 API 調用
    streaming_response = await call_llm_streaming(
        [{"role": "user", "content": prompt}],
        context_info="測試串流 API"
    )
    
    streaming_time = time.time() - start_time
    print(f"\n完成時間: {streaming_time:.2f} 秒")
    print(f"回應長度: {len(streaming_response)} 字符")
    
    # 比較結果
    print("\n===== 性能比較 =====")
    print(f"普通 API 時間: {normal_time:.2f} 秒")
    print(f"串流 API 時間: {streaming_time:.2f} 秒")
    
    if streaming_time < normal_time:
        print(f"串流 API 更快，節省了 {normal_time - streaming_time:.2f} 秒 ({(1 - streaming_time/normal_time) * 100:.1f}%)")
    else:
        print(f"普通 API 更快，節省了 {streaming_time - normal_time:.2f} 秒 ({(1 - normal_time/streaming_time) * 100:.1f}%)")
    
    # 比較內容相似度 (簡單比較)
    similarity = sum(1 for a, b in zip(normal_response, streaming_response) if a == b) / max(len(normal_response), len(streaming_response))
    print(f"內容相似度: {similarity * 100:.1f}%")

if __name__ == "__main__":
    asyncio.run(test_streaming_vs_normal()) 