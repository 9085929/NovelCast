import json
import os
import re


# --- 辅助函数 ---

def parse_labels(label_string):
    """
    将标签字符串 "key1：value1\tkey2：value2" 解析成字典。
    """
    metadata = {}
    # 使用正则表达式来分割，可以更好地处理不规则的空格
    parts = re.split(r'\s+', label_string.strip())

    # 临时变量存储文本
    text_content = ""

    for part in parts:
        if not part:
            continue
        # 使用中文冒号分割
        if '：' in part:
            key, value = part.split('：', 1)
            if value =="female":
                value ="女"
            elif value == "male":
                value = "男"
            # 特别处理文本字段
            if key == "文本":
                text_content = value
            else:
                metadata[key] = value
        # 兼容英文冒号
        elif ':' in part:
            key, value = part.split(':', 1)
            if key == "文本":
                text_content = value
            else:
                metadata[key] = value

    return text_content, metadata


def get_hero_name_from_path(path):
    """
    从文件路径中提取英雄名称。
    例如: /home/huang/lol/含羞蓓蕾 莉莉娅/xxx.mp3 -> 含羞蓓蕾 莉莉娅
    """
    # os.path.dirname(path) 获取目录路径: /home/huang/lol/含羞蓓蕾 莉莉娅
    # os.path.basename(...) 获取最后一个部分: 含羞蓓蕾 莉莉娅
    return os.path.basename(os.path.dirname(path))


# --- 主逻辑 ---

def merge_data(audio_file, hero_file, output_file):
    """
    整合音频和英雄信息文件。
    """
    # 1. 加载两个JSON文件
    with open(audio_file, 'r', encoding='utf-8') as f:
        audio_data = json.load(f)
    with open(hero_file, 'r', encoding='utf-8') as f:
        # 假设英雄信息是一个对象列表
        hero_list = json.load(f)

    # 2. 创建一个以英雄名字为键的查找表，方便快速匹配
    # 注意：这里的匹配逻辑可能需要根据你的实际情况调整
    # 我们假设英雄文件夹名（如“含羞蓓蕾 莉莉娅”）能够通过英雄传记里的'name'或'other_name'找到
    hero_bio_map = {hero['name']: hero for hero in hero_list}  #莉莉娅
    hero_bio_map.update({hero['other_name']: hero for hero in hero_list if 'other_name' in hero})
    # 3. 初始化最终的数据结构
    merged_data = {}

    # 4. 遍历所有音频信息
    for path, info in audio_data.items():
        hero_name_from_path = get_hero_name_from_path(path)

        # 如果这个英雄还没在我们的整合字典里，就初始化它
        if hero_name_from_path not in merged_data:
            merged_data[hero_name_from_path] = {
                "音频": []
            }
        # 解析标签字符串
        label_str = info.get("labels", "")
        text, metadata = parse_labels(label_str)

        # 构建音频对象
        audio_clip_info = {
            "路径": path,
            "文本": text,
            "元数据": metadata
        }

        # 添加到该英雄的音频列表中
        merged_data[hero_name_from_path]["音频"].append(audio_clip_info)

    # 5. 将英雄的生平信息合并进去
    for hero_folder_name, data in merged_data.items():
        matched_bio = None
        # 尝试进行匹配。一个简单的策略是看文件夹名是否包含英雄名。
        for name, bio in hero_bio_map.items():
            if name in hero_folder_name:
                matched_bio = bio
                break  # 找到第一个匹配就停止

        if matched_bio:
            # 使用 .update() 方法将bio字典中的所有键值对复制过来
            # 把 bio 信息放在顶层
            temp_clips = data["音频"]
            data.clear()
            data.update(matched_bio)
            data["音频"] = temp_clips
            data["性别"] = data["音频"][0]["元数据"].get("性别", "未知")
            # 存入新的json
        else:
            print(f"警告：无法为英雄文件夹 '{hero_folder_name}' 找到匹配的生平信息。")

    # 6. 保存整合后的数据到新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        # json.dump 写入文件，ensure_ascii=False 保证中文正常显示，indent=2 格式化输出
        json.dump(merged_data, f, ensure_ascii=False, indent=2)

    print(f"数据整合完成！已保存到文件: {output_file}")


# --- 执行 ---
if __name__ == '__main__':
    # 请将下面的文件名替换成你的实际文件名
    audio_info_file = '/home/huang/Code/Podcast/Preprocessing/lol_final_725hhh.json'
    hero_info_file = '/home/huang/Code/Podcast/Preprocessing/hero_traits.json'
    output_json_file = 'merged_lol_data.json'

    merge_data(audio_info_file, hero_info_file, output_json_file)