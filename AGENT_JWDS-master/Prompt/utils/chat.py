import json
import sys
import os,re
sys.path.append(os.path.dirname(__file__))
import random
from openai import OpenAI
client = OpenAI(api_key="", base_url="https://api.deepseek.com")
client2= OpenAI(api_key="", base_url="https://chatapi.onechats.ai/v1/")
client_qwen = OpenAI(api_key="", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")


API_KEYS = [
    
]

def choose_api_key():

    client= OpenAI(api_key=" ", base_url="https://chatapi.onechats.ai/v1/")

    return client


def Deepseek_Generate(prompt_text,system_text):
    prompt_text = prompt_text.replace('\n\n', '\n')
    if system_text == '':
        response = client.chat.completions.create(
            # model="deepseek-chat",
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": prompt_text},
            ],
            max_tokens=8192,
            stream=False,
            temperature=1.3
        )
    else:
        response = client.chat.completions.create(
            # model="deepseek-chat",
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt_text},
            ],
            max_tokens=8192,
            stream=False,
            temperature=1.3
        )
    result = response.choices[0].message.content
    result = result.replace('\n\n', '\n')
    return result


def QwenPLUS_Generate(prompt_text,system_text):
    prompt_text = prompt_text.replace('\n\n', '\n')
    if system_text == '':
        response = client_qwen.chat.completions.create(
            model="qwen-plus-1125",
            # model="qwen-max-0125",
            # model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": prompt_text},
            ],
            max_tokens=8192,
            stream=False,
            temperature=1.3
        )
    else:
        response = client_qwen.chat.completions.create(
            model="qwen-plus-1220",
            # model="qwen-max-0125",
            # model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt_text},
            ],
            max_tokens=8192,
            stream=False,
            temperature=1.3
        )
    result = response.choices[0].message.content
    result = result.replace('\n\n', '\n')
    return result

def QwenPLUS_Generate_JSON(prompt_text,system_text):
    prompt_text = prompt_text.replace('\n\n', '\n')
    if system_text == '':
        response = client_qwen.chat.completions.create(
            model="qwen-plus-2025-09-11",
            # model="qwen-max-0125",
            # model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": prompt_text},
            ],
            max_tokens=32768,
            stream=False,
            temperature=1.3,
            response_format={"type": "json_object"}
        )
    else:
        response = client_qwen.chat.completions.create(
            model="qwen-plus-2025-09-11",
            # model="qwen-max-0125",
            # model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt_text},
            ],
            max_tokens=32768,
            stream=False,
            temperature=1.3,
            response_format = {"type": "json_object"}
        )
    result = response.choices[0].message.content
    result = result.replace('\n\n', '\n')
    print(result)
    if result.startswith("```") and result.endswith("```"):
        json_str = re.search(r'```json\n([\s\S]*?)\n```', result, re.DOTALL).group(1)
        data = json.loads(json_str)
        return data
    json_result = json.loads(result)
    return json_result





def Gemini_Generate_Json(prompt_text, system_text):
    cilent_gemini = choose_api_key()
    
    messages = []
    
    final_content = prompt_text
    if system_text:
        final_content = f"【系统指令/背景设定】\n{system_text}\n\n【用户任务】\n{prompt_text}"
    
    messages.append({"role": "user", "content": final_content})

    try:
        response = cilent_gemini.chat.completions.create(
            model='gemini-3-pro-preview', 
            
            messages=messages,
            max_tokens=8192, 
            temperature=0.7,
            
        )
        
        if not response or not response.choices:
            raise ValueError("API 返回了空响应 (No choices)")
            
        result = response.choices[0].message.content
        
        if not result or not result.strip():
            print(f"[警告] 模型返回了空字符串！可能是由于安全过滤。")
            raise ValueError("模型返回空内容")

        import json
        import re

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            pass

        match = re.search(r'```(?:json)?\s*(\{.*\}|\[.*\])\s*```', result, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        match_bracket = re.search(r'(\{.*\})|(\[.*\])', result, re.DOTALL)
        if match_bracket:
            json_str = match_bracket.group(0)
            try:
                return json.loads(json_str)
            except:
                pass

        print(f"[解析失败] 无法从以下内容提取 JSON:\n{result[:200]}...")
        raise ValueError("无法解析 JSON")

    except Exception as e:
        # 打印详细错误方便调试
        print(f"[API Error] 详细报错: {e}")
        raise e





def Gemini_Generate_onechat(prompt_text,system_text):
    prompt_text = prompt_text.replace('\n\n', '\n')
    if system_text == '':
        response = client2.chat.completions.create(model='gemini-2.5-pro-preview-05-06', messages=[
            {"role": "user", "content": prompt_text}
        ], temperature=1.3)

    else:
        response = client2.chat.completions.create(
            model="gemini-2.5-pro-preview-05-06",
            # model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt_text},
            ],
            temperature=1.3
        )
    print(response)
    result = response.choices[0].message.content
    result = result.replace('\n\n', '\n')
    return result