"""
YAML處理工具
"""

import yaml

def yaml_safe_load(yaml_str):
    """安全載入 YAML 字符串，處理常見格式問題"""
    try:
        # 直接嘗試載入
        return yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        print(f"YAML 解析錯誤，嘗試修復: {str(e)}")
        
        # 修復常見的冒號缺失問題
        lines = yaml_str.split("\n")
        fixed_lines = []
        
        for line in lines:
            # 如果行以空格開頭後接非空字符，且不包含冒號，則添加冒號
            if line.strip() and line.startswith("  ") and ":" not in line:
                # 檢查該行是否看起來像一個鍵（通常是一個短語）
                fixed_line = line + ":"
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)
        
        fixed_yaml = "\n".join(fixed_lines)
        
        try:
            return yaml.safe_load(fixed_yaml)
        except yaml.YAMLError:
            # 如果仍然失敗，將內容轉換為普通文本格式返回
            print("YAML 修復失敗，轉換為普通文本")
            result = {"text": yaml_str}
            return result 