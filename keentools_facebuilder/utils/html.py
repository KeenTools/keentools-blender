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


def skip_new_lines_and_spaces(txt):
    return re.sub("[\r\n\s]+", " ", txt)


def skip_single_tags(html):
    start = 0
    end = len(html)

    arr = list()
    while start < end:
        res = re.search("(<br>|<br\s*/>)", html[start:end])

        if res is None:
            arr.append({'type':'text', 'content':html[start:end]})
            start = end
        else:
            if res.start() > 0:
                arr.append({'type':'text', 'content': html[start:res.start()]})
            arr.append({'type':'br', 'content': res.group(0)})
            start += res.end()

    if arr == []:
        return {'type':'none', 'content':''}
    if len(arr) == 1:
        return arr[0]
    else:
        return arr


def parse_html(html):
    start = 0
    end = len(html)

    arr = list()
    while start < end:
        res = re.search("(<(.+)>((.|\n)+?)</\\2>)", html[start:end])
        if res is None:
            arr.append(skip_single_tags(html[start:end]))
            start = end
        else:
            if res.start() > 0:
                arr.append(skip_single_tags(html[start:start + res.start()]))
            arr.append({'type':res.group(2),
                        'content':parse_html(res.group(3))})
            start += res.end()
    if len(arr) == 1:
        return arr[0]
    else:
        return arr


def split_long_string(txt, limit):
    if len(txt) < limit:
        return [txt]
    start = 0
    end = len(txt)
    spaces_pos = [i for i in range(0, end) if txt[i]==' ']
    spaces_pos.append(end)  # for last call
    arr = ['']
    for p in spaces_pos:
        if p - start < limit:
            arr[-1] = txt[start:p]
        else:
            start += len(arr[-1]) + 1  # +1 to skip space
            arr.append(txt[start:p])
    arr[-1] = txt[start:end]
    return arr


def create_label(layout, txt, limit=32):
    for t in split_long_string(txt, limit):
        layout.label(text="{}".format(t))


def text_from_element(el):
    t = type(el)
    if t == list:
        txt = ''
        for t in el:
            txt += text_from_element(t)
        return txt
    elif t == dict:
        if el['type'] not in {'br', 'none'}:
            return text_from_element(el['content'])
    elif t == str:
        return el


def render_dict(layout, el):
    t = el['type']
    if t in {'h1', 'h2', 'h3', 'h4'}:
        txt = text_from_element(el['content'])
        create_label(layout, txt)

    if t in {'ul', 'p'}:
        render_main(layout, el['content'])

    elif t == 'text':
        txt = text_from_element(el['content'])
        if txt not in {'',' '}:
            create_label(layout, txt)

    elif t == 'li':
        txt = text_from_element(el['content'])
        create_label(layout, '— ' + txt)

    elif t == 'br':
        return


def render_list(layout, tree):
    for el in tree:
        if type(el) == list:
            render_list(layout, el)
        elif type(el) == dict:
            render_dict(layout, el)


def render_main(layout, el):
    if type(el) == list:
        return render_list(layout, el)
    elif type(el) == dict:
        return render_dict(layout, el)
