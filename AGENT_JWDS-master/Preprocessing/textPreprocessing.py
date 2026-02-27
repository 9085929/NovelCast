import json
import os
import shutil
import re

#读取json文件
def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

data = read_json_file("./lol_total.json")

"""
    读取原始JSON文件，将其转换为目标格式，并保存到新文件。
    :param input_file_path: 原始JSON文件的路径
    :param output_file_path: 转换后要保存的JSON文件路径
"""
def transform_data(input_file_path, output_file_path):
    with open(input_file_path, 'r', encoding='utf-8') as f:
        original_data = json.load(f)

    # 初始化转换后的数据字典和自增ID
    transformed_data = {}
    record_id = 0

    # 性别映射
    gender_map = {
        "female": "女",
        "male": "男"
    }
    # 遍历原始数据中的每一项
    for wav_path, value in original_data.items():
        labels_str = value.get("labels", "")

        # 1. 解析 labels 字符串
        # 使用\t分割，然后用：分割键值对，并存入字典方便提取
        # strip() 用于去除首尾可能存在的空白字符（包括\t）
        label_parts = labels_str.strip().split('\t')
        parsed_labels = {}
        for part in label_parts:
            if '：' in part:
                key, val = part.split('：', 1)
                parsed_labels[key.strip()] = val.strip()

        # 2. 提取需要的信息并构建新格式
        if not parsed_labels:
            print(f"警告：跳过一个空标签记录，路径为 {wav_path}")
            continue

        # 提取各个字段，如果某个字段不存在，则使用默认值（例如空字符串）
        tone = parsed_labels.get("语气", "")
        age = parsed_labels.get("年龄", "")
        gender_raw = parsed_labels.get("性别", "")
        pitch = parsed_labels.get("音高", "")
        volume = parsed_labels.get("音量", "")
        speed = parsed_labels.get("语速", "")
        asr_text = parsed_labels.get("文本", "")

        # 转换性别
        gender = gender_map.get(gender_raw, gender_raw)  # 如果找不到映射，则使用原始值

        # 3. 组合成新的记录
        new_record = {
            "id": str(record_id),
            "desc": [
                gender,
                age,
                speed,
                pitch,
                volume
            ],
            "tone": tone,
            "wav_path": wav_path,  # wav_path 来自原始数据的key
            "asr_text": asr_text,
        }

        # 4. 将新记录添加到结果字典中
        transformed_data[str(record_id)] = new_record

        # ID自增
        record_id += 1

    # 5. 将结果写入新的JSON文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        # ensure_ascii=False 保证中文字符正常显示
        # indent=2          让JSON文件格式更美观，易于阅读
        json.dump(transformed_data, f, ensure_ascii=False, indent=2)

    print(f"处理完成！总共处理了 {record_id} 条记录。")
    print(f"结果已保存到: '{output_file_path}'")

"""
根据 "文本" 字段的长度筛选 JSON 数据。

:param input_file_path: 原始JSON文件的路径
:param output_file_path: 筛选后要保存的JSON文件路径
:param min_length: 文本需要超过的最小长度 (不包含)
"""
def filter_json_by_text_length(input_file_path, output_file_path, min_length=5):

    with open(input_file_path, 'r', encoding='utf-8') as f:
        original_data = json.load(f)

    # 用于存放筛选后数据的字典
    filtered_data = {}

    # 遍历原始数据中的每一项
    for wav_path, value in original_data.items():
        # wav_path是否存在
        if not os.path.exists(wav_path):
            print(f"警告：跳过一个不存在的音频文件，路径为 {wav_path}")
            continue

        labels_str = value.get("labels", "")

        # 1. 解析 labels 字符串以找到 "文本"
        text_content = ""  # 初始化为空字符串
        label_parts = labels_str.strip().split('\t')
        for part in label_parts:
            if part.startswith("文本："):
                # 提取 "文本：" 后面的内容
                text_content = part.split('：', 1)[1]
                break  # 找到后就跳出循环

        # 2. 检查文本内容的长度
        # len() 对于中文字符，一个汉字长度为1
        if len(text_content) > min_length:
            # 如果长度大于5，则将原始记录添加到筛选结果中
            filtered_data[wav_path] = value

    # 3. 将筛选结果写入新的JSON文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=4)

    print(f"筛选完成！共找到 {len(filtered_data)} 条符合条件的记录。")
    print(f"结果已保存到: '{output_file_path}'")

"""
读取JSON文件，校正无效的文件路径，并保存到新文件。
校正逻辑：使用上一个有效路径的目录来修复当前无效路径。
"""
def correct_file_paths(input_file_path, output_file_path):

    with open(input_file_path, 'r', encoding='utf-8') as f:
        # json.load() 在Python 3.7+版本中会保持原始文件的顺序
        original_data = json.load(f)


    corrected_data = {}
    last_known_good_dir = None
    corrected_count = 0
    uncorrected_count = 0

    print("开始校正文件路径...")

    # 遍历原始数据（字典的顺序是保留的）
    for original_path, value in original_data.items():
        # Case 1: 原始路径是有效的
        if os.path.exists(original_path):
            # 将此有效条目直接添加到新数据中
            corrected_data[original_path] = value
            # 更新“最后一个已知的正确目录”
            last_known_good_dir = os.path.dirname(original_path)

        # Case 2: 原始路径是无效的，需要尝试修复
        else:
            # 如果我们已经有了一个参考目录
            if last_known_good_dir:
                # 提取原始路径中的文件名部分
                filename = original_path.split("/")[-2]+"/"+original_path.split("/")[-1]
                # filename = os.path.basename(original_path)
                # 构建新的、可能的正确路径
                new_path_attempt = os.path.join(last_known_good_dir, filename)

                # 检查新路径是否存在
                if os.path.exists(new_path_attempt):
                    # 修复成功！
                    corrected_data[new_path_attempt] = value
                    corrected_count += 1
                    # print(f"  [成功] '{original_path}' -> '{new_path_attempt}'")
                else:
                    # 修复失败，保留原始错误路径并发出警告
                    corrected_data[original_path] = value
                    uncorrected_count += 1
                    print(f"  [失败] 无法校正 '{original_path}'。尝试的路径 '{new_path_attempt}' 也不存在。")
            else:
                # 如果这是第一个条目且路径无效，则无法修复
                corrected_data[original_path] = value
                uncorrected_count += 1
                print(f"  [失败] 无法校正 '{original_path}'，因为还没有找到任何有效路径作为参考。")

    # 将校正后的数据写入新文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(corrected_data, f, ensure_ascii=False, indent=4)

    print("\n--- 校正完成 ---")
    print(f"成功校正了 {corrected_count} 个路径。")
    if uncorrected_count > 0:
        print(f"有 {uncorrected_count} 个路径无法被自动校正，已在输出文件中保留原样。")
    print(f"结果已保存到: '{output_file_path}'")


"""
将角色目录下的所有子目录中的文件移动到角色目录本身（扁平化）。
:param input_json_path: 包含正确文件路径的输入JSON文件。
:param output_json_path: 保存移动后新路径的输出JSON文件。
:param base_path: 所有音频文件的共同根目录。
"""
def flatten_character_dirs(input_json_path, output_json_path, base_path="/home/huang/lol/"):

    # 打开日志文件log.txt



    # --- 安全性第一：检查输入文件 ---
    if not os.path.exists(input_json_path):
        print(f"错误：输入JSON文件不存在 '{input_json_path}'")
        return

    print("!!! 警告：此操作将永久移动您磁盘上的文件。请确保您已备份数据。 !!!")
    # input("按 Enter键 继续...") # 如果需要，可以取消注释此行以增加一个手动确认步骤

    with open(input_json_path, 'r', encoding='utf-8') as f:
        original_data = json.load(f)

    final_data = {}
    dirs_to_cleanup = set()  # 记录所有需要清理的源目录

    moved_count = 0
    skipped_collision_count = 0
    already_correct_count = 0
    error_count = 0

    print("开始扁平化目录结构...")

    # 确保基础路径以斜杠结尾
    if not base_path.endswith(os.path.sep):
        base_path += os.path.sep

    # 遍历JSON中的每一条记录
    for source_path, value in original_data.items():
        # --- 1. 安全与有效性检查 ---
        if not os.path.exists(source_path):
            print(f"  [错误] 源文件不存在，跳过: {source_path}")
            with open("log.txt", "a", encoding='utf-8') as log_file:
                log_file.write(f"  [错误] 源文件不存在，跳过: {source_path}\n")
            final_data[source_path] = value
            error_count += 1
            continue

        if not source_path.startswith(base_path):
            print(f"  [跳过] 路径不在指定的基础路径下: {source_path}")
            with open("log.txt", "a", encoding='utf-8') as log_file:
                log_file.write(f"  [跳过] 路径不在指定的基础路径下: {source_path}\n")

            final_data[source_path] = value
            continue

        # --- 2. 路径解析 ---
        # 移除基础路径，得到相对路径，如 "含羞蓓蕾 莉莉娅/1/118372099.mp3"
        relative_path = source_path[len(base_path):]
        path_parts = relative_path.split(os.path.sep)

        # 如果路径部分小于等于2 (e.g., ['角色', '文件名'])，说明文件已在顶层，无需移动
        if len(path_parts) <= 2:
            final_data[source_path] = value
            already_correct_count += 1
            continue

        # --- 3. 构建目标路径并处理冲突 ---
        character_dir_name = path_parts[0]
        filename = path_parts[-1]

        # 目标路径，即角色目录 + 文件名
        destination_path = os.path.join(base_path, character_dir_name, filename)

        # 核心安全检查：处理文件名冲突
        if os.path.exists(destination_path):
            # 如果目标路径存在，并且不是文件本身（有时会发生自己移动到自己的情况），则为冲突
            if os.path.realpath(source_path) != os.path.realpath(destination_path):
                print(f"  [冲突] 目标文件已存在，跳过移动: {destination_path}")
                with open("log.txt", "a", encoding='utf-8') as log_file:
                    log_file.write(f"  [冲突] 目标文件已存在，跳过移动: {destination_path}\n")

                final_data[source_path] = value  # 在新JSON中保留原始路径
                skipped_collision_count += 1
                continue

        # --- 4. 执行移动 ---
        try:
            # 记录文件的原始父目录，以便后续清理
            source_dir = os.path.dirname(source_path)
            dirs_to_cleanup.add(source_dir)

            # 执行移动
            shutil.move(source_path, destination_path)
            print(f"  [成功] '{source_path}' -> '{destination_path}'")

            # 更新JSON数据为新的路径
            final_data[destination_path] = value
            moved_count += 1

        except Exception as e:
            print(f"  [致命错误] 移动 '{source_path}' 时发生异常: {e}")
            final_data[source_path] = value
            error_count += 1

    # --- 5. 清理空的子目录 ---
    print("\n开始清理空的源目录...")
    # 按路径长度降序排序，确保先处理最深的子目录
    for d in sorted(list(dirs_to_cleanup), key=len, reverse=True):
        try:
            # os.rmdir() 只会删除空目录，如果非空会抛出OSError，这正是我们想要的
            if os.path.exists(d):
                os.rmdir(d)
                print(f"  -> 已删除空目录: {d}")
        except OSError:
            # 目录不是空的（可能因为有冲突文件未移走），忽略即可
            pass
        except Exception as e:
            print(f"  [错误] 清理目录 '{d}' 时发生异常: {e}")

    # --- 6. 保存最终结果 ---
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print("\n--- 操作完成 ---")
    print(f"成功移动: {moved_count} 个文件")
    print(f"因文件名冲突而跳过: {skipped_collision_count} 个文件")
    print(f"已在正确位置无需移动: {already_correct_count} 个文件")
    print(f"因错误未处理: {error_count} 个文件")
    print(f"最终的路径信息已保存到: '{output_json_path}'")


def find_dirs_with_subdirs(base_path):
    """
    检查指定基础路径下的每个文件夹，找出其中仍然包含子文件夹的。

    :param base_path: 要检查的根目录，例如 "/home/huang/lol/"
    """
    # 确保基础路径存在且是一个目录
    if not os.path.isdir(base_path):
        print(f"错误：提供的路径 '{base_path}' 不存在或不是一个目录。")
        return

    print(f"正在检查 '{base_path}' 下的文件夹...")

    # 用来存储结果的列表
    non_flat_dirs = []

    # 遍历基础路径下的所有项目（文件和文件夹）
    try:
        top_level_items = os.listdir(base_path)
    except PermissionError:
        print(f"错误：没有权限访问 '{base_path}'。")
        return

    for item_name in top_level_items:
        # 构建完整的项目路径
        item_path = os.path.join(base_path, item_name)

        # 只处理目录（即角色文件夹）
        if os.path.isdir(item_path):
            # 现在，我们检查这个角色文件夹内部是否还有子文件夹
            try:
                # 遍历角色文件夹内部的所有内容
                for sub_item_name in os.listdir(item_path):
                    sub_item_path = os.path.join(item_path, sub_item_name)

                    # 如果在内部发现了一个目录，就说明这个角色文件夹不“平坦”
                    if os.path.isdir(sub_item_path):
                        # 记录下这个角色文件夹的路径
                        non_flat_dirs.append(item_path)
                        # 找到一个就足够了，跳出内层循环，检查下一个角色文件夹
                        break
            except PermissionError:
                print(f"警告：没有权限访问 '{item_path}'，已跳过。")

    # 打印最终结果
    print("\n--- 检查结果 ---")
    if not non_flat_dirs:
        print("🎉 恭喜！所有文件夹都已成功扁平化，不再包含任何子文件夹。")
    else:
        print("⚠️ 以下文件夹仍然包含子文件夹：")
        for path in non_flat_dirs:
            print(f"  - {path}")


def valid(input_file_path,output_json_path):
    final_data = {}
    with open(input_file_path, 'r', encoding='utf-8') as f:
        # json.load() 在Python 3.7+版本中会保持原始文件的顺序
        original_data = json.load(f)
    for original_path, value in original_data.items():
        # Case 1: 原始路径是有效的
        if os.path.exists(original_path):
            final_data[original_path] = value
            continue
        else:
            print(f"文件不存在: {original_path}")
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)


def valid2(input_file_path,output_json_path):
    final_data = {}
    chars_to_check = {"漫", "幻", "家"}
    with open(input_file_path, 'r', encoding='utf-8') as f:
        # json.load() 在Python 3.7+版本中会保持原始文件的顺序
        original_data = json.load(f)
    for original_path, value in original_data.items():
        # Case 1: 原始路径是有效的
        if os.path.exists(original_path):
            if all(char in original_path for char in chars_to_check):
                print(f"文件名包含指定字符: {original_path}")
            else:
                final_data[original_path] = value
            continue
        else:
            print(f"文件不存在: {original_path}")
    # with open(output_json_path, 'w', encoding='utf-8') as f:
    #     json.dump(final_data, f, ensure_ascii=False, indent=4)


"""
清理JSON中文件路径的噪声，并在文件系统中实际重命名文件。
规则1: 移除括号/方括号及其内容, 如 (text) 或 [text]。
规则2: 移除文件名末尾、扩展名前的空格, 如 "name .mp3" -> "name.mp3"。
"""
def clean_and_rename_files_advanced(input_json_path, output_json_path):

    # --- 安全性第一：检查输入文件 ---
    if not os.path.exists(input_json_path):
        print(f"错误：输入JSON文件不存在 '{input_json_path}'")
        return

    print("!!! 警告：此操作将永久重命名您磁盘上的文件。请确保您已备份数据。 !!!")

    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 规则1: 匹配括号/方括号及其中的内容
    # noise_pattern = re.compile(r"[\(\[（【].*?[\)\]）】]")
    # noise_pattern = re.compile(
    #     r"[\s\(\[（【{]*(?:漫|幻|家|[\s\`~-])+[\s\)\]）】}]*"
    # )
    noise_pattern = re.compile(r"[\(\[（【{][^\])}】]+[\)\]）】}]")
    string_to_remove = "漫幻家动漫"

    final_data = {}
    renamed_count = 0
    skipped_count = 0
    error_count = 0

    print("开始清理文件名并重命名文件...")

    # 遍历JSON中的每一条记录
    for original_path, value in data.items():
        dir_name = os.path.dirname(original_path)
        base_name = os.path.basename(original_path)

        # --- 文件名清理流程 ---
        # 1. 应用规则1：移除括号内容
        temp_cleaned_name = noise_pattern.sub('', base_name).strip()

        # 2. 应用规则2：移除扩展名前的空格
        #    os.path.splitext能安全地分离文件名和扩展名
        #    例如 "abc .mp3" -> ('abc ', '.mp3')

        temp_cleaned_name = temp_cleaned_name.replace(string_to_remove, "")

        name_part, extension_part = os.path.splitext(temp_cleaned_name)

        #    只对文件名部分使用rstrip()来移除末尾的空格
        name_part = name_part.rstrip()

        #    重新组合成干净的文件名
        cleaned_base_name = name_part + extension_part

        # 3. (可选但推荐) 将文件名内部的多个连续空格替换为单个空格
        cleaned_base_name = re.sub(r'\s+', ' ', cleaned_base_name)

        # 如果清理后文件名没有变化，则直接保留
        if cleaned_base_name == base_name:
            final_data[original_path] = value
            continue

        new_path = os.path.join(dir_name, cleaned_base_name)

        # --- 核心重命名逻辑与安全检查 ---
        try:
            # 1. 检查源文件是否存在
            if not os.path.exists(original_path):
                print(f"  [错误] 源文件不存在，无法重命名: {original_path}")
                final_data[original_path] = value
                error_count += 1
                continue

            # 2. 检查目标文件是否已存在，防止覆盖
            if os.path.exists(new_path):
                print(f"  [冲突]{base_name} 目标文件已存在，跳过重命名: {new_path}")
                # final_data[original_path] = value
                skipped_count += 1
                continue

            # 3. 执行重命名
            shutil.move(original_path, new_path)
            print(f"  [成功] '{base_name}' -> '{cleaned_base_name}'")

            # 使用新的路径更新JSON数据
            final_data[new_path] = value
            renamed_count += 1

        except Exception as e:
            print(f"  [致命错误]{base_name} 重命名 '{original_path}' 时发生异常: {e}")
            final_data[original_path] = value
            error_count += 1

    # 将最终结果写入新的JSON文件
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print("\n--- 操作完成 ---")
    print(f"成功重命名: {renamed_count} 个文件")
    print(f"因目标已存在而跳过: {skipped_count} 个文件")
    print(f"因错误未处理: {error_count} 个文件")
    print(f"最终的路径信息已保存到: '{output_json_path}'")

"""
根据一个“黄金标准”JSON文件，删除指定扫描路径下所有不在JSON中的.mp3文件。

:param json_path: 最终的、包含所有应保留文件路径的JSON文件。
:param scan_path: 要扫描和清理的磁盘根目录。
:param dry_run: 如果为True，则只打印将要删除的文件，不执行实际删除。
"""
def clean_disk_based_on_json(json_path, scan_path, dry_run=True):

    # =========================================================================
    # ！！！ 警告：这是一个破坏性操作，会永久删除文件。请务必小心！ ！！！
    # =========================================================================


    with open(json_path, 'r', encoding='utf-8') as f:
        golden_data = json.load(f)

    # 将所有应保留的路径放入一个集合中，以便快速查找。
    # 使用 os.path.abspath 确保路径格式统一。
    files_to_keep = {os.path.abspath(p) for p in golden_data.keys()}
    print(f"加载完成，共 {len(files_to_keep)} 个文件需要保留。")
    print("-" * 50)

    # 步骤 2: 扫描磁盘获取所有存在的.mp3文件
    print(f"步骤 2: 正在扫描磁盘目录 '{scan_path}' 获取所有.mp3文件...")
    files_on_disk = set()
    for root, dirs, files in os.walk(scan_path):
        for name in files:
            # 您可以根据需要添加更多音频格式，如.wav, .flac等
            if name.lower().endswith('.mp3'):
                full_path = os.path.abspath(os.path.join(root, name))
                files_on_disk.add(full_path)

    print(f"扫描完成，磁盘上共找到 {len(files_on_disk)} 个.mp3文件。")
    print("-" * 50)

    # 步骤 3: 找出需要删除的文件
    # 使用集合的差集运算，找出在磁盘上但不在保留列表中的文件
    files_to_delete = files_on_disk - files_to_keep

    if not files_to_delete:
        print("🎉 恭喜！磁盘非常干净，没有需要删除的文件。")
        return

    print(f"步骤 3: 比较完成，发现 {len(files_to_delete)} 个多余的文件需要删除。")
    print("-" * 50)

    # 步骤 4: 执行操作（演习或真实删除）
    if dry_run:
        print("--- 演习模式 (DRY RUN) ---")
        print("以下文件将被删除（但现在不会执行任何操作）：")
        # 只打印前50个作为示例，避免刷屏
        for i, file_path in enumerate(list(files_to_delete)):
            print(f"  - {file_path}")
        print("\n演习结束。要真正删除这些文件，请在脚本中将 DRY_RUN 设置为 False 并重新运行。")
    else:
        print("--- 真实删除模式 (DELETION MODE) ---")
        print("！！！即将永久删除以下文件！！！")
        # 再次确认
        confirm = input(f"您确定要永久删除这 {len(files_to_delete)} 个文件吗？此操作无法撤销！(请输入 'yes' 来确认): ")

        if confirm.lower() == 'yes':
            print("正在删除文件...")
            deleted_count = 0
            error_count = 0
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    print(f"  [已删除] {file_path}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  [删除失败] {file_path} - 原因: {e}")
                    error_count += 1
            print("\n--- 删除完成 ---")
            print(f"成功删除: {deleted_count} 个文件")
            print(f"删除失败: {error_count} 个文件")
        else:
            print("操作已取消。没有文件被删除。")


if __name__ == '__main__':
    # correct_file_paths(
    #     input_file_path="./lol_total.json",
    #     output_file_path="./lol_total_corrected.json"
    # )


    # valid("./lol_total_corrected_flattened.json","./lol_total_corrected_flattened_validated.json")

    # flatten_character_dirs("./lol_total_corrected.json","lol_total_corrected_flattened.json")

    # find_dirs_with_subdirs("/home/huang/lol/")

    # valid("./lol_total_cleaned2.json")


    # filter_json_by_text_length(
    #     input_file_path="./lol_total_corrected_flattened_validated.json",
    #     output_file_path="./lol_total_filtered_FINAL.json",
    #     min_length=8
    # )

    # valid("./lol_total_cleaned.json","./lol_total_cleaned_validated.json")
    # valid2("./lol_total_cleaned_validated.json","./lol_total_cleaned_validated2.json")

    # clean_and_rename_files_advanced(
    #     input_json_path="./lol_total_cleaned_validated.json",
    #     output_json_path="./lol_total_cleaned2.json"
    # )
    # valid2("./lol_total_cleaned2.json","./lol_total_cleaned_validated2.json")

    # filter_json_by_text_length(
    #     input_file_path="./lol_total_cleaned2.json",
    #     output_file_path="./lol_total_filtered_FINAL.json",
    #     min_length=8
    # )
    # transform_data("./lol_total.json","./lol_total_transformed.json")

    # clean_disk_based_on_json("lol_total_filtered_FINAL.json","/home/huang/lol/",False)

    with open("/home/huang/Code/Podcast/Preprocessing/lol_final_725aaa.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(len(data))
    cleaned_data = {}
    cnt = 0
    for wav_path, value in data.items():
        values = value["labels"]
        text = values.split("\t")[-2]
        text = text[3:]
        if "哈哈哈哈哈哈哈哈哈哈哈哈" in text :
            print(f"发现不合规文本: {text}，路径: {wav_path}")
            # 删除wav_path文件
            if os.path.exists(wav_path):
                os.remove(wav_path)
            else:
                print(f"警告：文件不存在，无法删除: {wav_path}")
            #删除这条记录
            cnt+=1
        else:
            cleaned_data[wav_path] = value
    with open("/home/huang/Code/Podcast/Preprocessing/lol_final_725hhh.json", 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    print(f"总共有 {cnt} 条不合规文本。新数据有:{len(cleaned_data)}")
