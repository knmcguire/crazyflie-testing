# Copyright (C) 2021 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import collections
import glob
import os
import toml
import traceback
import sys

from mdutils.mdutils import MdUtils
from pathlib import Path

DIR = os.path.dirname(os.path.realpath(__file__))
REQUIREMENT = os.path.join(DIR, '../requirements/')


def render_md(name: str, data: dict, md: MdUtils, level: int) -> bool:
    '''
    Render a level of the TOML requirements. If the data has a "description"
    element, we add that as a header. If an element is a "dict" we will render
    it using this method when we are done. All other elements is added in a
    table, it is there we find details about a requirement.
    '''
    if name is not None:
        # If there no rational, then this is a group, not a requirement...
        if 'rational' not in data:
            name = name.capitalize().replace('_', ' ')  # ... so we make it pretty.
        md.new_header(level=level, title=name)
        level += 1

    if 'description' in data:
        md.new_paragraph(data['description'])
        del data['description']

    req_fields = list()
    for key, value in collections.OrderedDict(sorted(data.items())).items():
        if not isinstance(value, dict):
            req_fields.extend([key, str(value).replace('\n', ' ')])
            del data[key]

    if req_fields:
        req_fields = ['Field', 'Value'] + req_fields
        rows = int(len(req_fields) / 2)
        md.new_table(columns=2, rows=rows, text=req_fields, text_align='left')

    for key, value in data.items():
        if not render_md(key, value, md, level):
            return False

    return True


def render_requirement(name: str, requirement: dict) -> bool:
    ''' Render a requiremennt file, read to a dict '''
    md = MdUtils(file_name=str(Path(name).with_suffix('')))

    md.write(f'\n\n<!-- This file is auto-generated from: {Path(name).name} -->\n\n')

    result = render_md(None, requirement['requirement'], md, level=1)
    if result:
        md.new_table_of_contents(table_title='Contents', depth=4)
        md.create_md_file()

    return result


def render():
    requirements = glob.glob(REQUIREMENT + '*.toml')
    for requirement in requirements:
        try:
            req = toml.load(open(requirement))
            if not render_requirement(requirement, req):
                print(f'Failed to render {requirement}', file=sys.stderr)
        except Exception as err:
            print(f'Failed to load requirement TOML file: {err}')
            traceback.print_exc()

    readme = MdUtils(
        file_name=os.path.join(REQUIREMENT, 'README.md'),
        title='Requirements'
    )

    readme.write('\n<!-- This file is auto-generated! -->\n')

    readme.new_paragraph(('The requirements represents what we can test '
                          'about or products and devices. They are added to '
                          'TOML files in this directory. The TOML files are '
                          'parsed from the test framework and used as input '
                          'to the tests. They are also rendered to markdown '
                          'using `utils/render_requirements.py`.\n\n'
                          'Below is a list of the current groups:\n'))

    # Linkify the requirements
    readme.new_list([
                        '[{0}]({0})'.format(Path(req).with_suffix('.md').name)
                        for req in requirements
                    ])
    readme.create_md_file()


if __name__ == "__main__":
    render()
