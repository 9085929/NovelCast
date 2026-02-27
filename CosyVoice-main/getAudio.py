import os
import sys
import json
import time
import re
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

# --- 路径配置 (请根据您的实际环境确认) ---
COSYVOICE_ROOT = "/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/CosyVoice-main"
sys.path.insert(0, COSYVOICE_ROOT)
sys.path.insert(0, os.path.join(COSYVOICE_ROOT, "cosyvoice/third_party/Matcha-TTS"))
VOICES_JSON_PATH = r"/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/AGENT_JWDS-master/Voices/merged_lol_data_xiyou_1028.json"

# 导入CosyVoice的核心TTS生成函数
from cosyvoice.run_Script import generate_tts

class VoiceNotFoundError(KeyError):
    pass

# --- 辅助函数 ---

def normalize_audio(audio_path, target_dbfs=-20.0):
    try:
        audio = AudioSegment.from_file(audio_path)
        if len(audio) == 0:
            print(f"[WARNING] Audio file {audio_path} is empty. Skipping normalization.")
            return
        change_in_dbfs = target_dbfs - audio.dBFS
        normalized_audio = audio.apply_gain(change_in_dbfs)
        normalized_audio.export(audio_path, format="wav")
    except CouldntDecodeError:
        print(f"[ERROR] Could not decode audio file: {audio_path}. It might be corrupted or in an unsupported format.")
    except Exception as e:
        print(f"[ERROR] Could not normalize audio file {audio_path}: {e}")

def get_voice_options_and_paths_from_json(json_path):
    voice_name_to_data = {}
    if not os.path.exists(json_path):
        print(f"[警告] 音色库文件未找到: {json_path}")
        return voice_name_to_data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[错误] 解析JSON文件 '{json_path}' 失败: {e}")
        return voice_name_to_data

    # 直接使用 Key 作为名字
    for character_full_name, voice_info in data.items():
        if "音频" in voice_info and isinstance(voice_info["音频"], list) and len(voice_info["音频"]) > 0:
            voice_name_to_data[character_full_name] = voice_info
        else:
            print(f"[警告] JSON中角色 '{character_full_name}' 的条目缺少'音频'列表或列表为空。")
    return voice_name_to_data

# CosyVoice的TTS接口函数
def get_audio_path(filenameState, final_script):
    return generate_tts(filenameState, final_script)

# ------------------------------------------------------------------
# --- 全新重构的核心处理函数 ---
# ------------------------------------------------------------------
def tts_process(generated_script, character_voice, filenameState, output_dir):
    # 1. 准备工作：加载角色配置，构建包含所有句子信息的元数据列表
    run_timestamp = int(time.time())
    print(f"[INFO] Using unique run ID: {run_timestamp} to bust any potential cache.")

    # 构建角色名称到配对声音Key的映射
    role_to_voice_name = {item["角色名称"]: item["配对声音"] for item in character_voice.get("角色声音配对", [])}
    default_narrator_voice = role_to_voice_name.get("旁白")
    script_data = generated_script.get("剧本", [])

    final_script_metadata = []
    for item in script_data:
        for scene_script in item['场景剧本']:
            content = scene_script.get('内容', '').strip()
            if not content: continue
            
            speaker = scene_script['角色']
            voice_name = role_to_voice_name.get(speaker, default_narrator_voice)
            
            if not voice_name or voice_name not in voice_data_map:
                print(f"[Warning] 角色 '{speaker}' 对应的音色 '{voice_name}' 未在音色库中找到，尝试使用旁白音色。")
                voice_name = default_narrator_voice
                if not voice_name or voice_name not in voice_data_map:
                      print(f"[Error] 角色 '{speaker}' 无可用音色，跳过此句。")
                      continue
            
            voice_info = voice_data_map[voice_name]
            available_samples = voice_info.get("音频")
            if not available_samples:
                print(f"[Error] 音色 '{voice_name}' 没有可用的音频样本，跳过。")
                continue
            
            reference_audio = available_samples[0]
            
            final_script_metadata.append({
                '内容': content,
                '语音ID': voice_name,
                '音频路径': reference_audio["路径"],
                'ASR文本': reference_audio["文本"]
            })

    # 2. 核心逻辑：逐句生成，强制停顿
    temp_files = []
    
    # 【修改点 1】初始化一个列表，而不是空的 AudioSegment
    audio_segments_list = [] 
    
    # === 配置停顿时间 (毫秒) ===
    PAUSE_BETWEEN_SENTENCES = 100 
    silence_segment = AudioSegment.silent(duration=PAUSE_BETWEEN_SENTENCES) # 预先生成静音段

    print("\n[INFO] Starting audio generation with SENTENCE-BY-SENTENCE strategy (Anti-Run-On)...")
    i = 0
    block_index = 0

    while i < len(final_script_metadata):
        start_metadata = final_script_metadata[i]
        current_speaker_id = start_metadata['语音ID']
        current_reference_audio_path = start_metadata['音频路径']
        
        first_line = start_metadata['内容']
        text_corrections = {
            "玄奘": "玄葬",        # 强制修正 'bao' -> 'zang' (利用同音字)
            # "孙悟空": "孙悟 空", # 示例：如果觉得这三个字念太快，加个空格缓冲
            # "挑剔": "挑tī",      # 示例：部分生僻字注音
        }

        # 执行替换
        for original_text, fixed_text in text_corrections.items():
            if original_text in first_line:
                # 只有当它不是“陈玄奘”这种全名时才替换（可选，因为陈玄脏读音也对，这里简单粗暴全替换即可）
                # 为了日志清晰，打印一下
                print(f"    [Auto-Fix] Replacing '{original_text}' with '{fixed_text}' to fix pronunciation.")
                first_line = first_line.replace(original_text, fixed_text)
        first_line = first_line.rstrip("。！？… ，") + "。" 
        
        text_block = [first_line]
        j = i + 1 
        full_text_for_block = text_block[0]
        
        if not full_text_for_block.endswith("……"):
             pass 
        
        print(f"  -> Generating sentence {block_index + 1}: {full_text_for_block[:30]}...")

        block_script_line = {
            '内容': full_text_for_block,
            '语音ID': current_speaker_id,
            '音频路径': current_reference_audio_path,
            'ASR文本': start_metadata['ASR文本']
        }
        
        block_filename = f"{filenameState}_sent_{run_timestamp}_{block_index}"
        
        # 调用TTS
        segment_audio_path = get_audio_path(block_filename, [block_script_line])
        
        # e. 处理生成的音频
        if segment_audio_path and os.path.exists(segment_audio_path) and os.path.getsize(segment_audio_path) > 1024:
            normalize_audio(segment_audio_path)
            try:
                segment_audio = AudioSegment.from_file(segment_audio_path)
                
                # 【修改点 2】不要用 +=，而是 append 到列表
                audio_segments_list.append(segment_audio)
                
                temp_files.append(segment_audio_path)
                print(f"     [SUCCESS] Sentence generated.")
            except Exception as e:
                print(f"     [ERROR] Could not load generated audio file {segment_audio_path}: {e}")
        else:
            print(f"     [ERROR] Failed to generate audio for: '{full_text_for_block[:20]}...'")

        # 【修改点 3】将静音也 append 到列表
        audio_segments_list.append(silence_segment)

        i = j
        block_index += 1

    # 3.收尾工作
    # 【修改点 4】检查列表是否为空
    if not audio_segments_list:
        print("[ERROR] No audio segments were generated.")
        return None

    print(f"\n[INFO] Merging all audio segments...")
    
    # 【修改点 5】使用 sum 函数一次性合并列表（极快），初始值为 empty
    # 注意：sum 的第一个参数是列表，第二个参数是起始值（AudioSegment.empty()）
    final_audio = sum(audio_segments_list, AudioSegment.empty())

    final_output_path = os.path.join(output_dir, f"{filenameState}_tts_cosyvoice_final.wav")
    print(f"[INFO] Exporting final audio...")
    final_audio.export(final_output_path, format="wav")
    print(f"\n[SUCCESS] Saved to: {final_output_path}")
    
    print("[INFO] Cleaning up temporary segment files...")
    for temp_file in temp_files:
        try: os.remove(temp_file)
        except: pass
    
    return final_output_path


# --- 主程序入口 (保持不变) ---
if __name__ == '__main__':
    # --- 您的全局变量和路径 ---
    voice_data_map = get_voice_options_and_paths_from_json(VOICES_JSON_PATH)

    base_dir = "/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/JWDS"
    start_chapter, end_chapter = 8, 8
    
    
    folder_map = {}
    try:
        folder_map = {int(d.split('-')[0]): d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d.split('-')[0].isdigit()}
    except (ValueError, IndexError): pass
    
    for chapter in range(start_chapter, end_chapter + 1):
        if chapter not in folder_map:
            print(f"[警告] 未找到章节 {chapter} 对应的文件夹，跳过！")
            continue
        
        folder_name = folder_map[chapter]
        #gen_results_dir = os.path.join(base_dir, folder_name, "gen_results") 
        gen_results_dir = os.path.join(base_dir, folder_name, "gen_teenagers")
        #gen_results_dir = os.path.join(base_dir, folder_name, "gen_adult") 
        script_path = os.path.join(gen_results_dir,'11_script_with_emotion.json')
        character_path = os.path.join(gen_results_dir, '12_role_voice_map.json')
        
        if os.path.exists(script_path) and os.path.exists(character_path):
            with open(script_path, 'r', encoding='utf-8') as f: script = json.load(f)
            with open(character_path, 'r', encoding='utf-8') as f2: character = json.load(f2)
            try:
                tts_process(script, character, folder_name, gen_results_dir)
            except VoiceNotFoundError as e:
                print(f"[错误] 生成 {folder_name} 时出错：{e}，跳过该章！")
            except Exception as e:
                print(f"[严重错误] 在处理 {folder_name} 时发生未知异常: {e}")
        else:
            print(f"[警告] 文件夹 {gen_results_dir} 中缺少 '11_script_with_emotion.json' 或 '12_role_voice_map.json' 文件，跳过！")
