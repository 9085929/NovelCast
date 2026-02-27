import json


Voice_Lib_path = "./Voices/metadata.json"
role_match_path = "./result/role/role_result.json"
script_path = "./result/script/xiyou_1.json"
role_audio_path = "./result/role/combined_role_audio.json"

"""
combined role & audio
 {
      "角色名称": "旁白",
      "配对声音": 22,
      "音频路径": "/home/huang/Code/Podcast/Voices/ref_wav/SSB04340059.wav",
      "ASR文本": "张小光 欲乐营销如何从云端落地"
    },
"""
def CombinedRoleandAudio(Voice_Lib_path,role_match_path):
    with open(Voice_Lib_path, 'r', encoding='utf-8') as f:
        voice_lib = json.load(f)
    # 加载第二个 JSON 文件：角色与声音的映射
    with open(role_match_path, 'r', encoding='utf-8') as f:
        role_mapping = json.load(f)
    # 提取角色声音配对列表
    role_list = role_mapping.get("角色声音配对", [])
    # 构建新数据列表
    combined_data = []
    for role_info in role_list:
        role_name = role_info["角色名称"]
        voice_id = str(role_info["配对声音"])  # 转成字符串以匹配 keys
        # 查找对应的语音数据
        if voice_id in voice_lib:
            voice_info = voice_lib[voice_id]
            combined_entry = {
                "角色名称": role_name,
                "配对声音": int(voice_id),
                "音频路径": voice_info["wav_path"],
                "ASR文本": voice_info["asr_text"]
            }
            combined_data.append(combined_entry)
        else:
            print(f"警告：找不到 ID 为 {voice_id} 的语音数据")
    # 保存或打印结果
    output_json = {"角色语音映射": combined_data}
    # 打印结果
    print(json.dumps(output_json, ensure_ascii=False, indent=2))
    # 或者保存到文件
    with open('./result/role/combined_role_audio.json', 'w', encoding='utf-8') as f:
        json.dump(output_json, f, ensure_ascii=False, indent=2)


"""
加载剧本信息
{
    "内容": "没什么恩情可报！你以后出去，不许说是我的徒弟！你若说出半个字来，我把你这猢狲剥皮锉骨，神魂贬到九幽之处，万劫不得翻身！",
    "语音ID": 36,
    "说话者": "须菩提祖师",
    "语调建议": "决绝，严厉警告，不带感情。",
    "音频路径": "/home/huang/Code/Podcast/Voices/ref_wav/SSB04340101.wav",
    "ASR文本": "2014年台湾皇冠出版社初帅的邵帅"
  },
"""
def process_script(script_path, role_audio_path):

    with open(script_path, 'r', encoding='utf-8') as f:
        Script = json.load(f)
    script_data = Script.get("剧本", [])

    with open(role_audio_path, 'r', encoding='utf-8') as f:
        role_audio_data = json.load(f)

    # 构建 voice_id 到 音频路径 和 ASR文本 的映射字典
    voice_info_map = {}
    for entry in role_audio_data["角色语音映射"]:
        voice_id = entry["配对声音"]
        voice_info_map[voice_id] = {
            "音频路径": entry["音频路径"],
            "ASR文本": entry["ASR文本"]
        }
    # 构建角色 -> voice_id 映射
    role_to_voice = {}
    for entry in role_audio_data["角色语音映射"]:
        role_to_voice[entry["角色名称"]] = entry["配对声音"]

    # 默认旁白语音 ID
    default_narrator_id = role_to_voice.get("旁白", 22)

    # 匹配生成最终结果
    final_script = []

    for item in script_data:
        if '对话' in item:
            speaker = item['说话者']
            voice_id = role_to_voice.get(speaker)
            content = item['对话']
            speaker_key = '说话者'
        elif '旁白' in item:
            voice_id = default_narrator_id
            content = item['旁白']
            speaker = '旁白'
            speaker_key = '类型'
        else:
            continue  # 忽略无效项

        # 获取语音相关信息
        voice_info = voice_info_map.get(voice_id, {})
        audio_path = voice_info.get("音频路径", "")
        asr_text = voice_info.get("ASR文本", "")

        final_script.append({
            '内容': content,
            '语音ID': voice_id,
            speaker_key: speaker,
            '语调建议': item['语调建议'],
            '音频路径': audio_path,
            'ASR文本': asr_text
        })

    # 输出结果（可选：保存到文件）
    output_script_path = 'result/script/final_script_pre.json'
    with open(output_script_path, 'w', encoding='utf-8') as f:
        json.dump(final_script, f, ensure_ascii=False, indent=2)


# with open("/home/huang/Code/Podcast/result/script/final_script_pre.json", 'r', encoding='utf-8') as f:
#     script_data = json.load(f)
# print(len(script_data))



