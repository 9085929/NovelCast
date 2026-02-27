from openai import OpenAI
import json
import os
client2= OpenAI(api_key="sk-1bcd44d6982c405ca22ea23e8d6c38c2", base_url="https://api.deepseek.com")
client_qwen = OpenAI(api_key="sk-75be6cb9e1b746878dced094fad65152", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
def Deepseek_Generate_onechat(prompt_text,system_text):
    prompt_text = prompt_text.replace('\n\n', '\n')
    if system_text == '':
        response = client2.chat.completions.create(model='deepseek-chat', messages=[
            {"role": "user", "content": prompt_text}
        ], response_format={'type': 'json_object'})

    else:
        response = client2.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt_text},
            ],
            response_format={
                'type': 'json_object'
            }
        )
    result = response.choices[0].message.content
    return json.loads(result)




Instruction = """你是一名专业的角色分析师和剧本顾问。你的任务是阅读我提供的英雄联盟角色的人物传记，并从中提取核心信息，以便为音频剧本的角色进行音色匹配。
请遵循以下步骤处理我给出的数据：
1. 生成核心摘要: 将长篇的 [人物传记] 缩写成一段100~150字的精简摘要。摘要应重点突出角色的核心身份、关键经历和主要动机。
2. 提炼性格关键词: 从传记中提取5-10个最能代表角色性格的关键词或短语。这些词应该简洁、有力。
3. 推断人物原型: 从传记中推断出一个包含1-3个人物原型的数组。
4. 你的输出**必须**是一个单一的、结构完整的JSON对象，**绝对不能**包含任何JSON格式之外的解释性文字或标记。
输出的JSON格式必须如下：
{
  "摘要": "生成的摘要文本",
  "性格关键词": ["关键词1", "关键词2", "关键词3"，...],
  "人物原型": ["原型1", "原型2"，...]
}
"""
output_path = "hero_traits.json"

# 如果文件不存在，先创建一个空的 json 列表
cd cd

with open("/home/huang/Code/Podcast/Preprocessing/LOL_BLOG.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

for cur,i in enumerate(data):
    if cur<1:
        continue
    name = i['name']
    other_name = i['other_name'] if 'other_name' in i else ''
    blog= i['hero_tale'] if 'hero_tale' in i else ''
    print(name)
    print(other_name)
    print(blog)
    UserIns =f"""英雄名称：{name}
人物传记: {blog}
"""
    rsp = Deepseek_Generate_onechat(UserIns, Instruction)
    rsp['name'] = name
    rsp['other_name'] = other_name
    print(rsp)
    # 读取已有内容
    with open(output_path, 'r', encoding='utf-8') as f:
        existing_data = json.load(f)

    # 追加新数据
    existing_data.append(rsp)

    # 写回文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)
    print(cur)

