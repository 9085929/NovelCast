import time

import json
import sys
# import Prompt
from UIFuction import *
import os
# sys.path.append(os.path.join(os.path.dirname(__file__), 'CosyVoice'))
# from CosyVoice.run_Script import generate_tts
import gradio as gr


"""
音色处理逻辑
"""
def tts_process(generated_script, character_voice, filenameState):
    print("[INFO] Starting TTS generation...")
    # 模拟 TTS 生成过程
    with open('/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/AGENT_JWDS-master/Voices/merged_lol_data.json', 'r', encoding='utf-8') as f:
        voice_lib = json.load(f)
    # 加载第二个 JSON 文件：角色与声音的映射
    role_to_voice_name = {
        item["角色名称"]: item["配对声音"]
        for item in character_voice.get("角色声音配对", [])
    }
    # 默认旁白音色 (如果映射中没有旁白，则选择列表中的第一个可用音色作为备用)
    default_narrator_voice = role_to_voice_name.get("旁白", list(voice_data_map.keys())[0] if voice_data_map else None)
    script_data = generated_script.get("剧本", [])
    final_script = []

    for item in script_data:
        content = None
        speaker = None
        speaker_key = None

        if '对话' in item:
            speaker = item['说话者']
            content = item['对话']
            speaker_key = '说话者'
            # 从映射中找到该角色配对的音色名，如果没有则使用旁白音色
            voice_name = role_to_voice_name.get(speaker, default_narrator_voice)

        elif '旁白' in item:
            speaker = '旁白'
            content = item['旁白']
            speaker_key = '类型'
            voice_name = default_narrator_voice

        else:
            continue

        if not voice_name or voice_name not in voice_data_map:
            print(f"[警告] 角色 '{speaker}' 对应的音色 '{voice_name}' 未在音色库中找到，跳过此行。")
            continue

        # 从 voice_data_map 中获取音色信息
        # 规则：使用该音色的第一个音频作为参考
        voice_info = voice_data_map[voice_name]
        if not voice_info.get("音频") or len(voice_info["音频"]) == 0:
            print(f"[警告] 音色 '{voice_name}' 没有可用的音频样本，跳过。")
            continue

        reference_audio = voice_info["音频"][0]
        audio_path = reference_audio["路径"]
        asr_text = reference_audio["文本"]

        final_script.append({
            '内容': content,
            '语音ID': voice_name,  # 注意：这里现在是音色名称字符串，而不是数字ID
            speaker_key: speaker,
            '语调建议': item.get('语调建议', ''),  # 使用.get增加健壮性
            '音频路径': audio_path,
            'ASR文本': asr_text
        })

    print(json.dumps(final_script, indent=2, ensure_ascii=False))
    # tts_audio_path = generate_tts(filenameState, final_script)
    
    print("[INFO] TTS generation finished.")

    # return tts_audio_path, gr.update(open=True), "TTS 生成成功，请点击播放按钮收听。"
    return "/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/result/原著-白话.wav", gr.update(open=True), "TTS 生成成功，请点击播放按钮收听。"


"""
快速模式：一键串联分析→剧本→配音推荐→TTS 输出（带进度提示）
"""
def _read_uploaded_text_quick(file_obj):
    if not file_obj:
        return ""
    try:
        with open(file_obj.name, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"[读取文件失败] {e}"


def quick_pipeline(selected_mode, input_text, uploaded_file):
    # 输出顺序：status_md, storyline_tb, character_tb, script_tb, audio_out
    status_msgs = []

    def push(msg):
        status_msgs.append(msg)
        return "\n".join([f"- {m}" for m in status_msgs[-8:]])

    # 切换 Prompt 模式
    try:
        switch_prompt_module(selected_mode)
        yield (
            push(f"已切换模式：{selected_mode}"),
            gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value=None)
        )
    except Exception as e:
        yield (
            push(f"[错误] 切换模式失败：{e}"),
            gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value=None)
        )
        return

    # 准备文本
    text = (input_text or "").strip()
    if not text and uploaded_file is not None:
        text = _read_uploaded_text_quick(uploaded_file) or ""
    if not text:
        yield (
            push("[提示] 没有检测到输入文本，请先输入或上传文件。"),
            gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value=None)
        )
        return

    # 内容分析
    yield (
        push("开始分析内容……（这一步可能较久）"),
        gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value=None)
    )
    try:
        # 参考现有 analyze_content_process 输出结构
        storyline_text, character_text, character_json = analyze_content_process(text)
        yield (
            push("内容分析完成。"),
            gr.update(value=storyline_text),
            gr.update(value=character_text),
            gr.update(value=""),
            gr.update(value=None)
        )
    except Exception as e:
        yield (
            push(f"[错误] 内容分析失败：{e}"),
            gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value=None)
        )
        return

    # 生成剧本
    yield (
        push("开始生成剧本……"),
        gr.update(value=storyline_text), gr.update(value=character_text), gr.update(value=""), gr.update(value=None)
    )
    try:
        script_text, _btn_voice, _acc_script, process_status, generated_script_json = generate_script_process(text, storyline_text, character_json)
        yield (
            push("剧本生成完成。"),
            gr.update(value=storyline_text), gr.update(value=character_text), gr.update(value=script_text), gr.update(value=None)
        )
    except Exception as e:
        yield (
            push(f"[错误] 剧本生成失败：{e}"),
            gr.update(value=storyline_text), gr.update(value=character_text), gr.update(value=""), gr.update(value=None)
        )
        return

    # 角色声音配对
    yield (
        push("开始角色声音配对……"),
        gr.update(value=storyline_text), gr.update(value=character_text), gr.update(value=script_text), gr.update(value=None)
    )
    try:
        _btn_tts, _acc_role, process_status, character_voice_json = voice_match_process(character_json, generated_script_json)
        yield (
            push("角色声音配对完成。"),
            gr.update(value=storyline_text), gr.update(value=character_text), gr.update(value=script_text), gr.update(value=None)
        )
    except Exception as e:
        yield (
            push(f"[错误] 声音配对失败：{e}"),
            gr.update(value=storyline_text), gr.update(value=character_text), gr.update(value=script_text), gr.update(value=None)
        )
        return

    # 生成 TTS
    yield (
        push("开始生成TTS 音频……"),
        gr.update(value=storyline_text), gr.update(value=character_text), gr.update(value=script_text), gr.update(value=None)
    )
    try:
        audio_path, _acc_tts_update, final_msg = tts_process(generated_script_json, character_voice_json, "quick_mode")
        yield (
            push(final_msg),
            gr.update(value=storyline_text), gr.update(value=character_text), gr.update(value=script_text), gr.update(value=audio_path)
        )
    except Exception as e:
        yield (
            push(f"[错误] TTS 生成失败：{e}"),
            gr.update(value=storyline_text), gr.update(value=character_text), gr.update(value=script_text), gr.update(value=None)
        )
        return

def tts_prepare(*ui_inputs):
    """
        从UI组件中收集用户最终确定的角色和声音选择。
        Gradio会将所有输入组件的值作为扁平化的*args传入。
        """
    character_names = ui_inputs[:MAX_CHARACTERS]
    selected_voice_display_names = ui_inputs[MAX_CHARACTERS:MAX_CHARACTERS * 2]
    a_list_of_reasons = ui_inputs[MAX_CHARACTERS * 2:]

    updated_pairings = []
    for i in range(MAX_CHARACTERS):
        char_name = character_names[i]
        voice_display_name = selected_voice_display_names[i]

        # 如果角色名为空，说明这一行是未使用的，直接跳过
        if not char_name:
            continue

        # 将UI上显示的名称 (e.g., "莉莉娅 (好奇, 善良)") 转换回JSON中的键名 (e.g., "含羞蓓蕾 莉莉娅")
        voice_name = voice_display_to_name_map.get(voice_display_name)

        if voice_name:
            updated_pairings.append({
                "角色名称": char_name,
                "配对声音": voice_name,
                # 您也可以在这里收集理由，如果需要的话
                "理由": a_list_of_reasons[i]
            })

    # 返回与原始 `character_voice_json_state` 格式一致的字典
    return {"角色声音配对": updated_pairings}

"""
音色预览逻辑
"""
VOICES_JSON_PATH = r"/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/AGENT_JWDS-master/Voices/merged_lol_data_xiyou_1028.json"
voice_data = None
try:
    # 1. 先验证文件是否存在（兜底检查）
    if not os.path.exists(VOICES_JSON_PATH):
        raise FileNotFoundError(f"文件路径不存在：{VOICES_JSON_PATH}")
    # 2. 指定UTF-8编码读取（解决中文解码问题）
    with open(VOICES_JSON_PATH, "r", encoding="utf-8") as f:
        voice_data = json.load(f)
    print(f"✅ 音色库加载成功！共加载 {len(voice_data)} 个角色")
except FileNotFoundError:
    print(f"[警告] 音色库文件未找到：{VOICES_JSON_PATH}")
except UnicodeDecodeError:
    print(f"[错误] 音色库文件解码失败，请确保文件为UTF-8编码")
except json.JSONDecodeError as e:
    print(f"[错误] 音色库JSON格式错误：{e}（行 {e.lineno}，列 {e.colno}）")
except Exception as e:
    print(f"[错误] 音色库加载失败：{type(e).__name__} - {str(e)}")

# --- 辅助函数：从JSON加载音色列表和路径映射 ---
def get_voice_options_and_paths_from_json(json_path):
    """
    从JSON文件加载音色信息，返回可选的音色描述/ID列表和音色ID到文件路径的映射。
    """
    voice_options = []  # 用于Dropdown的显示名称
    voice_display_to_name  = {}  # 显示名 -> 序号真实角色名 (序号 1-性别-性格 (好奇, 善良)" -> "含羞蓓蕾 莉莉娅")
    voice_name_to_data  = {}  # 真实角色名 -> 该角色的所有数据
    voice_simpleName_to_displayName_map={}
    if not os.path.exists(json_path):
        print(f"[警告] 音色库文件未找到。")
        return voice_options, voice_display_to_name, voice_name_to_data,voice_simpleName_to_displayName_map

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[错误] 解析JSON文件 '{json_path}' 失败: {e}")
        return voice_options, voice_display_to_name, voice_name_to_data,voice_simpleName_to_displayName_map
    valid_voice_index = 0
    # character_full_name: JSON中的角色全名，如 "含羞蓓蕾 莉莉娅"
    for character_full_name, voice_info in data.items():
        # 检查是否有可用的音频文件
        if "音频" in voice_info and isinstance(voice_info["音频"], list) and len(voice_info["音频"]) > 0:
            valid_voice_index+=1
            # 1. 格式化序号 (例如：001, 002, ...)
            formatted_index = f"{valid_voice_index:03d}"
            # 2. 获取性别。如果JSON中没有"性别"字段，则默认为 "未知"
            gender = voice_info.get("性别", "未知")
            # 构建一个用户友好的显示名称，包含性格关键词
            keywords_preview = f" ({', '.join(voice_info.get('性格关键词', [])[:3])}···)" if voice_info.get(
                '性格关键词') else ""
            display_name = f"{formatted_index}-{gender}-{keywords_preview}"

            simple_name = voice_info.get("name","")
            voice_simpleName_to_displayName_map[simple_name] = display_name

            voice_options.append(display_name)
            voice_display_to_name[display_name] = character_full_name  # 映射显示名到JSON的key
            voice_name_to_data[character_full_name] = voice_info  # 映射JSON的key到完整数据
        else:
            print(f"[警告] JSON中角色 '{character_full_name}' 的条目缺少'音频'列表或列表为空。")

    if not voice_options:
        print(f"[警告] JSON文件 '{json_path}' 为空或不包含有效的音色条目。")

    return voice_options, voice_display_to_name, voice_name_to_data,voice_simpleName_to_displayName_map


# --- 加载音色数据 ---
# voice_options_list: Dropdown中显示的音色名称列表
# voice_display_to_name_map: 将Dropdown中的显示名称映射回JSON中的角色名key
# voice_data_map: 将JSON中的角色名key映射到其完整信息
voice_options_list, voice_display_to_name_map, voice_data_map,voice_simpleName_to_displayName_map = get_voice_options_and_paths_from_json(VOICES_JSON_PATH)
# 创建一个反向映射，用于从角色名找到其在UI上的显示名 含羞蓓蕾 莉莉娅-显示名称
voice_name_to_display_map = {v: k for k, v in voice_display_to_name_map.items()}
"""
根据选择的声音名称，查找并返回对应的音频文件路径。
"""
def play_preview_for_character(voice_display_name):
    if not voice_display_name:
        # 如果没有选择声音，则不执行任何操作。
        # 在生成器函数中，return None 会停止迭代，等同于不产生任何更新。
        return None

    # 1. 从显示名称获取真实的音色/角色名
    voice_name = voice_display_to_name_map.get(voice_display_name)

    if voice_name and voice_name in voice_data_map:
        # 2. 获取该音色的第一个音频样本作为预览
        audio_list = voice_data_map[voice_name].get("音频", [])
        if audio_list:
            audio_path = audio_list[0].get("路径")
            if audio_path and os.path.exists(audio_path):
                # 使用 yield 技巧强制重新加载和播放
                yield gr.update(value=None, visible=False)
                time.sleep(0.05)
                yield gr.update(value=audio_path, visible=False)
                return

    # 如果找不到文件，清空播放器
    yield gr.update(value=None, visible=False)

"""
接收AI返回的角色声音配对JSON，并更新UI界面。
"""
def update_character_voice_previews(character_voice_json):

    updates = []
    try:
        data = character_voice_json.get('角色声音配对', [])
        num_characters = len(data)

        # 1. 显示主容器
        updates.append(gr.update(visible=True))  # 对应的character_voice_preview_container

        # 2. 遍历AI返回的角色数据，填充并显示对应的UI行
        for i in range(min(num_characters, MAX_CHARACTERS)):
            char_info = data[i]
            char_name = char_info.get('角色名称')
            voice_name = char_info.get('配对声音') # AI返回的是真实的角色名，如 "莉莉娅"
            reason = char_info.get('理由')
            # 从真实角色名找到对应的UI显示名，用于设置下拉框的默认值
            default_voice_display_name = voice_simpleName_to_displayName_map.get(voice_name)
            updates.append(gr.update(visible=True))
            updates.append(gr.update(value=char_name))
            updates.append(gr.update(value=default_voice_display_name))
            updates.append(gr.update(value=reason))

        for i in range(num_characters, MAX_CHARACTERS):
            updates.append(gr.update(visible=False))
            updates.append(gr.update(value=""))
            updates.append(gr.update(value=None))
            updates.append(gr.update(value=None))


        # 如果返回的角色数为0，则隐藏主容器
        if num_characters == 0:
            updates[0] = gr.update(visible=False)


    except Exception as e:
        print(f"解析角色声音JSON或更新UI时出错: {e}")
        updates = [gr.update(visible=False)]
        for i in range(MAX_CHARACTERS):
            updates.extend([
                gr.update(visible=False), gr.update(value=""),
                gr.update(value=None), gr.update(value=None)
            ])

    # 返回所有更新指令。返回的列表长度必须与outputs列表完全匹配。
    # 我们将所有更新打包成一个列表返回
    return updates



# --- 事件处理函数：当选择的音色改变时更新音频播放器 ---
"""
根据选择的音色显示名称，找到对应的音频文件路径用于播放。
"""
def preview_selected_voice_from_json(selected_display_name):
    if not selected_display_name:
        return gr.update(value=None, visible=False, label="选择音色试听")
        # 1. 从显示名找到真实的角色名
    voice_name = voice_display_to_name_map.get(selected_display_name)

    if voice_name and voice_name in voice_data_map:
        # 2. 找到第一个音频文件用于预览
        audio_list = voice_data_map[voice_name].get("音频", [])
        if audio_list:
            audio_path = audio_list[0].get("路径")
            if audio_path and os.path.exists(audio_path):
                label_text = f"试听: {selected_display_name}"
                return gr.update(value=audio_path, visible=True, label=label_text)
            else:
                return gr.update(value=None, visible=True, label=f"错误: 音频文件未找到 ({selected_display_name})")

    return gr.update(value=None, visible=False, label="选择音色试听")

def initialize_audio_player_on_load():
    initial_audio_update = gr.update(value=None, label="选择一个音色进行试听", visible=False)

    if voice_options_list:
        selected_name = voice_options_list[0]  # 获取Dropdown的初始值
        # 调用与change事件相同的逻辑来获取更新对象
        # 注意：这里我们不能直接调用 preview_selected_voice_from_json 并期望它能工作，
        # 因为 preview_selected_voice_from_json 是为 .change() 设计的，返回的是 gr.update()
        # 我们需要模拟它的逻辑来构造初始的 gr.update()
        voice_name = voice_display_to_name_map.get(selected_name)
        if voice_name and voice_name in voice_data_map:
            # 2. 找到第一个音频文件用于预览
            audio_list = voice_data_map[voice_name].get("音频", [])
            if audio_list:
                audio_path = audio_list[0].get("路径")
                if audio_path and os.path.exists(audio_path):
                    label_text = f"试听: {selected_name}"
                    return gr.update(value=audio_path, visible=True, label=label_text)
                else:
                    return gr.update(value=None, visible=True, label=f"错误: 音频文件未找到 ({selected_name})")
    return initial_audio_update




# --- Gradio UI ---

demo_css = """
.gradio-container { 
    max-width: 100% !important; 
    width: 100% !important;
    margin: 0 !important; 
    padding: 10px !important;
}
.main { 
    max-width: none !important; 
    width: 100% !important; 
}
.contain { 
    max-width: none !important; 
    width: 100% !important; 
}
.flex { 
    width: 100% !important; 
}
footer { display: none !important; }
"""

with gr.Blocks(theme=gr.themes.Soft(), analytics_enabled=False,
               css=demo_css) as demo: 
    # Top bar
    with gr.Row():
        main_title_md = gr.Markdown("# AI4Reading 📝")
        with gr.Row():
                # 模式选择器
                mode_switcher = gr.Radio(
                    ["成年版", "青年版", "儿童版"],
                    label="内容生成模式",
                    value="儿童版",  # 默认值
                    interactive=True,  # 明确启用交互性
                    scale=2
                )
                
    gr.Markdown("---")

    with gr.Tabs() as main_tabs:
        with gr.Tab("快速模式（推荐）"):
            with gr.Row():
                with gr.Column(scale=2):
                    quick_input_text = gr.Textbox(label="输入文本（可直接粘贴章节内容）", lines=8, placeholder="在此粘贴文本，或右侧上传文件……")
                with gr.Column(scale=1):
                    quick_file_upload = gr.File(label="上传文件（.txt/.pdf，优先读取 .txt）", file_types=['.txt', '.pdf'])

            quick_status_md = gr.Markdown("- 准备就绪")
            quick_btn = gr.Button("🚀 一键生成音频", variant="primary")

            with gr.Row():
                with gr.Column():
                    quick_storyline_tb = gr.Textbox(label="故事线", lines=5, interactive=False)
                with gr.Column():
                    quick_character_tb = gr.Textbox(label="角色信息", lines=5, interactive=False)

            quick_script_tb = gr.Textbox(label="生成的剧本", lines=8, interactive=False)
            quick_audio_out = gr.Audio(label="生成的语音", type="filepath", interactive=False)

            quick_btn.click(
                fn=quick_pipeline,
                inputs=[mode_switcher, quick_input_text, quick_file_upload],
                outputs=[quick_status_md, quick_storyline_tb, quick_character_tb, quick_script_tb, quick_audio_out]
            )

        with gr.Tab("正常模式"):
            with gr.Row():
                # 上传文档
                pdf_upload = gr.File(
                    label="上传文件,支持PDF/TXT",
                    file_types=['.pdf', '.txt'],
                    scale=2
                )
                # 处理状态显示
                process_status_display = gr.Textbox(label="处理状态", show_label=True, interactive=False, scale=3, max_lines=2,
                                                    placeholder="上传文件后，此处将显示解析和生成状态。")

            # 章节 Section
            with gr.Accordion("📚 章节", open=True) as chapter_accordion:
                # 章节内容 Markdown
                chapter_content_md = gr.Markdown("上传内容")
                with gr.Row():
                    with gr.Column(scale=4):
                        # PDF内容显示区域
                        pdf_content_display = gr.Textbox(
                            value="请先上传并解析PDF。",
                            label="章节内容 (PDF解析)",
                            lines=10,
                            max_lines=10,
                            interactive=False,  # Display only
                            show_label=False
                        )

                    with gr.Column(scale=1):
                        # 右侧Markdown区域
                        chapter_right_md = gr.Markdown("（上传PDF后，点击下方功能进行分析）")
                        # 分析内容/重新分析
                        btn_generate = gr.Button("✍️ 分析内容 / 重新分析", interactive=False)
                        # 按钮：生成剧本
                        btn_generate_script = gr.Button("📜 剧本生成", interactive=False)
                        # 按钮：角色声音配对
                        btn_generate_voiceMatch = gr.Button("🎭 角色声音配对", interactive=False)
                        # 按钮：生成TTS
                        btn_generate_tts = gr.Button("🎤 生成TTS", interactive=False)

            # 故事主线 Section
            with gr.Accordion("📖 故事线", open=False) as Accordion_Storyline:
                # 故事线操作提示 Markdown
                storyline_md = gr.Markdown("（上传PDF后，点击'生成内容'进行分析）")
                # 故事线内容显示区域
                storyline_content_display = gr.Textbox(
                    value="请先上传并解析PDF。",
                    lines=5,
                    interactive=False,  # Display only
                    show_label=False
                )
            # 音色选择与试听 Section
            with gr.Accordion("🎤 音色选择与试听", open=True) as voice_accordion:
                with gr.Row():
                    with gr.Column():
                        # 音色选择下拉框
                        voice_json_selector = gr.Dropdown(
                            label="音色 (编号-性别-性格)",
                            choices=voice_options_list,  # 使用从JSON加载的显示名称列表
                            value=voice_options_list[0] if voice_options_list else None,  # 默认选择第一个音色
                            interactive=True,
                            scale=3
                        )
                    with gr.Column():
                        # 音色试听播放器
                        voice_json_preview_player = gr.Audio(
                            label="选择一个音色进行试听",
                            type="filepath",
                            interactive=False,
                            show_download_button=False,
                            show_share_button=False,
                            autoplay=False,
                            visible=False
                        )

                    if voice_options_list:
                        initial_selected_name = voice_options_list[0]
                        voice_name = voice_display_to_name_map.get(initial_selected_name)
                        if voice_name and voice_name in voice_data_map:
                            audio_list = voice_data_map[voice_name].get("音频", [])
                            initial_audio_path = audio_list[0].get("wav_path")

                            if initial_audio_path and os.path.exists(initial_audio_path):
                                initial_label = f"试听: {initial_selected_name}"
                                voice_json_preview_player.value = initial_audio_path
                                voice_json_preview_player.label = initial_label
                                voice_json_preview_player.visible = True
                            else:
                                voice_json_preview_player.label = f"错误: 默认音色音频 '{initial_audio_path}' 未找到"
                                voice_json_preview_player.visible = True  # 显示错误信息

            # 角色 Section
            with gr.Accordion("🗣️ 角色", open=False) as Accordion_Role:
                # 角色操作提示 Markdown
                character_md = gr.Markdown("（上传PDF后，点击'生成内容'进行分析）")
                # 角色信息 Markdown
                character_md3 = gr.Markdown("提取的角色信息：")
                # 角色内容显示区域
                character_content_display = gr.Textbox(
                    value="请先上传并解析PDF。",
                    lines=3,
                    interactive=False,  # Display only
                    show_label=False
                )
                # 角色声音描述 Markdown
                character_md2 = gr.Markdown("角色声音描述：")

                with gr.Column(visible=False) as character_voice_preview_container:

                    # 预创建最大数量的UI组件行，初始时全部隐藏
                    MAX_CHARACTERS = 15  # 可以根据需要调整最大支持的角色数
                    character_rows = []
                    character_name_outputs = []
                    character_voice_dropdowns = []
                    character_play_buttons = []
                    character_audio_players = []
                    character_voice_reasons = []

                    for i in range(MAX_CHARACTERS):
                        with gr.Row(visible=False,equal_height=True) as row:
                            # 角色名称（不可编辑）
                            name_output = gr.Textbox(label=f"角色 {i + 1}", interactive=False, scale=1,max_lines=1)
                            # 声音选择下拉框
                            voice_dropdown = gr.Dropdown(
                                label="音色 (编号-性别-性格)",
                                choices=voice_options_list,
                                interactive=True,
                                scale=3
                            )
                            voice_reason = gr.Textbox(label=f"理由", interactive=False, scale=5,max_lines=2)
                            # 播放按钮m
                            play_btn = gr.Button("▶️ 试听", scale=1,size="sm")
                            # 隐藏的音频播放器，用于实现点击按钮播放的功能
                            audio_player = gr.Audio(visible=False, autoplay=True)
                        character_rows.append(row)
                        character_name_outputs.append(name_output)
                        character_voice_dropdowns.append(voice_dropdown)
                        character_voice_reasons.append(voice_reason)
                        character_play_buttons.append(play_btn)
                        character_audio_players.append(audio_player)

            # 剧本 Section
            with gr.Accordion("📜 剧本生成", open=False) as Accordion_Script:
                script_md = gr.Markdown("（分析内容后，点击'剧本生成'进行生成）")
                # 剧本内容显示区域
                generated_script_display = gr.Textbox(
                    label=None, show_label=False,
                    lines=15,
                    interactive=False,  # Allow user to edit generated script
                    placeholder="(点击'生成剧本'后，AI生成的剧本将显示在此)"
                )
            # TTS Section
            with gr.Accordion("🔊 TTS 生成与播放", open=False) as Accordion_TTS:
                tts_md = gr.Markdown("生成的语音")
                tts_audio_output = gr.Audio(label="生成的语音", type="filepath", interactive=False, autoplay=False)

            # 状态存储（正常模式专用）
            character_json_state = gr.State()
            storyline_json_state = gr.State()
            character_voice_json_state = gr.State()
            generated_script_json_state = gr.State()
            filename_state = gr.State()
            updated_character_voice_state = gr.State()

            # 上传/清理事件等（正常模式）
            pdf_upload.upload(
                fn=display_uploaded_file_content,
                inputs=[pdf_upload],
                outputs=[pdf_content_display, process_status_display, btn_generate, filename_state]  # 更新文件内容显示框和状态显示框
            )

            pdf_upload.clear(
                fn=clear_all_related_outputs,
                inputs=None,
                outputs=[
                    pdf_content_display,
                    process_status_display,
                    storyline_content_display,
                    character_content_display,
                    generated_script_display,
                    tts_audio_output,
                    btn_generate,
                    btn_generate_script,
                    btn_generate_voiceMatch,
                    btn_generate_tts,
                    Accordion_Storyline,
                    Accordion_Role,
                    Accordion_Script,
                    Accordion_TTS,
                    mode_switcher
                ]
            )

            # 立即更新UI状态的函数
            def disable_mode_switcher_immediately():
                return gr.update(interactive=False)

            btn_generate.click(
                fn=disable_mode_switcher_immediately,
                inputs=None,
                outputs=[mode_switcher]
            ).then(
                fn=analyze_content_process,
                inputs=[pdf_content_display],
                outputs=[
                    storyline_content_display,
                    character_content_display,
                    btn_generate_script,
                    Accordion_Storyline,
                    Accordion_Role,
                    process_status_display,
                    storyline_json_state,
                    character_json_state
                ]
            )

            btn_generate_script.click(
                fn=generate_script_process,
                inputs=[pdf_content_display, storyline_content_display, character_json_state],
                outputs=[
                    generated_script_display,
                    btn_generate_voiceMatch,
                    Accordion_Script,
                    process_status_display,
                    generated_script_json_state
                ]
            )

            for i in range(MAX_CHARACTERS):
                character_play_buttons[i].click(
                    fn=play_preview_for_character,
                    inputs=[character_voice_dropdowns[i]],
                    outputs=[character_audio_players[i]]
                )

            all_preview_outputs = [character_voice_preview_container]
            for i in range(MAX_CHARACTERS):
                all_preview_outputs.append(character_rows[i])
                all_preview_outputs.append(character_name_outputs[i])
                all_preview_outputs.append(character_voice_dropdowns[i])
                all_preview_outputs.append(character_voice_reasons[i])

            btn_generate_voiceMatch.click(
                fn=voice_match_process,
                inputs=[character_json_state, generated_script_json_state],
                outputs=[
                    btn_generate_tts,
                    Accordion_Role,
                    process_status_display,
                    character_voice_json_state
                ]
            ).then(
                fn=update_character_voice_previews,
                inputs=[character_voice_json_state],
                outputs=all_preview_outputs
            )

            all_character_ui_inputs = character_name_outputs + character_voice_dropdowns + character_voice_reasons

            btn_generate_tts.click(
                fn=tts_prepare,
                inputs=all_character_ui_inputs,
                outputs=[
                    updated_character_voice_state
                ]
            ).then(
                fn=tts_process,
                inputs=[generated_script_json_state, updated_character_voice_state,filename_state],
                outputs=[
                    tts_audio_output,
                    Accordion_TTS,
                    process_status_display
                ]
            )

            voice_json_selector.change(
                fn=preview_selected_voice_from_json,
                inputs=[voice_json_selector],
                outputs=[voice_json_preview_player]
            )
    character_json_state = gr.State()
    storyline_json_state = gr.State()
    character_voice_json_state = gr.State()
    generated_script_json_state = gr.State()
    filename_state = gr.State()
    updated_character_voice_state = gr.State()  # 用于存储用户在UI上选择的最终配音方案

    with gr.Row():
        # 上传文档（正常模式控件，初始隐藏）
        pdf_upload = gr.File(
            label="上传文件,支持PDF/TXT",
            file_types=['.pdf', '.txt'],
            scale=2,
            visible=False
        )
        # 处理状态显示（初始隐藏）
        process_status_display = gr.Textbox(label="处理状态", show_label=True, interactive=False, scale=3, max_lines=2,
                                            placeholder="上传文件后，此处将显示解析和生成状态。", visible=False)


    # 章节 Section
    with gr.Accordion("📚 章节", open=True, visible=False) as chapter_accordion:
        # 章节内容 Markdown
        chapter_content_md = gr.Markdown("上传内容")
        with gr.Row():
            with gr.Column(scale=4):
                # PDF内容显示区域
                pdf_content_display = gr.Textbox(
                    value="请先上传并解析PDF。",
                    label="章节内容 (PDF解析)",
                    lines=10,
                    max_lines=10,
                    interactive=False,  # Display only
                    show_label=False
                )

            with gr.Column(scale=1):
                # 右侧Markdown区域
                chapter_right_md = gr.Markdown("（上传PDF后，点击下方功能进行分析）")
                # 分析内容/重新分析
                btn_generate = gr.Button("✍️ 分析内容 / 重新分析", interactive=False)
                # 按钮：生成剧本
                btn_generate_script = gr.Button("📜 剧本生成", interactive=False)
                # 按钮：角色声音配对
                btn_generate_voiceMatch = gr.Button("🎭 角色声音配对", interactive=False)
                # 按钮：生成TTS
                btn_generate_tts = gr.Button("🎤 生成TTS", interactive=False)

    # 故事主线 Section
    with gr.Accordion("📖 故事线", open=False, visible=False) as Accordion_Storyline:
        # 故事线操作提示 Markdown
        storyline_md = gr.Markdown("（上传PDF后，点击'生成内容'进行分析）")
        # 故事线内容显示区域
        storyline_content_display = gr.Textbox(
            value="请先上传并解析PDF。",
            lines=5,
            interactive=False,  # Display only
            show_label=False
        )
    # 音色选择与试听 Section
    with gr.Accordion("🎤 音色选择与试听", open=True, visible=False) as voice_accordion:
        with gr.Row():
            with gr.Column():
                # 音色选择下拉框
                voice_json_selector = gr.Dropdown(
                    label="音色 (编号-性别-性格)",
                    choices=voice_options_list,  # 使用从JSON加载的显示名称列表
                    value=voice_options_list[0] if voice_options_list else None,  # 默认选择第一个音色
                    interactive=True,
                    scale=3
                )
            with gr.Column():
                # 音色试听播放器
                voice_json_preview_player = gr.Audio(
                    label="选择一个音色进行试听",
                    type="filepath",
                    interactive=False,
                    show_download_button=False,
                    show_share_button=False,
                    autoplay=False,
                    visible=False
                )

            if voice_options_list:
                initial_selected_name = voice_options_list[0]
                voice_name = voice_display_to_name_map.get(initial_selected_name)
                if voice_name and voice_name in voice_data_map:
                    audio_list = voice_data_map[voice_name].get("音频", [])
                    initial_audio_path = audio_list[0].get("wav_path")

                    if initial_audio_path and os.path.exists(initial_audio_path):
                        initial_label = f"试听: {initial_selected_name}"
                        voice_json_preview_player.value = initial_audio_path
                        voice_json_preview_player.label = initial_label
                        voice_json_preview_player.visible = True
                    else:
                        voice_json_preview_player.label = f"错误: 默认音色音频 '{initial_audio_path}' 未找到"
                        voice_json_preview_player.visible = True  # 显示错误信息

    # 角色 Section
    with gr.Accordion("🗣️ 角色", open=False, visible=False) as Accordion_Role:
        # 角色操作提示 Markdown
        character_md = gr.Markdown("（上传PDF后，点击'生成内容'进行分析）")
        # 角色信息 Markdown
        character_md3 = gr.Markdown("提取的角色信息：")
        # 角色内容显示区域
        character_content_display = gr.Textbox(
            value="请先上传并解析PDF。",
            lines=3,
            interactive=False,  # Display only
            show_label=False
        )
        # 角色声音描述 Markdown
        character_md2 = gr.Markdown("角色声音描述：")

        with gr.Column(visible=False) as character_voice_preview_container:

            # 预创建最大数量的UI组件行，初始时全部隐藏
            MAX_CHARACTERS = 15  # 可以根据需要调整最大支持的角色数
            character_rows = []
            character_name_outputs = []
            character_voice_dropdowns = []
            character_play_buttons = []
            character_audio_players = []
            character_voice_reasons = []

            for i in range(MAX_CHARACTERS):
                with gr.Row(visible=False,equal_height=True) as row:
                    # 角色名称（不可编辑）
                    name_output = gr.Textbox(label=f"角色 {i + 1}", interactive=False, scale=1,max_lines=1)
                    # 声音选择下拉框
                    voice_dropdown = gr.Dropdown(
                        label="音色 (编号-性别-性格)",
                        choices=voice_options_list,
                        interactive=True,
                        scale=3
                    )
                    voice_reason = gr.Textbox(label=f"理由", interactive=False, scale=5,max_lines=2)
                    # 播放按钮m
                    play_btn = gr.Button("▶️ 试听", scale=1,size="sm")
                    # 隐藏的音频播放器，用于实现点击按钮播放的功能
                    audio_player = gr.Audio(visible=False, autoplay=True)
                character_rows.append(row)
                character_name_outputs.append(name_output)
                character_voice_dropdowns.append(voice_dropdown)
                character_voice_reasons.append(voice_reason)
                character_play_buttons.append(play_btn)
                character_audio_players.append(audio_player)

    # 剧本 Section
    with gr.Accordion("📜 剧本生成", open=False, visible=False) as Accordion_Script:
        script_md = gr.Markdown("（分析内容后，点击'剧本生成'进行生成）")
        # 剧本内容显示区域
        generated_script_display = gr.Textbox(
            label=None, show_label=False,
            lines=15,
            interactive=False,  # Allow user to edit generated script
            placeholder="(点击'生成剧本'后，AI生成的剧本将显示在此)"
        )
    # TTS Section
    with gr.Accordion("🔊 TTS 生成与播放", open=False, visible=False) as Accordion_TTS:
        tts_md = gr.Markdown("生成的语音")
        tts_audio_output = gr.Audio(label="生成的语音", type="filepath", interactive=False, autoplay=False)



    """
    输入:
    - pdf_upload: 用户通过“上传文档”组件上传的文件对象。
    输出:
    - pdf_content_display: 更新“PDF内容显示区域”，显示从文件中提取的文本。
    - process_status_display: 更新“处理状态显示”，反馈文件上传成功等状态信息。
    - btn_generate: 激活“分析内容/重新分析”按钮，使其变为可点击。
    - filename_state: 将上传的文件名存入一个不可见的状态组件，供后续步骤使用。
    """
    pdf_upload.upload(
        fn=display_uploaded_file_content,
        inputs=[pdf_upload],
        outputs=[pdf_content_display, process_status_display, btn_generate, filename_state]  # 更新文件内容显示框和状态显示框
    )

    """
    输出 (outputs):
    - pdf_content_display, process_status_display, storyline_content_display, character_content_display, generated_script_display:
      清空所有文本显示区域，并将其重置为初始的占位符或提示文本。
    - tts_audio_output:
      清除“生成的语音”播放器中任何已存在的音频。
    - btn_generate, btn_generate_script, btn_generate_voiceMatch, btn_generate_tts:
      禁用（设置为不可交互）所有主要的功能按钮。
    - Accordion_Storyline, Accordion_Role, Accordion_Script, Accordion_TTS:
      折叠所有分析结果相关的Accordion区块，恢复UI的初始布局。
    """
    pdf_upload.clear(
        fn=clear_all_related_outputs,
        inputs=None,  # clear 事件通常不传递输入
        outputs=[  # 确保这里的顺序与 clear_all_related_outputs 函数返回值的顺序一致
            pdf_content_display,
            process_status_display,
            storyline_content_display,
            character_content_display,
            generated_script_display,
            tts_audio_output,
            btn_generate,
            btn_generate_script,
            btn_generate_voiceMatch,
            btn_generate_tts,
            Accordion_Storyline,
            Accordion_Role,
            Accordion_Script,
            Accordion_TTS,
            mode_switcher  # 重新启用模式选择器
        ]
    )

    """
    按钮：分析内容/重新分析
        输入 (inputs):
        - pdf_content_display: “PDF内容显示区域”中的文本内容，作为内容分析的源数据。

        输出 (outputs):
        - storyline_content_display: 更新“故事线内容显示区域”，展示分析出的故事线。
        - character_content_display: 更新“角色内容显示区域”，展示提取出的角色信息。
        - btn_generate_script: 激活“生成剧本”按钮，允许用户进行下一步操作。
        - Accordion_Storyline: 展开“故事主线 Section”以显示结果。
        - Accordion_Role: 展开“角色 Section”以显示结果。
        - process_status_display: 更新“处理状态显示”，反馈分析进度或完成信息。
        - storyline_json_state: 将分析出的故事线数据（通常为JSON格式）存入不可见的状态组件中。
        - character_json_state: 将分析出的角色信息数据（通常为JSON格式）存入不可见的状态组件中。
    """

    # 立即更新UI状态的函数
    def disable_mode_switcher_immediately():
        return gr.update(interactive=False)

    btn_generate.click(
        fn=disable_mode_switcher_immediately,
        inputs=None,
        outputs=[mode_switcher]
    ).then(
        fn=analyze_content_process,
        inputs=[pdf_content_display],  # 需要当前内容作为输入
        outputs=[
            storyline_content_display,  # 更新故事线
            character_content_display,  # 更新角色
            btn_generate_script,  # 更新剧本生成按钮状态
            Accordion_Storyline,
            Accordion_Role,
            process_status_display,
            storyline_json_state,
            character_json_state
        ]
    )

    """
       输入 (inputs):
       - pdf_content_display: “PDF内容显示区域”中的完整原文，提供剧本生成的详细上下文。
       - storyline_content_display: “故事线内容显示区域”的文本，作为生成剧本的核心大纲。
       - character_json_state: 存储有角色信息的不可见状态组件，用于在剧本中正确分配角色对话。

       输出 (outputs):
       - generated_script_display: 更新“剧本内容显示区域”，展示AI生成的对话式剧本。
       - btn_generate_voiceMatch: 激活“角色声音配对”按钮，解锁下一步工作流。
       - Accordion_Script: 展开“剧本 Section”以方便用户查看新生成的剧本。
       - process_status_display: 更新“处理状态显示”，反馈剧本生成完成的状态。
       - generated_script_json_state: 将生成的剧本数据（通常为JSON格式）存入不可见的状态组件，供后续TTS生成步骤使用。
   """
    btn_generate_script.click(
        fn=generate_script_process,
        inputs=[pdf_content_display, storyline_content_display, character_json_state],
        outputs=[
            generated_script_display,  # 剧本
            btn_generate_voiceMatch,  # 更新角色声音配对按钮状态
            Accordion_Script,
            process_status_display,
            generated_script_json_state
        ]
    )


    for i in range(MAX_CHARACTERS):
        character_play_buttons[i].click(
            fn=play_preview_for_character,
            inputs=[character_voice_dropdowns[i]],
            outputs=[character_audio_players[i]]
        )


    """
    --- 步骤 1: .click() ---
    当用户点击“角色声音配对”按钮时触发。
    输入 (inputs):
    - character_json_state: 存储有角色信息的不可见状态组件。
    - generated_script_json_state: 存储有已生成剧本的不可见状态组件。
    输出 (outputs):
    - btn_generate_tts: 激活“生成TTS”按钮，以进行最终的音频合成。
    - Accordion_Role: 确保“角色 Section”展开，以显示即将更新的配音建议。
    - process_status_display: 更新“处理状态显示”，反馈声音配对完成的状态。
    - character_voice_json_state: 将AI分析出的角色与推荐声音的配对结果（及理由）存入此不可见状态组件，以传递给下一步。
    --- 步骤 2: .then() ---
    在上一步的 `voice_match_process` 函数执行完毕后立即触发。
    输入 (inputs):
    - character_voice_json_state: 接收上一步输出的配音方案结果。
    输出 (outputs):
    - all_preview_outputs: 这是一个包含多个动态UI组件的列表。此步骤会根据输入的配音方案，动态地更新“角色 Section”下的声音选择区域：
        - 使与角色数量相对应的UI行(character_rows)可见。
        - 在每行中填入角色名称(character_name_outputs)。
        - 在下拉框(character_voice_dropdowns)中自动选中AI推荐的音色。
        - 显示AI给出该配音建议的理由(character_voice_reasons)。
    """
    all_preview_outputs = [character_voice_preview_container]
    for i in range(MAX_CHARACTERS):
        all_preview_outputs.append(character_rows[i])
        all_preview_outputs.append(character_name_outputs[i])
        all_preview_outputs.append(character_voice_dropdowns[i])
        all_preview_outputs.append(character_voice_reasons[i])


    btn_generate_voiceMatch.click(
        fn=voice_match_process,
        inputs=[character_json_state, generated_script_json_state],
        outputs=[
            # character_voice_display,  # 角色声音描述
            btn_generate_tts,  # 更新生成TTS按钮状态
            Accordion_Role,
            process_status_display,
            character_voice_json_state
        ]
    ).then(
        fn=update_character_voice_previews,
        inputs=[character_voice_json_state],
        outputs=all_preview_outputs  # 连接到我们所有的动态UI组件
    )

    all_character_ui_inputs = character_name_outputs + character_voice_dropdowns + character_voice_reasons

    btn_generate_tts.click(
        fn=tts_prepare,
        inputs=all_character_ui_inputs,
        outputs=[
            updated_character_voice_state
        ]
    ).then(
        fn=tts_process,
        inputs=[generated_script_json_state, updated_character_voice_state,filename_state],
        outputs=[
            tts_audio_output,  # 剧本
            Accordion_TTS,
            process_status_display
        ]
    )


    voice_json_selector.change(
        fn=preview_selected_voice_from_json,
        inputs=[voice_json_selector],
        outputs=[voice_json_preview_player]
    )

    # 添加模式选择器的事件处理（更新快速模式状态展示）
    def handle_mode_change(selected_mode):
        """当用户切换模式时，调用UIFuction中的switch_prompt_module函数"""
        switch_prompt_module(selected_mode)  # 切换Prompt模块
        return gr.update(value=f"当前模式: {selected_mode}，Prompt模块已切换")

    mode_switcher.change(
        fn=handle_mode_change,
        inputs=[mode_switcher],
        outputs=[quick_status_md]
    )


    # 应用启动时，如果默认选中了某个音色，也触发一次播放器更新
    demo.load(
        fn=initialize_audio_player_on_load,
        inputs=None,  # load事件通常没有直接的组件输入，但可以从全局变量获取
        outputs=[voice_json_preview_player]
    )



if __name__ == "__main__":
    demo.queue()
    demo.launch(server_name="127.0.0.1",server_port=7860)
