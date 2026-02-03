# CVPR 2026 论文录用预测器 (Paper Acceptance Predictor)

这是一个基于 Multi-Agent 大语言模型（LLM）的自动化系统，旨在模拟 CVPR 领域主席（Area Chair）的决策过程。它能够综合分析**审稿人意见（Reviews）和作者提交的Rebuttal PDF（包含视觉证据）**，从而预测论文最终的录用结果（Accept/Reject）及评分。

本系统支持同时使用 **Google Gemini** (如 `gemini-3-pro-preview`) 和 **OpenAI GPT** (如 `gpt-5.2-2025-12-11`) 模型。

## ✨ 功能特点

* **多模态分析**：不仅阅读文本，还能“看懂” Rebuttal PDF 中的新实验图表，判断视觉证据是否有效。
* **AC 模拟决策**：模拟 AC 的思维链，识别审稿人画像（Expert vs Shallow），权衡 Rebuttal 的翻盘力度。
* **双模型支持**：内置对 Google GenAI SDK 和 OpenAI SDK 的支持，可一键切换模型。

## 🛠️ 环境准备

### 1. 安装 Python 依赖

请确保您的 Python 环境（建议 Python 3.8+）安装了以下库：

```bash
pip install requests pdf2image Pillow google-genai openai

```

## 🚀 快速开始

### 第一步：设置 API Key

建议通过环境变量设置 Key，保护您的凭证安全：

**Linux/Mac:**

```bash
# 如果使用 Google Gemini
export GEMINI_API_KEY="您的_GOOGLE_API_KEY"

# 如果使用 OpenAI GPT
export OPENAI_API_KEY="您的_OPENAI_API_KEY"
# 可选：如果使用代理
export OPENAI_BASE_URL="https://api.openai.com/v1" 

```

**Windows (PowerShell):**

```powershell
$env:GEMINI_API_KEY="您的_GOOGLE_API_KEY"
$env:OPENAI_API_KEY="您的_OPENAI_API_KEY"

```

### 第二步：准备输入数据

在项目根目录下准备以下两个文件：

1. **`reviews.json`**：包含审稿意见的 JSON 文件。
* 格式参考：


```json
[
  {
    "Paper Summary": "...",
    "Paper Strengths": "...",
    "Major Weaknesses": "...",
    "Preliminary Recommendation": "3",
    "Confidence Level": "5"
  },
  ...
]

```


2. **`rebuttal.pdf`**：作者提交的 Rebuttal PDF 文件。

### 第三步：配置模型 (可选)

打开 `predictor_cvpr.py`，修改 `MODEL_NAME` 变量来选择您想使用的模型：

```python
# 使用 Google Gemini
MODEL_NAME = "gemini-3-pro-preview" 

# 或者使用 OpenAI GPT
# MODEL_NAME = "gpt-5.2-2025-12-11"

```

### 第四步：运行预测

在终端运行主程序：

```bash
python predictor_cvpr.py

```

### 输出示例

程序运行结束后，将输出类似如下的 JSON 预测报告：

```json
{
  "final_decision": "Accept",
  "detailed_label": "Accept (Poster)",
  "final_score": 4.7,
  "decision_archetype": "Saved_by_Rebuttal_Evidence",
  "reasoning": "Initial scores were borderline. The Rebuttal PDF successfully provided the missing comparisons...",
  "confidence": "High"
}

```

## 🙏 致谢 (Acknowledgements)

本项目的设计理念与核心框架深受 **PaperDecision** 项目的启发。特别感谢原作者团队对社区的开源贡献。

* **PaperDecision**: [https://github.com/PaperDecision/PaperDecision](https://github.com/PaperDecision/PaperDecision)
* *Benchmarking Decision Process with A Multi-Agent System*



---

**Disclaimer**: 本工具仅供"**娱乐**"，不能替代真实的同行评审过程。
