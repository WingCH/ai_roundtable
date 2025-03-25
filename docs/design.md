# AI 圓桌會議系統設計

## 系統概述
AI 圓桌會議系統是一個能夠根據使用者輸入的問題，動態生成多位代理人角色進行多輪討論，並自動產出最終摘要的系統。系統將模擬真實的圓桌會議，讓不同背景和專業領域的 AI 代理人進行深入討論。

## 核心功能
1. 動態生成代理人角色
2. 多輪討論機制
3. 觀點整合與摘要生成
4. 多方觀點呈現
5. 會議記錄管理
6. 進度追蹤與狀態管理
7. 錯誤處理與恢復機制

## 系統架構

### 1. 核心節點設計
```mermaid
classDiagram
    class Node {
        <<interface>>
        +prep(shared)
        +exec(prep_res)
        +post(shared, prep_res, exec_res)
    }
    
    class InputNode {
        -validate_input()
        +prep(shared)
        +exec(prep_res)
        +post(shared, prep_res, exec_res)
    }
    
    class AgentGeneratorNode {
        -generate_moderator()
        -generate_experts()
        +prep(shared)
        +exec(prep_res)
        +post(shared, prep_res, exec_res)
    }
    
    class DiscussionNode {
        -initialize_round()
        -conduct_round()
        -summarize_round()
        +prep(shared)
        +exec(prep_res)
        +post(shared, prep_res, exec_res)
    }
    
    class SummaryNode {
        -generate_summary()
        -format_output()
        +prep(shared)
        +exec(prep_res)
        +post(shared, prep_res, exec_res)
    }
    
    Node <|-- InputNode
    Node <|-- AgentGeneratorNode
    Node <|-- DiscussionNode
    Node <|-- SummaryNode
```

### 2. 數據流設計
```mermaid
flowchart TD
    subgraph 輸入階段
        A[InputNode] -->|接收問題| B[AgentGeneratorNode]
        B -->|生成主持人| C1[ModeratorGenerator]
        B -->|生成專家| C2[ExpertGenerator]
        C1 --> D[DiscussionNode]
        C2 --> D
    end

    subgraph 討論階段
        D -->|初始化討論| E[RoundStart]
        E -->|主持人開場| F[DiscussionRound]
        F -->|專家發言| G[ExpertResponse]
        G -->|專家互動| H[ExpertInteraction]
        H -->|主持人總結| I[RoundSummary]
        I -->|檢查觀察者輸入| J1{有觀察者輸入?}
        J1 -->|是| K1[處理觀察者輸入]
        K1 --> L[評估討論質量]
        J1 -->|否| L
        L -->|評估結果| M{討論是否充分?}
        M -->|否| F
        M -->|是| N[SummaryNode]
    end

    subgraph 輸出階段
        N -->|生成摘要| O[SummaryGenerator]
        O -->|格式化輸出| P[OutputFormatter]
        P -->|保存記錄| Q[RecordSaver]
        Q -->|錯誤處理| R{保存成功?}
        R -->|是| S[完成]
        R -->|否| T[錯誤處理]
        T --> Q
    end

    style 輸入階段 fill:#f9f,stroke:#333,stroke-width:2px
    style 討論階段 fill:#bbf,stroke:#333,stroke-width:2px
    style 輸出階段 fill:#bfb,stroke:#333,stroke-width:2px
```

### 3. 會議流程設計
```mermaid
sequenceDiagram
    participant User as 觀察者
    participant System as 系統
    participant Moderator as 主持人
    participant Experts as 專家們
    participant Storage as 存儲系統
    
    User->>System: 輸入問題
    System->>System: 生成主持人與專家角色
    System->>Moderator: 主持人開場白
    loop 動態討論
        Moderator->>Experts: 提出本輪討論重點
        Experts->>Experts: 輪流發表觀點
        Experts->>Experts: 專家間互動討論
        Moderator->>Experts: 引導討論方向
        Moderator->>System: 總結本輪討論
        System->>System: 評估討論質量
        System->>Storage: 保存本輪記錄
        par 觀察者介入（可選）
            User->>System: 提供補充觀點（可選）
            System->>Moderator: 整合觀察者觀點
            Moderator->>Experts: 引導專家回應
        and 系統評估
            System->>System: 評估討論充分性
        end
        alt 討論不充分
            System->>Moderator: 繼續下一輪
        else 討論充分
            System->>System: 結束討論
        end
    end
    System->>System: 生成最終摘要
    System->>Storage: 保存完整記錄
    System->>User: 輸出會議記錄
```

### 4. 共享數據結構
```python
shared = {
    "question": str,          # 使用者輸入的問題
    "moderator": Dict,        # 主持人信息
    "agents": List[Dict],     # 專家角色列表
    "discussion_history": List[Dict],  # 討論歷史
    "observer_inputs": List[Dict],     # 觀察者輸入記錄
    "summary": str,          # 最終摘要
    "timestamp": str,        # 會議時間戳
    "status": Dict,          # 系統狀態
    "error": Optional[Dict], # 錯誤信息
    "progress": Dict         # 進度信息
}
```

### 5. 代理人角色設計
每個代理人包含：
- 角色名稱
- 專業領域
- 性格特徵
- 觀點立場
- 專業背景描述
- 發言風格
- 互動偏好

## 實現細節

### 1. 代理人生成策略
- 根據問題關鍵字分析所需專業領域
- 確保代理人背景多樣性
- 動態調整代理人數量
- 生成合適的主持人角色
- 角色特徵平衡性檢查
- 避免角色重複或衝突

### 2. 討論機制
- 輪流發言制
- 觀點衝突處理
- 討論深度控制
- 動態評估討論充分性：
  - 觀點覆蓋度評估
  - 討論深度評估
  - 共識達成度評估
  - 分歧點明確性評估
  - 專家參與度評估
- 主持人引導和總結
- 專家互動質量評估
- 討論進度監控
- 動態調整討論策略
- 觀察者介入機制：
  - 完全可選的介入方式
  - 即時接收觀察者輸入（如有）
  - 智能整合觀察者觀點
  - 自然引導專家回應
  - 保持討論流程的連貫性
  - 不影響原有討論節奏

### 3. 摘要生成策略
- 提取關鍵觀點
- 整合不同立場
- 形成共識結論
- 保留重要分歧
- 提供後續建議
- 觀點重要性評估
- 結論可信度分析
- 討論充分性說明

### 4. 記錄管理
- 按時間戳保存記錄
- 結構化 YAML 格式
- 分類存儲討論記錄
- 支持歷史記錄查詢
- 記錄完整性驗證
- 自動備份機制
- 記錄版本控制

### 5. 錯誤處理機制
- 輸入驗證
- API 調用重試
- 異常狀態恢復
- 錯誤日誌記錄
- 用戶友好提示
- 系統狀態監控
- 自動恢復策略

## 技術實現
- 使用 Pocket Flow 框架
- OpenRouter API 進行 LLM 調用
  - 支援多個 AI 模型：
    - deepseek/deepseek-r1
    - openai/chatgpt-4o-latest
    - anthropic/claude-3.7-sonnet
  - 模型分配策略：
    - 輪詢方式平均分配請求
    - 自動負載均衡
    - 模型可用性監控
- YAML 格式處理結構化數據
- 異步處理多輪討論
- 進度顯示和錯誤處理
- 日誌記錄系統
- 性能監控
- 單元測試覆蓋
- 集成測試
- 部署文檔

## 環境配置
1. 安裝依賴：
```bash
pip install -r requirements.txt
```

2. 設置環境變量：
```bash
export OPENROUTER_API_KEY="your-api-key"
```

3. 運行系統：
```bash
python main.py
```

## 注意事項
1. API 使用限制：
   - 需要有效的 OpenRouter API 密鑰
   - 注意 API 調用頻率限制
   - 監控 API 使用成本

2. 模型特性：
   - 不同模型可能有不同的響應時間
   - 模型輸出格式可能略有差異
   - 需要適當的錯誤處理機制

3. 性能優化：
   - 異步處理 API 請求
   - 緩存常用響應
   - 監控系統資源使用
