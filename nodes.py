import asyncio
import traceback
import os
import yaml
import json
from typing import Dict, List, Optional
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown

from utils import call_llm, save_discussion_record

# 動態引入 Node，避免循環引用
try:
    from flow import Node
except ImportError:
    # 用於開發和測試的臨時 Node 類
    class Node:
        """臨時 Node 類，用於開發和測試"""
        async def run_async(self, shared):
            return await self.post_async(shared, None, None)
        
        async def post_async(self, shared, prep_res, exec_res):
            return "default"

class InputNode(Node):
    """接收使用者輸入的問題"""
    
    async def prep_async(self, shared: Dict) -> str:
        return shared.get("question", "")
    
    async def exec_async(self, question: str) -> str:
        # 驗證問題是否存在
        if not question or not question.strip():
            raise ValueError("問題不能為空")
        return question
    
    async def post_async(self, shared: Dict, prep_res: str, exec_res: str) -> str:
        # 問題已經在 main.py 中設置，這裡只是確認一下
        print(f"\n討論問題: {exec_res}\n")
        print("正在生成會議主持人與專家角色...\n")
        return "default"
        
    async def run_async(self, shared: Dict) -> str:
        """為 FlowRunner 系統提供的統一入口"""
        try:
            prep_res = await self.prep_async(shared)
            exec_res = await self.exec_async(prep_res)
            return await self.post_async(shared, prep_res, exec_res)
        except Exception as e:
            print(f"InputNode 執行錯誤: {str(e)}")
            shared["error"] = f"InputNode: {str(e)}"
            return "error"

class ModeratorGeneratorNode(Node):
    """生成主持人角色"""
    
    async def prep_async(self, shared: Dict) -> str:
        return shared["question"]
    
    async def exec_async(self, question: str) -> Dict:
        # 生成主持人
        moderator_prompt = f"""
        根據以下問題，生成一個合適的會議主持人角色：
        問題：{question}
        
        請提供以下信息：
        1. 姓名
        2. 專業背景
        3. 主持風格
        4. 專業領域
        5. 性格特徵
        
        以 YAML 格式輸出：
        ```yaml
        name: 主持人姓名
        background: 專業背景
        style: 主持風格
        expertise: 專業領域
        personality: 性格特徵
        ```
        """
        
        try:
            moderator_response = await call_llm([{"role": "user", "content": moderator_prompt}])
            moderator_yaml = moderator_response.strip().replace("```yaml", "").replace("```", "").strip()
            moderator = yaml.safe_load(moderator_yaml)
            
            # 檢查是否成功解析主持人數據
            if not isinstance(moderator, dict) or not moderator.get('name'):
                print(f"警告: 主持人數據格式不正確，使用默認主持人")
                moderator = {
                    "name": "默認主持人",
                    "background": "跨領域專家",
                    "style": "專業、平衡",
                    "expertise": "多學科整合",
                    "personality": "客觀公正"
                }
            
            return moderator
                
        except Exception as e:
            print(f"生成主持人時發生錯誤: {str(e)}")
            # 返回默認主持人作為備用
            return {
                "name": "預設主持人",
                "background": "跨領域專家",
                "style": "專業、平衡",
                "expertise": "多學科整合",
                "personality": "客觀公正"
            }
    
    async def post_async(self, shared: Dict, prep_res: str, exec_res: Dict) -> str:
        shared["moderator"] = exec_res
        
        # 將主持人信息轉換為 Markdown 格式
        markdown_content = []
        markdown_content.append("## 會議主持人")
        markdown_content.append(f"\n### {exec_res['name']}")
        markdown_content.append(f"- **專業背景**：{exec_res.get('background', '未提供')}")
        markdown_content.append(f"- **主持風格**：{exec_res.get('style', '未提供')}")
        markdown_content.append(f"- **專業領域**：{exec_res.get('expertise', '未提供')}")
        markdown_content.append(f"- **性格特徵**：{exec_res.get('personality', '未提供')}")
        
        # 將 Markdown 內容轉換為字符串
        markdown_string = "\n".join(markdown_content)
        
        # 使用 Rich 顯示 Markdown
        console = Console()
        console.print(Markdown(markdown_string))
        
        return "default"
        
    async def run_async(self, shared: Dict) -> str:
        """為 FlowRunner 系統提供的統一入口"""
        try:
            prep_res = await self.prep_async(shared)
            exec_res = await self.exec_async(prep_res)
            return await self.post_async(shared, prep_res, exec_res)
        except Exception as e:
            print(f"ModeratorGeneratorNode 執行錯誤: {str(e)}")
            shared["error"] = f"ModeratorGeneratorNode: {str(e)}"
            return "error"

class AgentGeneratorNode(Node):
    """生成專家角色"""
    
    async def prep_async(self, shared: Dict) -> str:
        return shared["question"]
    
    async def exec_async(self, question: str) -> List:
        # 生成專家
        experts_prompt = f"""
        根據以下問題，生成 3-5 位相關領域的專家角色：
        問題：{question}
        
        請為每位專家提供以下信息：
        1. 姓名
        2. 專業領域
        3. 專業背景
        4. 性格特徵
        5. 觀點立場
        6. 發言風格
        7. 互動偏好
        
        以 YAML 格式輸出：
        ```yaml
        experts:
          - name: 專家1姓名
            expertise: 專業領域
            background: 專業背景
            personality: 性格特徵
            stance: 觀點立場
            style: 發言風格
            interaction: 互動偏好
          # ... 更多專家
        ```
        """
        
        try:
            experts_response = await call_llm([{"role": "user", "content": experts_prompt}])
            experts_yaml = experts_response.strip().replace("```yaml", "").replace("```", "").strip()
            experts_data = yaml.safe_load(experts_yaml)
            
            # 檢查是否成功解析專家數據
            if not isinstance(experts_data, dict) or not experts_data.get('experts'):
                print(f"警告: 專家數據格式不正確，使用默認專家")
                return [
                    {
                        "name": "專家A",
                        "expertise": "相關領域專家",
                        "background": "資深研究員",
                        "personality": "分析型思考",
                        "stance": "客觀中立",
                        "style": "條理清晰",
                        "interaction": "喜歡深入討論"
                    },
                    {
                        "name": "專家B",
                        "expertise": "相關領域專家",
                        "background": "業界實踐者",
                        "personality": "實用主義",
                        "stance": "務實導向",
                        "style": "直接明了",
                        "interaction": "重視實際應用"
                    },
                    {
                        "name": "專家C",
                        "expertise": "相關領域專家",
                        "background": "理論研究者",
                        "personality": "嚴謹細致",
                        "stance": "理論為本",
                        "style": "學術嚴謹",
                        "interaction": "喜歡探討原理"
                    }
                ]
            
            return experts_data["experts"]
                
        except Exception as e:
            print(f"生成專家時發生錯誤: {str(e)}")
            # 返回默認專家作為備用
            return [
                {
                    "name": "預設專家A",
                    "expertise": "相關領域專家",
                    "background": "資深研究員",
                    "personality": "分析型思考",
                    "stance": "客觀中立",
                    "style": "條理清晰",
                    "interaction": "喜歡深入討論"
                },
                {
                    "name": "預設專家B",
                    "expertise": "相關領域專家",
                    "background": "業界實踐者",
                    "personality": "實用主義",
                    "stance": "務實導向",
                    "style": "直接明了",
                    "interaction": "重視實際應用"
                },
                {
                    "name": "預設專家C",
                    "expertise": "相關領域專家",
                    "background": "理論研究者",
                    "personality": "嚴謹細致",
                    "stance": "理論為本",
                    "style": "學術嚴謹",
                    "interaction": "喜歡探討原理"
                }
            ]
    
    async def post_async(self, shared: Dict, prep_res: str, exec_res: List) -> str:
        shared["agents"] = exec_res
        
        # 將專家信息轉換為 Markdown 格式
        markdown_content = []
        markdown_content.append("## 已生成專家團隊")
        
        for agent in exec_res:
            markdown_content.append(f"\n### {agent['name']}")
            markdown_content.append(f"- **專業領域**：{agent.get('expertise', '未提供')}")
            markdown_content.append(f"- **專業背景**：{agent.get('background', '未提供')}")
            markdown_content.append(f"- **性格特徵**：{agent.get('personality', '未提供')}")
            markdown_content.append(f"- **觀點立場**：{agent.get('stance', '未提供')}")
            markdown_content.append(f"- **發言風格**：{agent.get('style', '未提供')}")
            markdown_content.append(f"- **互動偏好**：{agent.get('interaction', '未提供')}")
        
        # 將 Markdown 內容轉換為字符串
        markdown_string = "\n".join(markdown_content)
        
        # 使用 Rich 顯示 Markdown
        console = Console()
        console.print(Markdown(markdown_string))
        
        print(f"\n總共生成了 {len(exec_res)} 位專家")
        return "default"
        
    async def run_async(self, shared: Dict) -> str:
        """為 FlowRunner 系統提供的統一入口"""
        try:
            prep_res = await self.prep_async(shared)
            exec_res = await self.exec_async(prep_res)
            return await self.post_async(shared, prep_res, exec_res)
        except Exception as e:
            print(f"AgentGeneratorNode 執行錯誤: {str(e)}")
            shared["error"] = f"AgentGeneratorNode: {str(e)}"
            return "error"

class SessionStartNode(Node):
    """準備討論會話"""
    
    async def prep_async(self, shared: Dict) -> Dict:
        return {
            "question": shared["question"],
            "moderator": shared["moderator"],
            "agents": shared["agents"]
        }
    
    async def exec_async(self, data: Dict) -> Dict:
        # 初始化會話記錄
        shared_data = {
            "discussion_history": [],
            "observer_inputs": []
        }
        return shared_data
    
    async def post_async(self, shared: Dict, prep_res: Dict, exec_res: Dict) -> str:
        shared["discussion_history"] = exec_res["discussion_history"]
        shared["observer_inputs"] = exec_res["observer_inputs"]
        
        # 將會話準備信息轉換為 Markdown 格式
        markdown_content = []
        markdown_content.append("# 討論會話準備完成")
        
        # 添加主持人信息
        moderator = shared["moderator"]
        markdown_content.append(f"\n## 本次討論主持人")
        markdown_content.append(f"### {moderator['name']}")
        markdown_content.append(f"- **專業背景**：{moderator.get('background', '未提供')}")
        markdown_content.append(f"- **主持風格**：{moderator.get('style', '未提供')}")
        
        # 添加專家信息摘要
        markdown_content.append(f"\n## 專家小組成員")
        for agent in shared["agents"]:
            markdown_content.append(f"- **{agent['name']}** ({agent.get('expertise', '未提供')})")
        
        markdown_content.append("\n## 開始討論")
        
        # 將 Markdown 內容轉換為字符串並顯示
        markdown_string = "\n".join(markdown_content)
        console = Console()
        console.print(Markdown(markdown_string))
        
        return "default"
    
    async def run_async(self, shared: Dict) -> str:
        """為 FlowRunner 系統提供的統一入口"""
        try:
            prep_res = await self.prep_async(shared)
            exec_res = await self.exec_async(prep_res)
            return await self.post_async(shared, prep_res, exec_res)
        except Exception as e:
            print(f"SessionStartNode 執行錯誤: {str(e)}")
            shared["error"] = f"SessionStartNode: {str(e)}"
            return "error"

class DiscussionNode(Node):
    """管理討論流程"""
    
    async def prep_async(self, shared: Dict) -> Dict:
        return {
            "question": shared["question"],
            "moderator": shared["moderator"],
            "agents": shared["agents"],
            "history": shared.get("discussion_history", []),
            "observer_inputs": shared.get("observer_inputs", [])
        }
    
    async def exec_async(self, data: Dict) -> Dict:
        console = Console()
        
        question = data["question"]
        moderator = data["moderator"]
        agents = data["agents"]
        history = data["history"]
        observer_inputs = data["observer_inputs"]
        
        # 確定當前討論輪次
        current_round = len(history) + 1
        
        # 顯示當前輪次標題
        round_title = f"# 第 {current_round} 輪討論"
        console.print(Markdown(round_title))
        
        # 檢查是否有觀察者輸入
        has_observer_input = len(observer_inputs) > 0 and len(observer_inputs) >= current_round - 1
        observer_input = observer_inputs[current_round - 2] if has_observer_input and current_round > 1 else None
        
        try:
            # 構建開場白或本輪討論重點
            if current_round == 1:
                # 第一輪討論，由主持人開場
                opening_prompt = f"""
                你是一位名為 {moderator['name']} 的討論主持人，具有 {moderator['background']} 背景，主持風格是 {moderator['style']}。
                
                你正在主持一場關於「{question}」的專家圓桌討論。請提供一個開場白，包括：
                1. 對問題的簡要介紹
                2. 討論的重要性和目的
                3. 本輪討論的重點
                
                請直接以主持人的身份發言，無需使用引號或特殊格式。
                """
                
                opening_response = await call_llm([{"role": "user", "content": opening_prompt}])
                
                # 保存開場白
                opening_data = {
                    "role": "moderator",
                    "name": moderator['name'],
                    "opening": opening_response,
                    "focus": "初始討論"
                }
                
            else:
                # 非第一輪，主持人總結上一輪並提出新的討論重點
                previous_round = history[current_round - 2]
                previous_responses = previous_round.get('responses', [])
                previous_summary = previous_round.get('summary', {}).get('summary', '沒有總結')
                
                # 檢查是否有觀察者輸入
                observer_note = ""
                if observer_input:
                    observer_note = f"\n\n此外，有觀察者提出以下觀點或疑問：\n{observer_input}\n請在本輪討論中適當考慮這一觀點。"
                
                new_focus_prompt = f"""
                你是一位名為 {moderator['name']} 的討論主持人，具有 {moderator['background']} 背景，主持風格是 {moderator['style']}。
                
                你正在主持一場關於「{question}」的專家圓桌討論。目前已經進行了 {current_round - 1} 輪討論。
                
                上一輪討論的總結是：
                {previous_summary}
                
                {observer_note}
                
                請提出本輪（第 {current_round} 輪）討論的重點和方向，包括：
                1. 簡要回顧已討論的內容
                2. 指出尚未充分探討的方面
                3. 提出本輪討論應該關注的具體問題或角度
                
                請直接以主持人的身份發言，無需使用引號或特殊格式。
                """
                
                new_focus_response = await call_llm([{"role": "user", "content": new_focus_prompt}])
                
                # 保存本輪討論重點
                opening_data = {
                    "role": "moderator",
                    "name": moderator['name'],
                    "opening": new_focus_response,
                    "focus": f"第 {current_round} 輪討論重點"
                }
            
            # 顯示主持人開場白或引導語
            moderator_md = f"## 主持人 {moderator['name']}\n\n{opening_data['opening']}"
            console.print(Markdown(moderator_md))
            console.print()
            
            # 專家依次發言
            responses = []
            for agent in agents:
                # 構建專家發言提示
                agent_prompt = self._build_agent_prompt(question, moderator, agent, history, current_round, opening_data, observer_input)
                
                # 獲取專家回應
                agent_response = await call_llm([{"role": "user", "content": agent_prompt}])
                
                # 保存專家回應
                response_data = {
                    "role": "agent",
                    "name": agent['name'],
                    "expertise": agent['expertise'],
                    "response": agent_response
                }
                responses.append(response_data)
                
                # 顯示專家發言（Markdown 格式）
                agent_md = f"## {agent['name']} ({agent['expertise']})\n\n{agent_response}"
                console.print(Markdown(agent_md))
                console.print()
            
            # 主持人總結本輪討論
            summary_prompt = f"""
            你是一位名為 {moderator['name']} 的討論主持人，具有 {moderator['background']} 背景，主持風格是 {moderator['style']}。
            
            你正在主持一場關於「{question}」的專家圓桌討論。剛剛結束了第 {current_round} 輪討論，請總結本輪討論的主要觀點和結論。
            
            以下是本輪討論的內容：
            
            討論重點：
            {opening_data['opening']}
            
            專家發言：
            """
            
            for response in responses:
                summary_prompt += f"{response['name']}（{response['expertise']}）: {response['response']}\n\n"
            
            summary_prompt += """
            請提供：
            1. 本輪討論的核心觀點整合
            2. 達成的共識（如果有）
            3. 存在的分歧（如果有）
            
            請直接以主持人的身份發言，無需使用引號或特殊格式。
            """
            
            round_summary = await call_llm([{"role": "user", "content": summary_prompt}])
            
            # 顯示總結（Markdown 格式）
            summary_md = f"## 主持人總結\n\n{round_summary}"
            console.print(Markdown(summary_md))
            console.print()
            
            # 評估討論是否需要繼續
            evaluation_prompt = f"""
            你是一位資深的討論評估專家。請評估以下專家討論是否已經充分探討了主題，是否需要繼續討論。
            
            討論問題：{question}
            
            當前討論輪次：{current_round}
            
            討論歷史摘要：
            """
            
            # 添加歷史討論摘要
            for i, round_data in enumerate(history):
                if round_data.get('summary'):
                    evaluation_prompt += f"第 {i+1} 輪總結：{round_data['summary'].get('summary', '無總結')}\n\n"
            
            # 添加當前輪次總結
            evaluation_prompt += f"""
            本輪總結：{round_summary}
            
            評估討論是否應該結束的標準：
            1. 是否已經全面覆蓋了問題的各個方面
            2. 是否達成了一定程度的共識或清晰地表達了不同觀點
            3. 是否已經提供了足夠的深度分析
            4. 再繼續討論是否會產生實質性的新見解
            
            請回答：「繼續討論」或「結束討論」，並簡要說明理由。
            """
            
            evaluation_response = await call_llm([{"role": "user", "content": evaluation_prompt}])
            
            # 解析評估結果
            should_continue = "繼續討論" in evaluation_response
            
            # 將本輪討論數據整合到歷史中
            round_data = {
                "round_number": current_round,
                "opening": opening_data,
                "responses": responses,
                "summary": {
                    "role": "moderator",
                    "name": moderator['name'],
                    "summary": round_summary
                },
                "evaluation": evaluation_response
            }
            
            return {
                "round_data": round_data,
                "should_continue": should_continue
            }
            
        except Exception as e:
            print(f"討論過程中發生錯誤: {str(e)}")
            return {
                "round_data": {
                    "round_number": current_round,
                    "error": str(e)
                },
                "should_continue": False
            }
    
    def _build_agent_prompt(self, question, moderator, agent, history, current_round, opening_data, observer_input=None):
        """構建專家發言提示"""
        prompt = f"""
        你是一位名為 {agent['name']} 的專家，專業領域是 {agent['expertise']}，具有 {agent['background']} 背景。
        你的性格特徵是 {agent.get('personality', '未提供')}，觀點立場是 {agent.get('stance', '未提供')}。
        你的發言風格是 {agent.get('style', '專業客觀')}，互動偏好是 {agent.get('interaction', '理性交流')}。
        
        你正在參加一場由 {moderator['name']} 主持的關於「{question}」的專家圓桌討論。
        
        以下是當前討論的情況：
        - 這是第 {current_round} 輪討論
        - 主持人提出的本輪討論重點是：{opening_data['opening']}
        """
        
        # 添加歷史討論記錄
        if history and len(history) > 0:
            prompt += "\n先前討論的摘要：\n"
            for i, round_data in enumerate(history):
                prompt += f"第 {i+1} 輪總結：{round_data.get('summary', {}).get('summary', '無總結')}\n"
        
        # 添加觀察者輸入（如果有）
        if observer_input:
            prompt += f"\n有觀察者提出以下觀點或疑問：\n{observer_input}\n請在你的回應中考慮這一觀點。\n"
        
        prompt += """
        請從你的專業角度，針對當前討論重點發表見解，包括：
        1. 你對問題的專業分析
        2. 可能的解決方案或建議
        3. 對其他專家觀點的回應（如果這不是第一輪討論）
        
        請直接以專家的身份發言，無需使用引號或特殊格式。請確保你的回應：
        - 符合你的專業背景和觀點立場
        - 展現你的性格特徵和發言風格
        - 提供有深度的見解而不是泛泛而談
        - 篇幅適中（200-400字左右）
        """
        
        return prompt
    
    async def post_async(self, shared: Dict, prep_res: Dict, exec_res: Dict) -> str:
        # 獲取本輪討論數據和是否應該繼續的標誌
        round_data = exec_res["round_data"]
        should_continue = exec_res["should_continue"]
        
        # 更新共享數據
        if "discussion_history" not in shared:
            shared["discussion_history"] = []
        
        shared["discussion_history"].append(round_data)
        
        # 創建 Rich Console 對象
        console = Console()
        
        # 根據評估結果決定是否繼續討論
        if should_continue:
            evaluation_md = "## 評估結果\n\n討論尚未結束，將繼續進行下一輪討論。"
            console.print(Markdown(evaluation_md))
            console.print()
            return "continue_discussion"
        else:
            evaluation_md = "## 評估結果\n\n討論已經充分展開，準備生成最終摘要。"
            console.print(Markdown(evaluation_md))
            console.print()
            return "end_discussion"
            
    async def run_async(self, shared: Dict) -> str:
        """為 FlowRunner 系統提供的統一入口"""
        try:
            prep_res = await self.prep_async(shared)
            exec_res = await self.exec_async(prep_res)
            return await self.post_async(shared, prep_res, exec_res)
        except Exception as e:
            print(f"DiscussionNode 執行錯誤: {str(e)}")
            shared["error"] = f"DiscussionNode: {str(e)}"
            return "error"

class SummaryNode(Node):
    """生成討論摘要"""
    
    async def prep_async(self, shared: Dict) -> Dict:
        return {
            "question": shared["question"],
            "moderator": shared["moderator"],
            "agents": shared["agents"],
            "discussion_history": shared["discussion_history"],
            "observer_inputs": shared.get("observer_inputs", [])
        }
    
    async def exec_async(self, data: Dict) -> str:
        question = data["question"]
        moderator = data["moderator"]
        agents = data["agents"]
        discussion_history = data["discussion_history"]
        observer_inputs = data["observer_inputs"]
        
        # 構建摘要提示
        summary_prompt = f"""
        你是一位名為 {moderator['name']} 的討論主持人，具有 {moderator['background']} 背景。
        
        你剛剛主持了一場關於「{question}」的專家圓桌討論。討論已經結束，請根據以下討論記錄生成一個全面的最終摘要。
        
        討論包含了 {len(discussion_history)} 輪交流，參與的專家有：
        """
        
        # 添加專家信息
        for agent in agents:
            summary_prompt += f"- {agent['name']}（{agent['expertise']}，{agent.get('stance', '立場未知')}）\n"
        
        summary_prompt += "\n討論歷程：\n"
        
        # 添加討論歷史
        for i, round_data in enumerate(discussion_history):
            summary_prompt += f"\n第 {i+1} 輪討論：\n"
            
            # 添加開場白或重點
            if round_data.get('opening'):
                summary_prompt += f"討論重點：{round_data['opening'].get('opening', '未提供')}\n"
            
            # 添加專家回應摘要
            if round_data.get('responses'):
                summary_prompt += "專家觀點：\n"
                for response in round_data['responses']:
                    summary_prompt += f"- {response['name']}：{response['response']}\n"
            
            # 添加本輪總結
            if round_data.get('summary'):
                summary_prompt += f"本輪總結：{round_data['summary'].get('summary', '未提供')}\n"
            
            # 添加觀察者輸入（如果有）
            if i < len(observer_inputs) and observer_inputs[i]:
                summary_prompt += f"觀察者輸入：{observer_inputs[i]}\n"
        
        summary_prompt += """
        請提供一個全面且結構化的最終摘要，包括：
        1. 問題背景和討論目的
        2. 主要觀點和見解的綜合
        3. 達成的共識
        4. 存在的分歧或未解決的問題
        5. 可能的解決方案或建議
        6. 最終結論
        
        摘要應控制在 600-800 字左右，既全面又簡潔。要突出討論的實質性內容，而不是流程性描述。
        """
        
        try:
            # 生成摘要
            summary = await call_llm([{"role": "user", "content": summary_prompt}], max_tokens=1500)
            return summary
        except Exception as e:
            print(f"生成摘要時發生錯誤: {str(e)}")
            return f"無法生成摘要: {str(e)}"
    
    async def post_async(self, shared: Dict, prep_res: Dict, exec_res: str) -> str:
        # 保存摘要到共享數據
        shared["summary"] = exec_res
        shared["status"] = "completed"
        
        # 構建 Markdown 格式的最終摘要
        markdown_content = []
        markdown_content.append("# 討論最終摘要")
        markdown_content.append(f"\n## 討論問題")
        markdown_content.append(shared["question"])
        markdown_content.append("\n## 討論結論")
        markdown_content.append(exec_res)
        
        # 將 Markdown 內容轉換為字符串並顯示
        markdown_string = "\n".join(markdown_content)
        console = Console()
        console.print(Markdown(markdown_string))
        
        # 顯示完成信息
        complete_md = "\n## 討論已結束"
        console.print(Markdown(complete_md))
        
        # 保存討論記錄
        save_discussion_record(shared)
        
        return "default"
        
    async def run_async(self, shared: Dict) -> str:
        """為 FlowRunner 系統提供的統一入口"""
        try:
            prep_res = await self.prep_async(shared)
            exec_res = await self.exec_async(prep_res)
            return await self.post_async(shared, prep_res, exec_res)
        except Exception as e:
            print(f"SummaryNode 執行錯誤: {str(e)}")
            shared["error"] = f"SummaryNode: {str(e)}"
            return "error"