import os
import sys

# GPU 配置
os.environ["CUDA_VISIBLE_DEVICES"] = "1"

import torch
import torchaudio
import uuid
import json
from tqdm import tqdm

# --- 路径配置 ---
COSYVOICE_ROOT = "/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/CosyVoice-main"
sys.path.append(COSYVOICE_ROOT)
sys.path.append(f"{COSYVOICE_ROOT}/third_party/Matcha-TTS")

# --- 导入依赖 ---
from cosyvoice.cli.cosyvoice import CosyVoice2
# 注意：这里虽然导入了 load_wav 但我们不再在主逻辑里调用它，交给模型内部处理
from cosyvoice.utils.file_utils import load_wav

# --- 模型初始化 ---
# 请确保路径正确
model_dir = '/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/CosyVoice-main/pretrained_models/CosyVoice2-0.5B'

print(f"[INFO] 正在加载 CosyVoice2 模型: {model_dir} ...")

try:
    cosyvoice = CosyVoice2(model_dir, load_jit=False, load_trt=False, fp16=True)
except Exception as e:
    print(f"[警告] 标准初始化失败，尝试简化初始化: {e}")
    cosyvoice = CosyVoice2(model_dir)

print("[INFO] 模型加载完成！")

def generate_tts(fileName, final_script):
    """
    CosyVoice2 Zero-Shot 核心生成函数 (修正版：传路径而非Tensor)
    """
    script_data = final_script
    prefixFileName = fileName.split('.')[0]
    all_audio = []
    target_sr = cosyvoice.sample_rate
    
    # 设置静音 (0.3s)
    silence_duration = 0.3
    silence = torch.zeros((1, int(target_sr * silence_duration)), dtype=torch.float32)
    
    output_dir = '/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/result'
    os.makedirs(output_dir, exist_ok=True)
    
    for i, x in enumerate(tqdm(script_data, desc="CosyVoice2 Zero-Shot 合成中")):
        if not x.get('内容'):
            continue
            
        # 1. 获取参考音频路径
        prompt_audio_path = x.get('音频路径')
        # 2. 获取参考文本
        prompt_text = x.get('ASR文本', '')
        
        if not prompt_audio_path or not prompt_text:
            print(f"\n[跳过] 第 {i} 句缺少参考音频路径或参考文本。")
            continue

        if not os.path.exists(prompt_audio_path):
            print(f"\n[错误] 参考音频文件不存在: {prompt_audio_path}")
            continue

        try:
            # 【核心修改】直接传入路径字符串 (prompt_audio_path)
            # 您的版本似乎会在内部自动调用 load_wav，传入 Tensor 会导致 "Invalid file" 错误
            for j in cosyvoice.inference_zero_shot(x['内容'], prompt_text, prompt_audio_path, stream=False):
                all_audio.append(j['tts_speech'])
                
            all_audio.append(silence)
            
        except Exception as e:
            # 增加更详细的错误打印
            print(f"\n[错误] 合成第 {i} 句失败: {e}")
            continue
            
    # --- 保存结果 ---
    if not all_audio:
        print("[警告] 未生成任何音频数据！")
        return None

    final_audio = torch.cat(all_audio, dim=1)
    unique_id = str(uuid.uuid4().hex)
    output_path = os.path.join(output_dir, f'{prefixFileName}_{unique_id}.wav')
    
    torchaudio.save(output_path, final_audio, target_sr)
    print(f"\n[成功] 音频已保存至: {output_path}")
    
    return output_path