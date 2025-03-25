from rich.console import Console
from rich.markdown import Markdown

def test_markdown_rendering():
    """測試 Rich Markdown 渲染功能"""
    console = Console()
    
    # 模擬主持人信息
    moderator = {
        "name": "李教授",
        "background": "教育科技專家",
        "style": "引導式討論",
        "expertise": "教育科技整合",
        "personality": "開放思想"
    }
    
    # 模擬專家信息
    agents = [
        {
            "name": "王博士",
            "expertise": "人工智能研究",
            "background": "科技公司研究員",
            "personality": "分析型思考",
            "stance": "技術中立",
            "style": "理性分析",
            "interaction": "數據驅動"
        },
        {
            "name": "張教授",
            "expertise": "教育心理學",
            "background": "大學教育學院",
            "personality": "人文關懷",
            "stance": "學生中心",
            "style": "深入淺出",
            "interaction": "提問引導"
        }
    ]
    
    # 顯示主持人信息
    print("\n=== 測試主持人信息顯示 ===\n")
    
    moderator_md = []
    moderator_md.append("## 會議主持人")
    moderator_md.append(f"\n### {moderator['name']}")
    moderator_md.append(f"- **專業背景**：{moderator.get('background', '未提供')}")
    moderator_md.append(f"- **主持風格**：{moderator.get('style', '未提供')}")
    moderator_md.append(f"- **專業領域**：{moderator.get('expertise', '未提供')}")
    moderator_md.append(f"- **性格特徵**：{moderator.get('personality', '未提供')}")
    
    console.print(Markdown("\n".join(moderator_md)))
    
    # 顯示專家信息
    print("\n=== 測試專家信息顯示 ===\n")
    
    agents_md = []
    agents_md.append("## 已生成專家團隊")
    
    for agent in agents:
        agents_md.append(f"\n### {agent['name']}")
        agents_md.append(f"- **專業領域**：{agent.get('expertise', '未提供')}")
        agents_md.append(f"- **專業背景**：{agent.get('background', '未提供')}")
        agents_md.append(f"- **性格特徵**：{agent.get('personality', '未提供')}")
        agents_md.append(f"- **觀點立場**：{agent.get('stance', '未提供')}")
        agents_md.append(f"- **發言風格**：{agent.get('style', '未提供')}")
        agents_md.append(f"- **互動偏好**：{agent.get('interaction', '未提供')}")
    
    console.print(Markdown("\n".join(agents_md)))
    
    # 顯示討論輪次
    print("\n=== 測試討論輪次顯示 ===\n")
    
    console.print(Markdown("# 第 1 輪討論"))
    console.print(Markdown("## 主持人 李教授\n\n今天我們將討論人工智能對教育的影響。這是一個重要且及時的話題，因為AI技術正迅速變革教育領域。"))
    console.print(Markdown("## 王博士 (人工智能研究)\n\n從技術角度來看，AI可以提供個性化學習體驗，自動化評估，並協助教師處理行政工作。但我們需要確保技術增強而非取代教師的角色。"))
    console.print(Markdown("## 張教授 (教育心理學)\n\n重要的是要考慮AI如何影響學生的社交發展和批判性思維能力。我們應該關注教育的整體目標，而不僅僅是知識傳遞的效率。"))
    console.print(Markdown("## 主持人總結\n\n本輪討論中，我們看到了AI在教育中的潛力和挑戰。專家們一致認為需要平衡技術與人文元素，確保AI輔助教育而非替代教師。"))

if __name__ == "__main__":
    test_markdown_rendering() 