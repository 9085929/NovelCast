import time
from collections import defaultdict
import re
#from Children import *
from Teenager import *
#from Adult import *
import json
import os
import copy 
import argparse
def dialogue_to_annotated_string(dialogue):
    script_lines = []
    script_lines.append('{')
    script_lines.append('  "剧本": [')
    for scene_idx, scene in enumerate(dialogue["剧本"]):
        script_lines.append('    {')
        script_lines.append(f'      "场景": {scene["场景"]},')
        script_lines.append('      "场景剧本": [')

        for i, line in enumerate(scene["场景剧本"]):
            # 转义双引号以防破坏 JSON-like 结构（虽然不是严格 JSON）
            role = line["角色"].replace('"', '\\"')
            dialogue_text = line["对白"].replace('"', '\\"')
            line_str = f'        {{"角色": "{role}", "对白": "{dialogue_text}"}}  // index {i}'
            script_lines.append(line_str)

        script_lines.append('      ]')
        script_lines.append('    }' + (',' if scene_idx < len(dialogue["剧本"]) - 1 else ''))

    script_lines.append('  ]')
    script_lines.append('}')

    return '\n'.join(script_lines)

def script_to_annotated_string_by_scene(script):
    script_lines = []
    script_lines.append('    {')
    script_lines.append(f'      "场景": {script["场景"]},')
    script_lines.append('      "场景剧本": [')

    for i, line in enumerate(script["场景剧本"]):
        role = line["角色"].replace('"', '\\"')
        dialogue_text = line["内容"].replace('"', '\\"')
        line_str = f'        {{"角色": "{role}", "内容": "{dialogue_text}"}}  // index {i}'
        script_lines.append(line_str)

    script_lines.append('      ]')
    script_lines.append('    }')
    return '\n'.join(script_lines)

def dialogue_to_annotated_string_by_scene(dialogue):
    script_lines = []
    script_lines.append('    {')
    script_lines.append(f'      "场景": {dialogue["场景"]},')
    script_lines.append('      "场景剧本": [')

    for i, line in enumerate(dialogue["场景剧本"]):
        # 转义双引号以防破坏 JSON-like 结构（虽然不是严格 JSON）
        role = line["角色"].replace('"', '\\"')
        dialogue_text = line["对白"].replace('"', '\\"')
        line_str = f'        {{"角色": "{role}", "对白": "{dialogue_text}"}}  // index {i}'
        script_lines.append(line_str)

    script_lines.append('      ]')
    script_lines.append('    }')
    return '\n'.join(script_lines)

def combine_dialogue_and_narration(dialogue,narration):
    # 构建 narration 按场景号索引的字典
    narration_by_scene = {}
    for item in narration["剧本"]:
        narration_by_scene[item["场景"]] = item["旁白内容"]

    merged_script = []

    for scene_data in dialogue["剧本"]:
        scene_num = scene_data["场景"]
        dialogues = scene_data["场景剧本"]
        narrations = narration_by_scene.get(scene_num, [])

        # 按插入位置排序旁白（确保顺序正确）
        narrations_sorted = sorted(narrations, key=lambda x: x["插入位置"])

        # 构建插入映射：位置 -> 旁白列表（支持多个旁白在同一位置）

        insert_map = defaultdict(list)
        for nar in narrations_sorted:
            insert_map[nar["插入位置"]].append(nar["旁白"])

        # 合并
        merged_lines = []
        for idx, line in enumerate(dialogues):
            # 如果当前位置有旁白，先插入所有旁白
            if idx in insert_map:
                for nar_text in insert_map[idx]:
                    merged_lines.append({"角色": "旁白", "内容": nar_text})
            # 再插入对话
            merged_lines.append({"角色": line["角色"], "内容": line["对白"]})

        # 处理插入位置超出对话长度的情况（比如插在最后）
        max_dialogue_index = len(dialogues)
        for pos in insert_map:
            if pos >= max_dialogue_index:
                for nar_text in insert_map[pos]:
                    merged_lines.append({"类型": "旁白", "内容": nar_text})

        merged_script.append({
            "场景": scene_num,
            "场景剧本": merged_lines
        })

    return {"剧本": merged_script}

def combine_script_and_emotion(script,emotion):
    # 构建 narration 按场景号索引的字典
    script_map = {scene['场景']: scene for scene in script['剧本']}

    # 步骤 2: 遍历所有的语气标注信息
    # 使用 .get('语气标注', []) 来安全地获取列表，如果键不存在则返回空列表
    for scene_annotation in emotion.get('语气标注', []):
        scene_num = scene_annotation.get('场景')

        # 查找对应的场景剧本
        target_scene = script_map.get(scene_num)

        # 如果找不到对应的场景，打印警告并跳过
        if not target_scene:
            print(f"警告: 在剧本中找不到场景 {scene_num}，跳过此场景的语气标注。")
            continue

        # 步骤 3: 遍历单个场景内的所有台词标注
        for line_annotation in scene_annotation.get('场景剧本', []):
            position = line_annotation.get('台词位置')
            guidance = line_annotation.get('语气指导')

            # 检查必要信息是否存在
            if position is None or guidance is None:
                print(f"警告: 场景 {scene_num} 中有一条标注信息不完整，已跳过。")
                continue

            # 步骤 4: 更新原始剧本
            # 检查台词位置是否有效，防止索引越界错误
            if 0 <= position < len(target_scene['场景剧本']):
                # 在对应的台词字典中添加 '语气指导' 键值对
                target_scene['场景剧本'][position]['语气指导'] = guidance
            else:
                print(f"警告: 场景 {scene_num} 的台词位置 {position} 超出范围，跳过此条标注。")

    return script

def remove_parentheses_in_script(data):
    """
    递归遍历一个数据结构（列表或字典），移除所有字符串中的括号内容。
    """
    if isinstance(data, dict):
        # 如果是字典，遍历其键值对，并对值进行递归处理
        return {key: remove_parentheses_in_script(value) for key, value in data.items()}
    elif isinstance(data, list):
        # 如果是列表，遍历其元素，并对每个元素进行递归处理
        return [remove_parentheses_in_script(item) for item in data]
    elif isinstance(data, str):
        # 如果是字符串，使用正则表达式移除括号及其内容
        # r'\(.*?\)|（.*?）' 匹配半角()和全角（）及其中的任意内容（非贪婪模式）
        # .strip() 用于移除替换后可能留下的前后空格
        return re.sub(r'\(.*?\)|（.*?）', '', data).strip()
    else:
        # 如果是其他类型（如数字），保持原样返回
        return data

def extract_character_profiles(script_data, character_database):
    """
    从剧本中提取角色，并匹配其在角色档案中的完整资料。
    :param script_data: 包含剧本信息的字典。
    :param character_database: 包含所有角色档案的字典。
    :return: 一个字典，键是剧本中的角色名，值是对应的角色档案。如果找不到则为None。
    """

    # --- 步骤 1: 创建一个高效的角色查找映射表 ---
    # 为了能快速通过“规范化名称”或“别名”找到角色档案，我们先预处理角色数据库。
    # 创建一个字典，key是各种名称，value是完整的角色档案。
    character_lookup_map = {}
    # 检查"全部角色"键是否存在，避免出错
    all_characters = character_database.get("全部角色", [])

    for profile in all_characters:
        # 添加规范化名称到映射表
        if "规范化名称" in profile:
            normalized_name = profile["规范化名称"]
            character_lookup_map[normalized_name] = profile

        # 添加所有别名到映射表
        if "别名" in profile:
            for alias in profile["别名"]:
                character_lookup_map[alias] = profile

    # --- 步骤 2: 从剧本中获取所有不重复的角色 ---
    # 使用集合(set)可以自动去除重复的角色名
    script_characters = set()

    # 检查"场景剧本"键是否存在
    scene_script = script_data.get('场景剧本', [])

    for line in scene_script:
        if "角色" in line:
            script_characters.add(line['角色'])

    # --- 步骤 3: 匹配剧本角色和档案，并生成结果 ---
    matched_profiles = {}
    for character_name in script_characters:
        # 使用.get()方法从映射表中查找角色。
        # 如果找到，返回角色档案；如果找不到（比如“旁白”、“猴子们”），返回None。
        found_profile = character_lookup_map.get(character_name)
        if found_profile:
            matched_profiles[character_name] = found_profile

    return matched_profiles

def normalize_script_characters(script_data, character_list):
    """
    根据角色列表，将剧本中的角色名称规范化。
    它会遍历剧本中的每一句台词，将别名替换为规范化名称。

    :param script_data: 包含'剧本'键的原始剧本数据字典。
    :param character_list: 包含角色规范化名称和别名的列表。
    :return: 角色名称被规范化后的剧本数据字典。
    """
    # 1. 创建一个从别名到规范化名称的映射字典，以提高查找效率
    # 例如: {"美猴王": "孙悟空", "石猴": "孙悟空", "孙悟空": "孙悟空"}
    name_map = {}
    for char_info in character_list:
        normalized_name = char_info.get("规范化名称")
        if not normalized_name:
            continue

        # 将规范化名称本身也添加到映射中
        name_map[normalized_name] = normalized_name

        # 将所有别名都映射到规范化名称
        for alias in char_info.get("别名", []):
            name_map[alias] = normalized_name

    # 2. 遍历剧本的每个场景和每句台词
    for scene in script_data.get('剧本', []):
        for line in scene.get('场景剧本', []):
            original_name = line.get('角色')
            if original_name:
                # 3. 使用映射查找规范化名称。如果找不到，则保留原始名称
                # .get(key, default) 方法在这里非常适用
                line['角色'] = name_map.get(original_name, original_name)
    return script_data

def save_or_load(file_path, func, *args, **kwargs):
    """
    一个帮助函数，用于加载或生成并保存数据。
    :param file_path: 缓存文件的路径。
    :param func: 如果缓存文件不存在，则调用此函数生成数据。
    :param args: func 的位置参数。
    :param kwargs: func 的关键字参数。
    :return: 加载或生成的数据。
    """
    if os.path.exists(file_path):
        print(f"正在从缓存加载: {os.path.basename(file_path)}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print(f"缓存未找到，正在生成: {os.path.basename(file_path)}")
        result = func(*args, **kwargs)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"已保存缓存: {os.path.basename(file_path)}")
        time.sleep(5)  # 遵循原始代码的延时
        return result
GLOBAL_HISTORY_PATH = "/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/JWDS/global_character_history.json"
def load_global_history():
    if os.path.exists(GLOBAL_HISTORY_PATH):
        with open(GLOBAL_HISTORY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_global_history(history_data):
    with open(GLOBAL_HISTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)
def process_chapter(chapter_path, output_dir):
    # 提取当前章节号 (假设文件夹格式为 "1-第一章" 或 "1_第一章")
    folder_name = os.path.basename(os.path.dirname(chapter_path)) # 获取父文件夹名
    try:
        current_chapter_num = int(re.split(r'[-_]', folder_name)[0])
    except ValueError:
        print(f"警告：无法从文件夹名 {folder_name} 解析章节号，默认设为 1")
        current_chapter_num = 1

    print(f"\n{'='*20} 开始处理第 {current_chapter_num} 章 {'='*20}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(chapter_path, 'r', encoding='utf-8') as f:
        ori = f.read()

    # 1. 故事线 (不变)
    story_line_gemini = save_or_load(
        os.path.join(output_dir, '1_story_line.json'),
        Extraction_Summary,
        ori
    )

    char_file_path = os.path.join(output_dir, '2_characters.json')
    
    # 加载全局历史
    global_history = load_global_history()
    
    # --- 1. 构建“已知角色大全” (Global Known Characters) ---
    # 我们不仅需要上一章的，还需要之前所有章节出现过的角色
    all_known_characters_map = {}
    
    # 遍历历史记录中所有小于当前章节的数据
    # 注意：这里我们按章节顺序叠加，后面的覆盖前面的（保证拿到的是该角色最近一次的状态）
    sorted_chapters = sorted([int(k) for k in global_history.keys()])
    for chap_num in sorted_chapters:
        if chap_num < current_chapter_num:
            chapter_chars = global_history[str(chap_num)]
            for char in chapter_chars:
                all_known_characters_map[char["规范化名称"]] = copy.deepcopy(char)
    
    # 将字典转回列表，这就是目前为止所有已知的角色
    known_characters_list = list(all_known_characters_map.values())

    if known_characters_list:
        print(f"已加载历史角色库，共包含 {len(known_characters_list)} 个已知角色。")
    else:
        print("未找到历史角色数据，将作为初始章节处理。")

    # 检查本地是否已生成过 (断点续传)
    if os.path.exists(char_file_path):
        print(f"正在从缓存加载本章角色: {os.path.basename(char_file_path)}")
        with open(char_file_path, 'r', encoding='utf-8') as f:
            final_chapter_characters = json.load(f)
            
        # 即使是加载缓存，也要把本章的新数据同步到 merged_chars_map 以便后续保存到 global_history
        # (这里为了简单，直接假设 final_chapter_characters 已经是全量数据)
        pass 
        
    else:
        # 调用 AI 获取增量/变化
        print("正在分析本章角色变化...")
        incremental_data = Extraction_Characters(ori, known_characters_list)
        
        updates = incremental_data.get("变化或新增角色", [])
        active_chapter_roles = incremental_data.get("本章出场角色名列表", [])
        if not updates and "全部角色" in incremental_data:
             updates = incremental_data["全部角色"]
             print(f"检测到全量角色列表 (共 {len(updates)} 个)，将作为基础库。")

        # --- 合并逻辑 ---
        # 1. 建立合并字典，初始内容为已知角色大全
        merged_chars_map = copy.deepcopy(all_known_characters_map)
        
        # 2. 应用更新
        print(f"AI 识别出 {len(updates)} 个需要更新/新增的角色。")
        for char in updates:
            name = char["规范化名称"]
            if name in merged_chars_map:
                print(f"  -> [更新] 老角色发生变化: {name} (年龄/设定更新)")
            else:
                print(f"  -> [新增] 发现新角色: {name}")
            
            # 覆盖或新增
            merged_chars_map[name] = char
        
        # 3. 转换回列表格式
        full_char_list = list(merged_chars_map.values())
        
        if active_chapter_roles:
            print(f"正在根据出场名单过滤角色 (共 {len(active_chapter_roles)} 个)...")
            filtered_char_list = []
            for name in active_chapter_roles:
                if name in merged_chars_map:
                    filtered_char_list.append(merged_chars_map[name])
                else:
                    print(f"  [警告] 出场名单中的 '{name}' 未在合并库中找到，已跳过。")
            
            final_chapter_characters = {"全部角色": filtered_char_list}
        else:
            print("  [警告] AI 未返回本章出场名单，将使用全量角色库作为兜底。")
            final_chapter_characters = {"全部角色": full_char_list}

        # 5. 保存到本地文件 (2_characters.json 现在只包含过滤后的角色)
        with open(char_file_path, 'w', encoding='utf-8') as f:
            json.dump(final_chapter_characters, f, ensure_ascii=False, indent=4)
        
        # 6. 更新全局历史文件 (必须保存全量 full_char_list，供下一章使用)
        global_history[str(current_chapter_num)] = full_char_list
        save_global_history(global_history)
        print(f"全局历史已更新：第 {current_chapter_num} 章存档完毕 (全库共 {len(full_char_list)} 个角色)。")
        
        time.sleep(5)

    # 准备后续步骤需要的字符串
    character_list = [
        {
            "规范化名称": char.get("规范化名称", ""), 
            "别名": char.get("别名", []),
            "性格特征": char.get("性格特征", [])
        }
        for char in final_chapter_characters.get("全部角色", [])
    ]
    character_list_str = json.dumps(character_list, indent=4, ensure_ascii=False)

    # 3. 改编大纲生成
    script_structure_gemini = save_or_load(
        os.path.join(output_dir, '3_script_structure.json'),
        Script_Structure_Planning,
        ori, story_line_gemini,character_list_str
    )

    # --- 准备大纲映射表 (Scene ID -> Outline) ---
    # 用于后续步骤中准确查找对应场景的大纲，防止因场景增删导致索引错位
    outline_map = {item['场景']: item for item in script_structure_gemini['改编大纲']}

    # 4. 对白生成
    dialogue_gemini_path = os.path.join(output_dir, '4_dialogue.json')
    if os.path.exists(dialogue_gemini_path):
        dialogue_gemini = save_or_load(dialogue_gemini_path, lambda: None)
    else:
        dialogue_gemini = {'剧本': []}
        last_scene_ending = ""
        for i, structure in enumerate(script_structure_gemini['改编大纲']):
            scene_dialogue_path = os.path.join(output_dir, f'4_dialogue_scene_{structure["场景"]}.json')
            tmp_structure = json.dumps(structure, indent=4, ensure_ascii=False)
            
            # --- 修改调用：传入 last_scene_ending ---
            # 注意：save_or_load 需要稍微变通一下才能传参，或者直接调用函数（为了演示逻辑，这里简化写法）
            # 如果要保留 save_or_load 的缓存功能，建议暂时把 save_or_load 去掉，直接调 Dialogue_Generation
            # 或者修改 save_or_load 支持更多参数。
            # 这里为了确保生效，建议直接调用：
            
            print(f"正在生成第 {structure['场景']} 幕对话...")
            if os.path.exists(scene_dialogue_path):
                 with open(scene_dialogue_path, 'r', encoding='utf-8') as f:
                    result = json.load(f)
            else:
                result = Dialogue_Generation(
                    ori, 
                    character_list_str, 
                    tmp_structure, 
                    last_scene_ending  # <--- 传入上一幕结尾
                )
                # 保存单场景缓存
                with open(scene_dialogue_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
            
            dialogue_gemini['剧本'].append(result)
            
            # --- 提取本幕的最后3句对话，作为下一幕的参考 ---
            try:
                last_lines = result['场景剧本'][-3:] # 取最后3句
                last_scene_ending = json.dumps(last_lines, ensure_ascii=False, indent=2)
            except:
                last_scene_ending = "" # 防止出错

        with open(dialogue_gemini_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_gemini, f, ensure_ascii=False, indent=4)

    # 5. 旁白生成
    narration_gemini_path = os.path.join(output_dir, '5_narration.json')
    if os.path.exists(narration_gemini_path):
        narration_gemini = save_or_load(narration_gemini_path, lambda: None)
    else:
        narration_gemini = {'剧本': []}
        # 注意：这里假设 Dialogue 生成的场景顺序与大纲一致
        for i, structure in enumerate(script_structure_gemini['改编大纲']):
            scene_num = structure["场景"]
            scene_narration_path = os.path.join(output_dir, f'5_narration_scene_{scene_num}.json')
            
            # 找到对应的对话脚本
            current_dialogue = None
            for d in dialogue_gemini['剧本']:
                if d['场景'] == scene_num:
                    current_dialogue = d
                    break
            
            if current_dialogue:
                tmp_structure = json.dumps(structure, indent=4, ensure_ascii=False)
                tmp_dialogue = dialogue_to_annotated_string_by_scene(current_dialogue)
                result = save_or_load(
                    scene_narration_path,
                    Narration_Generation,
                    ori, tmp_structure, tmp_dialogue
                )
                narration_gemini['剧本'].append(result)
            else:
                print(f"警告：场景 {scene_num} 缺少对话脚本，跳过旁白生成。")

        with open(narration_gemini_path, 'w', encoding='utf-8') as f:
            json.dump(narration_gemini, f, ensure_ascii=False, indent=4)

    # 6. 合并旁白与对白
    pre_script_gemini = combine_dialogue_and_narration(dialogue_gemini, narration_gemini)
    with open(os.path.join(output_dir, '6_pre_script.json'), 'w', encoding='utf-8') as f:
        json.dump(pre_script_gemini, f, ensure_ascii=False, indent=4)

    continuity_script_path = os.path.join(output_dir, '6_5_continuity_script.json')

    print("正在强制执行场景连续性增强（去重/修桥）...")
    script_structure_str = json.dumps(script_structure_gemini['改编大纲'], indent=4, ensure_ascii=False)
    pre_script_str = json.dumps(pre_script_gemini, indent=4, ensure_ascii=False)
    
    # 直接调用保存，覆盖旧文件
    continuity_script = save_or_load(
        continuity_script_path,
        Scene_Continuity_Enhancer,
        script_structure_str, pre_script_str
    )
    # 将连续性增强后的剧本作为后续步骤的基础
    current_script_base = continuity_script

    # 7. 冲突增强 (修改：基于 continuity_script 遍历，按场景ID匹配大纲)
    conflict_script_path = os.path.join(output_dir, '7_conflict_script.json')
    if os.path.exists(conflict_script_path):
        script_conflict_escalation_gemini = save_or_load(conflict_script_path, lambda: None)
    else:
        script_conflict_escalation_gemini = {'剧本': []}
        for script in current_script_base['剧本']:
            scene_num = script['场景']
            scene_conflict_path = os.path.join(output_dir, f'7_conflict_scene_{scene_num}.json')
            
            # 按场景ID查找大纲
            outline = outline_map.get(scene_num, {"场景": scene_num, "改编目标": "保持连贯", "核心冲突": "未知"})
            
            tmp_script_structure = json.dumps(outline, indent=4, ensure_ascii=False)
            tmp_script = json.dumps(script, indent=4, ensure_ascii=False)
            
            result = save_or_load(
                scene_conflict_path,
                Conflict_Escalation,
                tmp_script_structure, character_list_str, tmp_script
            )
            script_conflict_escalation_gemini['剧本'].append(result)
        with open(conflict_script_path, 'w', encoding='utf-8') as f:
            json.dump(script_conflict_escalation_gemini, f, ensure_ascii=False, indent=4)

    # 8. 剧本审查
    proofread_path = os.path.join(output_dir, '8_proofread.json')
    if os.path.exists(proofread_path):
        script_proofreader = save_or_load(proofread_path, lambda: None)
    else:
        script_proofreader = {'剧本审查': []}
        for script in script_conflict_escalation_gemini['剧本']:
            scene_num = script['场景']
            scene_proofread_path = os.path.join(output_dir, f'8_proofread_scene_{scene_num}.json')
            
            # 按场景ID查找大纲
            outline = outline_map.get(scene_num, {"场景": scene_num, "改编目标": "保持连贯"})

            tmp_script_structure = json.dumps(outline, indent=4, ensure_ascii=False)
            tmp_script = json.dumps(script, indent=4, ensure_ascii=False)
            result = save_or_load(
                scene_proofread_path,
                Proofreader,
                ori, tmp_script_structure, tmp_script, character_list_str
            )
            # 记录场景ID以便对应
            tmp_dict = {'场景': scene_num, '审查结果': result['审查结果'], '问题清单': result['问题清单']}
            script_proofreader['剧本审查'].append(tmp_dict)
        with open(proofread_path, 'w', encoding='utf-8') as f:
            json.dump(script_proofreader, f, ensure_ascii=False, indent=4)

    # 9. 迭代修正
    refine_script_path = os.path.join(output_dir, '9_refined_script.json')
    if os.path.exists(refine_script_path):
        refine_script = save_or_load(refine_script_path, lambda: None)
    else:
        refine_script = {'剧本': []}
        # 这里我们需要同时遍历 剧本 和 审查结果。
        # 假设 script_proofreader 和 script_conflict_escalation_gemini 的顺序是一致的（都是按列表生成）
        
        # 构建一个 场景ID -> 剧本 的映射，方便查找
        conflict_script_map = {s['场景']: s for s in script_conflict_escalation_gemini['剧本']}

        for review in script_proofreader['剧本审查']:
            scene_num = review['场景']
            current_script = conflict_script_map.get(scene_num)
            
            if not current_script:
                print(f"错误：找不到场景 {scene_num} 的剧本，跳过修正。")
                continue

            if review['审查结果'].strip() == '通过':
                refine_script['剧本'].append(current_script)
                continue
            
            scene_refined_path = os.path.join(output_dir, f'9_refined_scene_{scene_num}.json')
            
            outline = outline_map.get(scene_num, {"场景": scene_num})
            
            tmp_script_structure = json.dumps(outline, indent=4, ensure_ascii=False)
            tmp_script = json.dumps(current_script, indent=4, ensure_ascii=False)
            tmp_feedback = json.dumps(review, indent=4, ensure_ascii=False)
            
            result = save_or_load(
                scene_refined_path,
                Script_Revision,
                ori, tmp_script_structure, tmp_script, tmp_feedback
            )
            refine_script['剧本'].append(result)
        with open(refine_script_path, 'w', encoding='utf-8') as f:
            json.dump(refine_script, f, ensure_ascii=False, indent=4)

    # 10. 后处理：去括号、规范化
    refine_script = remove_parentheses_in_script(refine_script)
    refine_script2 = normalize_script_characters(refine_script, character_list)
    with open(os.path.join(output_dir, '9_refined_script_normalized.json'), 'w', encoding='utf-8') as f:
        json.dump(refine_script2, f, ensure_ascii=False, indent=4)

    # 11. 语气标注
    emotion_path = os.path.join(output_dir, '10_emotion.json')
    if os.path.exists(emotion_path):
        Emotion = save_or_load(emotion_path, lambda: None)
    else:
        Emotion = {'语气标注': []}
        for script in refine_script2['剧本']:
            scene_num = script['场景']
            scene_emotion_path = os.path.join(output_dir, f'10_emotion_scene_{scene_num}.json')
            str_script = script_to_annotated_string_by_scene(script)
            character_profiles_in_script = extract_character_profiles(script, final_chapter_characters)
            tmp_character = [
                {
                    "规范化名称": v.get("规范化名称", ""), "别名": v.get("别名", []),
                    "性格特征": v.get("性格特征", []), "性别": v.get("性别", "")
                }
                for v in character_profiles_in_script.values()
            ]
            tmp_character2 = json.dumps(tmp_character, indent=4, ensure_ascii=False)
            result = save_or_load(
                scene_emotion_path,
                Emotional_Guidance,
                tmp_character2, str_script
            )
            Emotion['语气标注'].append(result)
        with open(emotion_path, 'w', encoding='utf-8') as f:
            json.dump(Emotion, f, ensure_ascii=False, indent=4)

    # 12. 将语气与剧本结合
    script_with_emotion = combine_script_and_emotion(refine_script2, Emotion)
    with open(os.path.join(output_dir, '11_script_with_emotion.json'), 'w', encoding='utf-8') as f:
        json.dump(script_with_emotion, f, ensure_ascii=False, indent=4)

    # 13. 角色声音配对
    role_voice_map = save_or_load(
        os.path.join(output_dir, '12_role_voice_map.json'),
        Role_Voice_Map,
        final_chapter_characters, 
        script_with_emotion,
        global_history=global_history  # <--- 传入之前加载的那个 global_character_history.json 内容
    )

    if str(current_chapter_num) in global_history:
        chapter_record = global_history[str(current_chapter_num)]
        
        # 创建一个 角色名 -> 音色ID 的字典
        voice_lookup = { item['角色名称']: item['配对声音'] for item in role_voice_map['角色声音配对'] }
        
        # 遍历历史记录里的角色，把音色填进去
        updated_count = 0
        for char_info in chapter_record:
            name = char_info.get("规范化名称")
            if name in voice_lookup:
                char_info["配对声音"] = voice_lookup[name] # <--- 关键：写入音色字段
                updated_count += 1
        
        # 步骤C: 保存回硬盘 (GLOBAL_HISTORY_PATH)
        # 这样下一章加载 global_history 时，就能看到这一章的“配对声音”字段了
        if updated_count > 0:
            save_global_history(global_history)
            print(f"已更新全局历史库：第 {current_chapter_num} 章已补充 {updated_count} 个角色的音色信息。")

    print(f"{'-'*20} 完成章节处理: {chapter_path} {'-'*20}\n")
    return role_voice_map


if __name__ == '__main__':
    # 1. 设置命令行参数解析器
    parser = argparse.ArgumentParser(description="处理《西游记》章节，生成音频剧本所需文件。")
    # modification: 添加 nargs='+' 允许接收多个整数，例如 -c 4 5 6
    parser.add_argument(
        '-c', '--chapter',
        type=int,
        nargs='+', 
        help="指定要单独处理的章节编号（可指定多个，空格分隔）。如果未提供，则按顺序处理所有章节。"
    )
    args = parser.parse_args()

    # --- 基本路径设置 ---
    base_dir = "/home/qzh/data_hdd/home/qzh/qzh/KGW/CosyVoice-main/JWDS"
    
    # 2. 获取并排序所有章节文件夹
    try:
        all_subfolders = sorted(
            [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))],
            key=lambda x: int(x.split('-')[0]) # 按文件夹名前的数字排序
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"错误：无法在目录 {base_dir} 中找到或解析章节文件夹。请检查路径和文件夹命名格式（如 '1-第一章'）。")
        print(f"具体错误: {e}")
        exit()

    # 3. 根据用户输入决定要处理的文件夹列表
    folders_to_process = []
    
    if args.chapter is not None:
        # --- 指定章节模式 (支持多章) ---
        target_chapter_nums = args.chapter # 现在这是一个列表，例如 [4, 5]
        print(f"*** 已选择指定章节模式：将处理章节 {target_chapter_nums} ***")
        
        # 遍历所有文件夹，如果该文件夹编号在目标列表中，则加入处理队列
        for folder in all_subfolders:
            try:
                folder_num = int(folder.split('-')[0])
                if folder_num in target_chapter_nums:
                    folders_to_process.append(folder)
            except (ValueError, IndexError):
                continue
        
        # 检查是否有未找到的章节
        found_nums = [int(f.split('-')[0]) for f in folders_to_process]
        missing = set(target_chapter_nums) - set(found_nums)
        if missing:
            print(f"警告：未找到以下章节对应的文件夹: {missing}")
            
        if not folders_to_process:
            print("错误：未找到任何指定的章节文件夹，程序退出。")
            exit()
            
    else:
        # --- 顺序模式 (默认) ---
        folders_to_process = all_subfolders
        print(f"*** 已选择顺序模式：将检查并处理所有 {len(folders_to_process)} 个章节 ***")

    # 4. 遍历并处理选定的文件夹
    for folder_name in folders_to_process:
        chapter_folder_path = os.path.join(base_dir, folder_name)
        ori_path = os.path.join(chapter_folder_path, "原著-白话.txt")
        #utput_dir = os.path.join(chapter_folder_path, "gen_results")
        output_dir = os.path.join(chapter_folder_path, "gen_teenagers")
        #output_dir = os.path.join(chapter_folder_path, "gen_adult")
        
        if os.path.exists(ori_path):
            # 调用主处理函数
            process_chapter(ori_path, output_dir)
        else:
            print(f"警告: 在文件夹 {folder_name} 中未找到 '原著-白话.txt' 文件，已跳过。")

            