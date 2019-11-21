# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ##### END GPL LICENSE BLOCK #####

import re


msg = "Hello people! <h3>What's New in KeenTools 1.5.6</h3>\n Some <br />text" \
               "<ul>\n  " \
               "<li>fixed performance issues in Nuke 12;</li>\n  " \
               "<li>pintooling performance improvements;</li>\n  " \
               "<li>fixed large frame numbers bug;</li>\n  " \
               "<li>fixed invisible model in macOS Catalina;</li>\n  " \
               "<li>minor fixes and improvements</li>\n" \
               "</ul>\n<br />\n"


def skip_new_lines_and_spaces(txt):
    return re.sub("[\r\n\s]+", " ", txt)


def skip_single_tags(html):
    # print("SKIP:", html)
    start = 0
    end = len(html)

    arr = list()
    while start < end:
        # print("skip:", len(html[start:end]), html[start:end])
        res = re.search("(<br>|<br\s*/>)", html[start:end])

        if res is None:
            arr.append(['text', html[start:end]])
            start = end
        else:
            if res.start() > 0:
                arr.append(['text', html[start:res.start()]])
            arr.append(['br', ''])
            start += res.end()
    if len(arr) == 1:
        return arr[0]
    else:
        return arr


def parse_html(html):
    # print("PARSE:", html)
    start = 0
    end = len(html)

    arr = list()
    while start < end:
        # print("parse:", len(html[start:end]), html[start:end])
        res = re.search("(<(.+)>((.|\n)+?)</\\2>)", html[start:end])
        if res is None:
            arr.append(skip_single_tags(html[start:end]))
            start = end
        else:
            if res.start() > 0:
                # print("before:", html[start:res.start()])
                arr.append(skip_single_tags(html[start:res.start()]))
            arr.append([res.group(2), parse_html(res.group(3))])
            start += res.end()
    if len(arr) == 1:
        return arr[0]
    else:
        return arr


def output_element(el):
    if type(el[1]) == list:
        render_message(el)
    elif type(el[1]) == str:
        if el[0] == 'h3':
            print("layout.label(text='{}')".format(el[1]))
        elif el[0] == 'li':
            print("layout.label(text='- {}')".format(el[1]))
        elif el[0] == 'text':
            if el[1] != ' ':
                print("layout.label(text='{}')".format(el[1]))
        else:
            print("layout.label(text='{}')".format(el[1]))


def text_from_tree(tree):
    if len(tree) == 0:
        return ''

    if type(tree) == str:
        print("tree:", tree)
        return tree

    if type(tree[1]) == str:
        print("tree1:", tree)
        return tree[1]

    if type(tree[0]) == str:
        return text_from_tree(tree[1])

    txt = ''
    for el in tree:
        txt = txt + text_from_tree(el)
    print("txt:", txt)
    return txt


def render_message(tree):
    for el in tree:
        print("el:", el)
        if type(el[0]) == str:
            output_element(el)
        if type(el[0]) == list:
            render_message(el)


res = parse_html(skip_new_lines_and_spaces(msg))
print(res)
tx = text_from_tree(res)
print("TEXT:", tx)
#render_message(res)