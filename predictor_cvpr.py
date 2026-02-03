import json
import os
from utils import pdf_pages_to_resized_base64, call_gpt_api, parse_decision
from prompt_cvpr import (
    PROMPT_REVIEW_SYNTHESIZER_CVPR,
    PROMPT_REBUTTAL_ANALYZER_CVPR,
    PROMPT_DECISION_COORDINATOR_CVPR
)

# 配置您的模型名称
# MODEL_NAME = "gemini-3-flash-preview"
MODEL_NAME = "gpt-5.2-2025-12-11" 

def preprocess_reviews(reviews_data):
    """
    格式化审稿人意见，提取关键字段供 Agent 阅读
    """
    formatted_reviews = []
    for idx, r in enumerate(reviews_data):
        formatted_reviews.append({
            "id": f"Reviewer {idx+1}",
            "summary": r.get("Paper Summary", ""),
            "strengths": r.get("Paper Strengths", ""),
            "major_weaknesses": r.get("Major Weaknesses", ""),
            "minor_weaknesses": r.get("Minor Weaknesses", ""),
            "recommendation": r.get("Preliminary Recommendation", ""),
            "justification": r.get("Justification For Recommendation And Suggestions For Rebuttal", ""),
            "confidence": r.get("Confidence Level", "")
        })
    return formatted_reviews

def run_cvpr_prediction(reviews_json_path, rebuttal_pdf_path):
    print(f"[*] Starting CVPR 2026 Prediction Pipeline...")
    
    # 1. 加载数据
    with open(reviews_json_path, 'r', encoding='utf-8') as f:
        reviews_raw = json.load(f)
    
    formatted_reviews = preprocess_reviews(reviews_raw)
    print(f"[*] Loaded {len(formatted_reviews)} reviews.")

    # 2. Agent 1: 分析审稿意见
    print(f"[*] Agent 1: Analyzing Reviews...")
    agent1_res = call_gpt_api(
        system_prompt=PROMPT_REVIEW_SYNTHESIZER_CVPR,
        question=f"Analyze these CVPR reviews: {json.dumps(formatted_reviews)}",
        model=MODEL_NAME
    )
    # print(f"DEBUG Agent 1: {agent1_res}")

    # 3. Agent 2: 分析 Rebuttal PDF (视觉 + 文本)
    print(f"[*] Agent 2: Analyzing Rebuttal PDF (Visual Evidence)...")
    rebuttal_images = []
    if os.path.exists(rebuttal_pdf_path):
        rebuttal_images = pdf_pages_to_resized_base64(rebuttal_pdf_path)
        print(f"[*] Converted PDF to {len(rebuttal_images)} images.")
    else:
        print(f"[!] Warning: Rebuttal PDF not found at {rebuttal_pdf_path}")

    rebuttal_context = {
        "review_concerns": agent1_res # 传入 Agent 1 的分析结果作为上下文
    }
    
    agent2_res = call_gpt_api(
        system_prompt=PROMPT_REBUTTAL_ANALYZER_CVPR,
        question=f"Analyze the rebuttal effectiveness based on attached PDF figures. Context: {json.dumps(rebuttal_context)}",
        base64_images=rebuttal_images, # 传入图片
        model=MODEL_NAME
    )
    # print(f"DEBUG Agent 2: {agent2_res}")

    # 4. Agent 3: 最终决策
    print(f"[*] Agent 3: Making Final Decision...")
    final_input = {
        "review_analysis": agent1_res,
        "rebuttal_analysis": agent2_res,
        "raw_scores": [r['recommendation'] for r in formatted_reviews]
    }

    decision_raw = call_gpt_api(
        system_prompt=PROMPT_DECISION_COORDINATOR_CVPR,
        question=f"Make the final CVPR 2026 decision: {json.dumps(final_input)}",
        model=MODEL_NAME
    )
    
    final_result = parse_decision(decision_raw)
    return final_result

# ==============================================================================
# 使用示例
# ==============================================================================
if __name__ == "__main__":
    # 假设您的输入文件如下：
    # 1. reviews.json: 包含审稿人意见的列表
    # 2. rebuttal.pdf: 作者提交的 Rebuttal PDF 文件
    
    json_file = "reviews.json"
    pdf_file = "rebuttal.pdf"
    
    # 检查文件是否存在，防止报错
    if not os.path.exists(json_file) or not os.path.exists(pdf_file):
        print("请确保目录下存在 'reviews.json' 和 'rebuttal.pdf' 文件以运行测试。")
    else:
        prediction = run_cvpr_prediction(json_file, pdf_file)
        
        print("\n" + "="*50)
        print("FINAL PREDICTION RESULT")
        print("="*50)
        print(json.dumps(prediction, indent=2, ensure_ascii=False))