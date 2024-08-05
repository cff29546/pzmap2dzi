import requests
import re

URL_TEMPLATE = 'https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}'
TITLE_PATTERN = re.compile('<div class="workshopItemTitle">(.*?)</div>')
DEP_PATTERN = re.compile('<a href="([^"]*)"[^>]*>\\s*<div class="requiredItem">\\s*(.*?)\\s*</div>\\s*</a>', re.MULTILINE)

def get_title_dep(mod_id):
    url = URL_TEMPLATE.format(mod_id=mod_id)
    rsp = requests.get(url)

    title = None
    match = TITLE_PATTERN.search(rsp.text)
    if match:
        title = match.group(1)

    depend = []
    for match in DEP_PATTERN.finditer(rsp.text):
        if match:
            dep_id = match.group(1).split('=')[-1]
            dep_name = match.group(2)
            depend.append((dep_id, dep_name))

    return title, depend


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='mod dep getter')
    parser.add_argument('ids', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    for steam_id in args.ids:
        title, dep = get_title_dep(steam_id)
        print(title, dep)

    #info = get_info('2782415851')
    #print(info)
    #info = get_info('2820363371')
    #print(info)
