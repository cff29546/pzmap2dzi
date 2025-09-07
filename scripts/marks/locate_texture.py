import sys
import os
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_BASE_DIR, '../..'))
_DEFAULT_CONF = os.path.join(_BASE_DIR, '../../conf/conf.yaml')
import main
from pzmap2dzi import lotheader, cell, mptask
from pzmap2dzi.render_impl import common


class SearchCell(object):
    def __init__(self, path, textures):
        self.path = path
        self.textures = textures

    def on_job(self, job):
        x, y = job
        c = cell.load_cell(self.path, x, y)
        if not c:
            return []
        marks = []
        for sx in range(c.cell_size):
            for sy in range(c.cell_size):
                for layer in range(c.minlayer, c.maxlayer):
                    square = c.get_square(sx, sy, layer)
                    if not square:
                        continue
                    for t in square:
                        if t in self.textures:
                            wx = x * c.cell_size + sx
                            wy = y * c.cell_size + sy
                            marks.append({
                                'type': 'point', 'name': t,
                                'x': wx, 'y': wy, 'layer': layer,
                            })
        return marks


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='texture locator')
    parser.add_argument('-c', '--conf', type=str, default=_DEFAULT_CONF)
    parser.add_argument('-p', '--parallel', type=int, default=16)
    parser.add_argument('-o', '--output', type=str, default='./output.json')
    parser.add_argument('-z', '--no-zoom-limit', type=int, default=128)
    parser.add_argument('textures', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    textures = set(args.textures)
    print('Textures to locate: [ {} ]'.format(', '.join(list(textures))))
    map_path = main.get_map_path(args.conf, 'default')
    print('Loading cell headers from [{}]'.format(map_path))
    headers = lotheader.load_all_headers(map_path)
    print('Total cell headers: {}'.format(len(headers)))

    jobs = []
    for (x, y), header in headers.items():
        for texture in header['tiles']:
            if texture in textures:
                jobs.append((x, y))
                break
    print('Cells containing targets: {}'.format(len(jobs)))
    task = mptask.Task(SearchCell(map_path, textures), mptask.SplitScheduler(verbose=True))
    result = task.run(jobs, args.parallel)
    marks = [m for sub in result for m in sub]
    print('Total marks found: {}'.format(len(marks)))

    if args.no_zoom_limit and len(marks) >= args.no_zoom_limit:
        for m in marks:
            m['visible_zoom_level'] = 2
    if args.output:
        common.dump_marks(marks, args.output)
        print('{} mark(s) saved to [{}]'.format(len(marks), args.output))



