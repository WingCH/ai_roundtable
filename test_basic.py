import pytest
from nodes import InputNode, ModeratorGeneratorNode, AgentGeneratorNode, SessionStartNode, DiscussionNode, SummaryNode
from flow import create_discussion_flow, FlowRunner

def test_node_inheritance():
    """測試節點繼承關係"""
    from pocketflow import Node
    assert issubclass(InputNode, Node)
    assert issubclass(ModeratorGeneratorNode, Node)
    assert issubclass(AgentGeneratorNode, Node)
    assert issubclass(SessionStartNode, Node)
    assert issubclass(DiscussionNode, Node)
    assert issubclass(SummaryNode, Node)

def test_flow_creation():
    """測試流程創建"""
    flow = create_discussion_flow()
    assert isinstance(flow, FlowRunner)
    assert "start" in flow.nodes
    assert isinstance(flow.nodes["start"], InputNode)

if __name__ == "__main__":
    test_node_inheritance()
    test_flow_creation()
    print("所有測試通過！") 