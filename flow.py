import asyncio
from pocketflow import Flow, AsyncFlow, Node

class FlowRunner:
    """流程運行器"""
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        
    def add_node(self, name, node):
        """添加節點"""
        self.nodes[name] = node
        self.edges[name] = {}
        
    def add_edge(self, src, dst, cond=None):
        """添加邊"""
        self.edges[src][cond] = dst
        
    async def run_async(self, shared):
        """運行整個流程（異步版本）"""
        current = "start"
        max_steps = 50  # 防止可能的無限循環
        step_count = 0
        
        while current != "end" and step_count < max_steps:
            step_count += 1
            print(f"執行節點: {current}")
            
            try:
                node = self.nodes.get(current)
                if not node:
                    raise ValueError(f"找不到節點: {current}")
                
                action = await node.run_async(shared)
                
                # 檢查 action 是否為有效值
                if action is None:
                    print(f"警告: 節點 {current} 返回了 None 作為動作，使用默認動作 'default'")
                    action = "default"
                
                # 檢查是否有指向下一個節點的邊
                if current in self.edges:
                    if action in self.edges[current]:
                        current = self.edges[current][action]
                    elif "default" in self.edges[current]:
                        print(f"警告: 找不到動作 '{action}' 的邊，使用默認邊")
                        current = self.edges[current]["default"]
                    else:
                        print(f"錯誤: 節點 {current} 無法處理動作 '{action}'，流程結束")
                        current = "end"
                else:
                    print(f"警告: 節點 {current} 沒有任何出邊，流程結束")
                    current = "end"
                    
            except Exception as e:
                error_msg = f"節點 {current} 執行時出錯: {str(e)}"
                print(f"錯誤: {error_msg}")
                shared["error"] = error_msg
                shared["status"] = "error"
                current = "end"  # 結束流程
        
        if step_count >= max_steps:
            print(f"警告: 流程執行超過最大步數 {max_steps}，強制結束")
            shared["error"] = f"流程執行超過最大步數 {max_steps}"
            shared["status"] = "exceeded_max_steps"
            
        return shared

class EndNode:
    """表示流程結束的節點"""
    async def run_async(self, shared):
        from rich.console import Console
        from rich.markdown import Markdown
        
        console = Console()
        end_md = "# 討論流程已結束"
        console.print(Markdown(end_md))
        
        if not shared.get("status"):
            shared["status"] = "completed"
        return "end"

def create_discussion_flow():
    """創建完整的討論流程"""
    # 動態引入，避免循環引用
    from nodes import InputNode, ModeratorGeneratorNode, AgentGeneratorNode, SessionStartNode, DiscussionNode, SummaryNode
    
    flow = FlowRunner()
    
    # 創建節點
    flow.add_node("start", InputNode())
    flow.add_node("generate_moderator", ModeratorGeneratorNode())
    flow.add_node("generate_agents", AgentGeneratorNode())
    flow.add_node("session_start", SessionStartNode())
    flow.add_node("discussion", DiscussionNode())
    flow.add_node("summary", SummaryNode())
    flow.add_node("end", EndNode())
    
    # 創建邊
    flow.add_edge("start", "generate_moderator", "default")
    flow.add_edge("generate_moderator", "generate_agents", "default")
    flow.add_edge("generate_agents", "session_start", "default")
    flow.add_edge("session_start", "discussion", "default")
    flow.add_edge("discussion", "summary", "end_discussion")
    flow.add_edge("discussion", "discussion", "continue_discussion")
    flow.add_edge("summary", "end", "default")
    
    return flow