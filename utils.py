import os
import base64
import io
import json
import re
import time
from typing import Dict, Any, Optional

# 图像处理依赖
from pdf2image import convert_from_path
from PIL import Image

# ==============================================================================
# SDK 导入
# ==============================================================================
# 1. Google Gen AI SDK
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import ClientError
except ImportError:
    print("[Warning] google-genai not installed. Gemini models will not work.")
    genai = None

# 2. OpenAI SDK
try:
    from openai import OpenAI, APIError
except ImportError:
    print("[Warning] openai not installed. GPT models will not work.")
    OpenAI = None

# ==============================================================================
# 配置区域 (建议使用环境变量，也可以在此处硬编码)
# ==============================================================================
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'GEMINI_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'sk-OPENAI_API_KEY')
OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1') # 如果使用代理，请修改此处

# 初始化客户端
client_gemini = None
if genai and GEMINI_API_KEY:
    client_gemini = genai.Client(api_key=GEMINI_API_KEY)

client_openai = None
if OpenAI and OPENAI_API_KEY:
    client_openai = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

# ==============================================================================
# 1. PDF 处理工具 (保持不变)
# ==============================================================================
def pdf_pages_to_resized_base64(pdf_path, target_width=1280, target_height=720, fmt="JPEG"):
    """
    将 PDF 的每一页转换为指定分辨率的图片，并编码为 Base64 字符串。
    """
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")
        
        images = convert_from_path(pdf_path, dpi=200, fmt=fmt.lower())
        
        base64_list = []
        for img in images[:10]: # 限制页数
            orig_width, orig_height = img.size
            if target_width:
                scale = target_width / orig_width
            elif target_height:
                scale = target_height / orig_height
            else:
                scale = 1.0
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            resized_img.save(buffer, format=fmt)
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
            base64_list.append(img_base64)
        return base64_list
    except Exception as e:
        print(f"[Error] PDF processing failed: {str(e)}")
        return []

# ==============================================================================
# 2. 双模型 API 调用工具 (核心修改)
# ==============================================================================
def call_gpt_api(
    system_prompt, 
    question, 
    base64_images=[], 
    model="gemini-3-flash-preview", # 默认模型，可传入 "gpt-4o" 切换
    temperature=1.0, 
    max_tokens=4096
):
    """
    统一 API 入口。根据 model 名称自动路由到 Gemini 或 OpenAI。
    """
    # === 分支 1: Gemini 系列 ===
    if "gemini" in model.lower():
        return _call_gemini_internal(system_prompt, question, base64_images, model, temperature, max_tokens)
    
    # === 分支 2: GPT 系列 (OpenAI) ===
    elif "gpt" in model.lower() or "o1" in model.lower():
        return _call_openai_internal(system_prompt, question, base64_images, model, temperature, max_tokens)
    
    else:
        print(f"[Error] Unknown model type: {model}. Please use 'gemini...' or 'gpt...'.")
        return ""

# --- 内部函数: Gemini 实现 ---
def _call_gemini_internal(system_prompt, question, base64_images, model, temperature, max_tokens):
    if not client_gemini:
        print("[Error] Gemini client not initialized. Check imports and API Key.")
        return ""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 1. 准备多模态内容 (PIL Image + Text)
            contents = []
            for img_b64 in base64_images:
                image_data = base64.b64decode(img_b64)
                image = Image.open(io.BytesIO(image_data))
                contents.append(image)
            contents.append(question)
            
            # 2. 配置
            # 注意：Gemini Thinking 模型通常需要较大的 max_tokens (如 8192)
            actual_max_tokens = 8192 if "thinking" in model else max_tokens
            
            generate_config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=actual_max_tokens,
                system_instruction=system_prompt
            )
            
            # 3. 调用
            response = client_gemini.models.generate_content(
                model=model,
                contents=contents,
                config=generate_config
            )
            
            if response.text:
                return response.text
            return ""

        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                delay = 5 * (2 ** attempt)
                print(f"[Gemini] Quota Exceeded. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"[Gemini] Error (Attempt {attempt+1}): {e}")
                time.sleep(2)
    return ""

# --- 内部函数: OpenAI 实现 ---
def _call_openai_internal(system_prompt, question, base64_images, model, temperature, max_tokens):
    if not client_openai:
        print("[Error] OpenAI client not initialized. Check imports and API Key.")
        return ""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 1. 构建 Messages
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # 构建 User Content (混合文本和图片 URL)
            user_content = []
            
            # 图片部分 (OpenAI 需要 base64 data URL)
            for img_b64 in base64_images:
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}",
                        "detail": "high"
                    }
                })
            
            # 文本部分
            user_content.append({
                "type": "text",
                "text": question
            })
            
            messages.append({"role": "user", "content": user_content})
            
            # 2. 调用
            response = client_openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content

        except Exception as e:
            print(f"[OpenAI] Error (Attempt {attempt+1}): {e}")
            time.sleep(2)
            
    return ""

# ==============================================================================
# 3. 决策解析工具
# ==============================================================================
def parse_decision(raw_output: str) -> Dict[str, Any]:
    if not raw_output:
        return {}
    
    raw_output = raw_output.strip()
    
    # 清理 Markdown 代码块
    if raw_output.startswith("```json"):
        raw_output = re.sub(r"^```(?:json)?\s*|```$", "", raw_output, flags=re.MULTILINE).strip()
    if raw_output.startswith("```"): 
        raw_output = re.sub(r"^```\w*\s*|```$", "", raw_output, flags=re.MULTILINE).strip()

    try:
        return _normalize_result(json.loads(raw_output))
    except json.JSONDecodeError:
        pass
    
    # Regex 回退解析
    result = {}
    
    decision_match = re.search(
        r'"final_decision"\s*:\s*"([^"]+)"|'
        r'final[_ ]?decision[:：]\s*(Accept|Reject)', 
        raw_output, re.IGNORECASE
    )
    if decision_match:
        result["final_decision"] = (decision_match.group(1) or decision_match.group(2)).strip()
        
    conf_match = re.search(
        r'"confidence"\s*:\s*"([^"]+)"|' 
        r'confidence[:：]\s*(High|Medium|Low)',
        raw_output, re.IGNORECASE
    )
    if conf_match:
        result["confidence"] = (conf_match.group(1) or conf_match.group(2)).strip()

    if "reasoning" not in result:
        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', raw_output)
        if reasoning_match:
             result["reasoning"] = reasoning_match.group(1)
        else:
             result["raw_output_snippet"] = raw_output[:500] + "..."

    return _normalize_result(result)

def _normalize_result(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "final_decision": _clean_str(data.get("final_decision")),
        "detailed_label": _clean_str(data.get("detailed_label")),
        "final_score": data.get("final_score"),
        "decision_archetype": _clean_str(data.get("decision_archetype")),
        "reasoning": data.get("reasoning", data.get("justification", "No reasoning provided.")),
        "confidence": _clean_str(data.get("confidence")),
    }

def _clean_str(s: Any) -> Optional[str]:
    if s is None: return None
    return str(s).strip()