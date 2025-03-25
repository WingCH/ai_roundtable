# AI 圓桌會議系統

這是一個基於 PocketFlow 框架開發的 AI 圓桌會議系統，能夠根據使用者輸入的問題動態生成多位代理人角色，進行深入討論並自動產出最終摘要。系統支援 OpenRouter 平台，可以輪詢使用多個 AI 模型。

## 功能特點

- 動態生成主持人和專家角色
- 智能討論機制和評估
- 動態討論輪次控制
- 觀察者介入機制
- 完整討論記錄保存
- 多模型輪詢支持

## 安裝步驟

1. 克隆專案：
```bash
git clone https://github.com/your-username/ai_roundtable.git
cd ai_roundtable
```

2. 安裝依賴：
```bash
pip install -r requirements.txt
```

3. 設置環境變數：
創建 `.env` 文件並添加：
```
OPENROUTER_API_KEY=your_api_key_here
```

## 使用方法

運行主程式：
```bash
python main.py
```

系統會：
1. 提示您輸入問題
2. 自動生成主持人和專家角色
3. 進行多輪討論 (直到達到充分討論質量)
4. 生成最終摘要
5. 保存完整記錄到 `records` 目錄

## 觀察者輸入

系統支持在討論過程中進行觀察者干預。如果您想在討論中間添加自己的觀點，可以在代碼中設置 `shared["observer_inputs"]` 數組來實現。

## 專案結構

```
ai_roundtable/
├── main.py          # 主程式
├── flow.py          # 流程控制
├── nodes.py         # 核心節點
├── utils.py         # 工具函數
├── requirements.txt # 依賴列表
└── .env             # 環境變數
```

## 依賴套件

- `openai`: 用於 API 調用
- `pyyaml`: 處理 YAML 格式數據
- `python-dotenv`: 讀取環境變數
- `pocketflow`: 核心流程框架
- `asyncio`: 提供異步支持
- `tqdm`: 進度顯示工具

## 已支持的 AI 模型

- `deepseek/deepseek-r1`
- `openai/chatgpt-4o-latest`
- `anthropic/claude-3.7-sonnet`

## 注意事項

- 需要有效的 OpenRouter API 密鑰
- 討論過程可能需要一些時間
- 完整記錄會自動保存為 YAML 格式
- 模型輪詢機制會在不同的請求間切換模型，確保均衡使用
