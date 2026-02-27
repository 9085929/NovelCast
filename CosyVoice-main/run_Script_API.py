import os
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
import uuid
from tqdm import tqdm

# --- 配置区 ---
# 请将你的 API-KEY 填入此处，或者设置环境变量 DASHSCOPE_API_KEY
dashscope.api_key = "sk-9a36723b018543e997ca94fa94ee88c8" 
MODEL_NAME = "cosyvoice-v3-plus"  # 强烈建议使用针对情感优化的 Plus 版本
OUTPUT_DIR = '/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/result'

def generate_tts(fileName, final_script):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    prefixFileName = fileName.split('.')[0]
    
    # 初始化合成器，voice 可以填一个基础音色名作为兜底
    synthesizer = SpeechSynthesizer(model=MODEL_NAME, voice='cosyvoice-v3')
    
    final_audio_bytes = b""

    for i, x in enumerate(tqdm(final_script, desc="API 合成进度")):
        text = x.get('内容', '').strip()
        if not text: continue
        
        # 修正：将参数直接传递，不使用不存在的 extra_parameters
        try:
            # 注意：这里的 prompt_audio 必须是一个公网 URL
            # 如果你暂时没有 URL，建议先注释掉 prompt 参数，
            # 使用默认音色跑通流程，或者使用百炼控制台生成的 voice_id
            audio_data = synthesizer.call(
                text=text,
                # 针对 CosyVoice 系列，尝试直接传入以下参数
                # prompt_text=x.get('ASR文本', ''),
                # prompt_audio='你的音频公网URL' 
            )
            
            if audio_data:
                final_audio_bytes += audio_data
                final_audio_bytes += b'\x00' * 9600 
        except Exception as e:
            print(f"\n[API 错误] 第 {i} 句失败: {e}")
            continue

    # ... 后续保存逻辑保持不变 ...

    if not final_audio_bytes:
        print("[警告] 未生成任何音频数据！")
        return None

    unique_id = str(uuid.uuid4().hex[:8])
    output_path = os.path.join(OUTPUT_DIR, f'{prefixFileName}_API_{unique_id}.wav')
    
    with open(output_path, 'wb') as f:
        f.write(final_audio_bytes)
    
    print(f"\n[成功] API 合成音频已保存至: {output_path}")
    return output_path