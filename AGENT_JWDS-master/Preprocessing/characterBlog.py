import requests
import pandas as pd
import re


def get_json(url):
    headers = {'User=Agent': 'Mozilla/5.0'}
    r_j = requests.get(url, headers=headers)
    return r_j.json()


def get_hero_url_list(json):
    h_l = []
    for i in range(len(json['champions'])):
        h_l.append('https://yz.lol.qq.com/v1/zh_cn/champions/{}/index.json'.
                   format(json['champions'][i]['slug']))
    return h_l


def get_hero_info(json):
    name = json['champion']['name']
    other_name = json['champion']['title']
    release_date = json['champion']['release-date']
    roles = []
    for r in range(len(json['champion']['roles'])):
        roles.append(json['champion']['roles'][r]['name'])
    roles = '/'.join(roles)
    hero_tale = re.sub('<p>|<\\/p>', '', json['champion']['biography']['full'])
    data = pd.DataFrame({'name': name,
                         'other_name': other_name,
                         'release_date': release_date,
                         'roles': roles,
                         'hero_tale': hero_tale}, index=[0])
    return data

from tqdm import tqdm
if __name__ == '__main__':
    url = 'https://yz.lol.qq.com/v1/zh_cn/search/index.json'
    all_hero_json = get_json(url)
    hero_url_list = get_hero_url_list(all_hero_json)
    # data = get_hero_info(hero_url_list[0])
    data = pd.DataFrame(columns=['name', 'other_name', 'release_date', 'roles', 'hero_tale'])
    # 添加进度条
    tqdm.pandas(desc="Processing Heroes")

    for i in tqdm(range(len(hero_url_list))):
        hero_json = get_json(hero_url_list[i])
        hero_data = get_hero_info(hero_json)
        data = pd.concat([data, hero_data])
    data.to_json('./LOL_BLOG.json', orient='records', force_ascii=False)
