from PIL import ImageDraw, ImageFont
from .common import render_text
from .. import util, pzdzi

CELL_COLOR = (255, 255, 0, 255) # yellow
BLOCK_COLOR = (0, 255, 0, 255) # green
CELL_FONT = ImageFont.truetype("arial.ttf", 40)
BLOCK_FONT = ImageFont.truetype("arial.ttf", 20)

def render_gridx(draw, x, y, color, width):
    xl, yl = x - pzdzi.IsoDZI.SQR_WIDTH // 2, y
    xt, yt = x, y - pzdzi.IsoDZI.SQR_HEIGHT // 2
    draw.line([xl, yl, xt, yt], fill=color, width=width)

def render_gridy(draw, x, y, color, width):
    xt, yt = x, y - pzdzi.IsoDZI.SQR_HEIGHT // 2
    xr, yr = x + pzdzi.IsoDZI.SQR_WIDTH // 2, y
    draw.line([xt, yt, xr, yr], fill=color, width=width)

class GridRender(object):
    def __init__(self, **options):
        map_path = options.get('input')
        self.cells = util.get_all_cells(map_path)
        self.cell = options.get('cell_grid', False)
        self.block = options.get('block_grid', False)

    def update_options(self, options):
        options['layers'] = 1
        return options

    def tile(self, im_getter, gx0, gy0, gl, gr, gt, gb, layer):
        drawing = []
        for gy in range(gt, gb + 1):
            for gx in range(gl, gr + 1):
                if (gx + gy) & 1:
                    continue
                sx = (gx + gy) >> 1
                sy = (gy - gx) >> 1
                
                ox, oy = pzdzi.IsoDZI.get_sqr_center(gx - gx0, gy - gy0)
                if self.cell and sx % pzdzi.CELL_SIZE == 0:
                    drawing.append((render_gridx, (ox, oy, CELL_COLOR, 5)))
                elif self.block and sx % 10 == 0:
                    drawing.append((render_gridx, (ox, oy, BLOCK_COLOR, 1)))
                if self.cell and sy % pzdzi.CELL_SIZE == 0:
                    drawing.append((render_gridy, (ox, oy, CELL_COLOR, 5)))
                elif self.block and sy % 10 == 0:
                    drawing.append((render_gridy, (ox, oy, BLOCK_COLOR, 1)))

                if self.cell and sx % pzdzi.CELL_SIZE == 1 and sy % pzdzi.CELL_SIZE == 1:
                    text = '{},{}'.format(sx // pzdzi.CELL_SIZE, sy // pzdzi.CELL_SIZE)
                    drawing.append((render_text, (ox, oy, text, CELL_COLOR, CELL_FONT)))
                if self.block and sx % 10 == 0 and sy % 10 == 0:
                    text = '{},{}'.format(sx // 10, sy // 10)
                    drawing.append((render_text, (ox, oy, text, BLOCK_COLOR, BLOCK_FONT)))

        if drawing:
            im = im_getter.get()
            draw = ImageDraw.Draw(im)
            for func, args in drawing:
                func(draw, *args)

 
    def square(self, im_getter, ox, oy, sx, sy, layer):
        cx = sx // pzdzi.CELL_SIZE
        cy = sy // pzdzi.CELL_SIZE
        if (cx, cy) not in self.cells:
            return
        drawing = []
        if self.cell and sx % pzdzi.CELL_SIZE == 0:
            drawing.append((render_gridx, (CELL_COLOR, 5)))
        elif self.block and sx % 10 == 0:
            drawing.append((render_gridx, (BLOCK_COLOR, 1)))
        if self.cell and sy % pzdzi.CELL_SIZE == 0:
            drawing.append((render_gridy, (CELL_COLOR, 5)))
        elif self.block and sy % 10 == 0:
            drawing.append((render_gridy, (BLOCK_COLOR, 1)))
        if self.cell and sx % pzdzi.CELL_SIZE == 1 and sy % pzdzi.CELL_SIZE == 1:
            text = '{},{}'.format(cx, cy)
            drawing.append((render_text, (text, CELL_COLOR, CELL_FONT)))
        if self.block and sx % 10 == 0 and sy % 10 == 0:
            text = '{},{}'.format(sx // 10, sy // 10)
            drawing.append((render_text, (text, BLOCK_COLOR, BLOCK_FONT)))

        if drawing:
            im = im_getter.get()
            draw = ImageDraw.Draw(im)
            for func, args in drawing:
                func(draw, ox, oy, *args)
 
            
TEXT_COLOR = (0, 255, 0, 128) # lime
class GridTopRender(object):
    def __init__(self, **options):
        self.font = None
        self.grid_gap = options.get('grid_gap', pzdzi.CELL_SIZE)
        self.cell_text = options.get('cell_text', False)

    def update_options(self, options):
        options['layers'] = 1
        return options

    def tile(self, im_getter, cx, cy, layer, size):
        if self.cell_text:
            if self.font is None:
                self.font = ImageFont.truetype("arial.ttf", 80 * size)
            im = im_getter.get()
            draw = ImageDraw.Draw(im)
            text = '{},{}'.format(cx, cy)
            w, h = draw.textsize(text, self.font)
            center = pzdzi.CELL_SIZE * size // 2
            draw.text((center - w // 2, center - h // 2), text, TEXT_COLOR, self.font)
        if self.grid_gap > 0:
            lines, rem = divmod(pzdzi.CELL_SIZE, self.grid_gap)
            gap = self.grid_gap * size
            for b in range(lines):
                draw.line([b * gap, 0, b * gap, pzdzi.CELL_SIZE * size], 'lime')
                draw.line([0, b * gap, pzdzi.CELL_SIZE * size, b * gap], 'lime')





