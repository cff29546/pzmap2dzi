import pyclipper

def clip(polyline, offset):
    pco = pyclipper.PyclipperOffset()
    if offset % 2 == 1:
       polyline = list(map(lambda p: (p[0] + 0.5, p[1] + 0.5), polyline))
    pco.AddPath(polyline, pyclipper.JT_MITER, pyclipper.ET_OPENBUTT)
    solution = pco.Execute(offset / 2.0)
    if len(solution) > 0:
        return solution[0]

def isLeft(x1, y1, x2, y2, x, y):
    return (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)

def point_in_polygon(polygon_points, x, y):
    if len(polygon_points) <= 1:
        return False
    n = 0
    end_points = polygon_points[1:] + polygon_points[:1]
    for p1, p2 in zip(polygon_points, end_points):
        x1, y1 = p1
        x2, y2 = p2
        if y1 <= y and y2 > y:
            if isLeft(x1, y1, x2, y2, x, y) > 0.0:
                n += 1
        if y2 <= y and y1 > y:
            if isLeft(x1, y1, x2, y2, x, y) < 0.0:
                n -= 1
    return n != 0

def points_bound(points):
    x = list(map(lambda p: p[0], points))
    y = list(map(lambda p: p[1], points))
    xmin = min(x)
    xmax = max(x)
    ymin = min(y)
    ymax = max(y)
    return xmin, ymin, xmax, ymax

def array2points(array):
    return [(array[i*2], array[i*2+1]) for i in range(len(array)//2)]


# direction order:
#   0
# 3 x 1
#   2
_DIR = [(0, -1), (1, 0), (0, 1), (-1, 0)]
_INSIDE = True
_OUTSIDE = False
_MAYBE_OUTSIDE = None

def get_border_from_square_map(m):
    borders = []
    for x, y in m:
        flags = []
        for i, flag in enumerate(m[x, y]):
            if flag is _MAYBE_OUTSIDE:
                xx = x + _DIR[i][0]
                yy = y + _DIR[i][1]
                flags.append(_INSIDE if (xx, yy) in m else _OUTSIDE)
            else:
                flags.append(flag)
        if _OUTSIDE in flags:
            borders.append(((x, y), flags))
    return borders

def rects_border(rects, may_overlap=False):
    m = {}
    for x, y, w, h in rects:
        dir_n_s = _INSIDE if h > 1 else _MAYBE_OUTSIDE
        dir_w_e = _INSIDE if w > 1 else _MAYBE_OUTSIDE

        # flag meannings:
        #     _INSIDE: the adjacent tile in this direction belongs to the same room
        #     _OUTSIDE: the adjacent tile in this direction is outside the room
        #     _MAYBE_OUTSIDE: Not sure, check later

        # corners
        m[x        , y        ] = (_MAYBE_OUTSIDE,        dir_w_e,        dir_n_s,  _MAYBE_OUTSIDE)
        m[x        , y + h - 1] = (       dir_n_s,        dir_w_e, _MAYBE_OUTSIDE,  _MAYBE_OUTSIDE)
        m[x + w - 1, y        ] = (_MAYBE_OUTSIDE, _MAYBE_OUTSIDE,        dir_n_s,         dir_w_e)
        m[x + w - 1, y + h - 1] = (       dir_n_s, _MAYBE_OUTSIDE, _MAYBE_OUTSIDE,         dir_w_e)

        # edges
        for i in range(1, w - 1):
            m[x + i, y        ] = (_MAYBE_OUTSIDE, _INSIDE,        dir_n_s, _INSIDE)
            m[x + i, y + h - 1] = (       dir_n_s, _INSIDE, _MAYBE_OUTSIDE, _INSIDE)
        for j in range(1, h - 1):
            m[x        , y + j] = (_INSIDE,        dir_w_e, _INSIDE, _MAYBE_OUTSIDE)
            m[x + w - 1, y + j] = (_INSIDE, _MAYBE_OUTSIDE, _INSIDE,        dir_w_e) 

        if may_overlap:
            for i in range(1, w - 1):
                for j in range(1, h - 1):
                    m[x, y] = [_INSIDE] * 4
            
    borders = get_border_from_square_map(m)
    return borders

def label_order(x, y):
    return (x + y, x)

def label_square(rects):
    labelx = None
    labely = None
    for x, y, w, h in rects:
        if labelx is None or label_order(x, y) < label_order(labelx, labely):
            labelx = x
            labely = y
    return labelx, labely


# isometric direction order:
# 3   0
#   x
# 2   1

X_START_WEIGHT = [
    # start_flag:
    #  outside;  inside
    #
    #  w pad_x;  w pad_x;
    [( 0,  0), ( 0, -1)], # dir = 0 (N)
    [( 1, -1), ( 1,  0)], # dir = 1 (E)
    [( 0,  0), ( 0,  1)], # dir = 2 (S)
    [(-1,  1), (-1,  0)], # dir = 3 (W)
]

Y_START_WEIGHT = [
    # start_flag:
    #  outside;  inside
    #
    #  h pad_y;  h pad_y;
    [(-1,  1), (-1,  0)], # dir = 0 (N)
    [( 0,  0), ( 0, -1)], # dir = 1 (E)
    [( 1, -1), ( 1,  0)], # dir = 2 (S)
    [( 0,  0), ( 0,  1)], # dir = 3 (W)
]

X_END_WEIGHT = [
    # start_flag:
    #  outside;  inside
    #
    #  w pad_x;  w pad_x;
    [( 1, -1), ( 1,  0)], # dir = 0 (N)
    [( 0,  0), ( 0, -1)], # dir = 1 (E)
    [(-1,  1), (-1,  0)], # dir = 2 (S)
    [( 0,  0), ( 0,  1)], # dir = 3 (W)
]

Y_END_WEIGHT = [
    # start_flag:
    #  outside;  inside
    #
    #  h pad_y;  h pad_y;
    [( 0,  0), ( 0,  1)], # dir = 0 (N)
    [( 1, -1), ( 1,  0)], # dir = 1 (E)
    [( 0,  0), ( 0, -1)], # dir = 2 (S)
    [(-1,  1), (-1,  0)], # dir = 3 (W)
]

def get_edge(edge_dir, start_flag, end_flag, x, y, w, h, pad_x, pad_y):
    ww, wpx = X_START_WEIGHT[edge_dir][start_flag]
    x1 = x + ww * w + wpx * pad_x
    wh, wpy = Y_START_WEIGHT[edge_dir][start_flag]
    y1 = y + wh * h + wpy * pad_y
    ww, wpx = X_END_WEIGHT[edge_dir][end_flag]
    x2 = x + ww * w + wpx * pad_x
    wh, wpy = Y_END_WEIGHT[edge_dir][end_flag]
    y2 = y + wh * h + wpy * pad_y
    return [x1, y1, x2, y2]

def get_edge_segments(border_flags, x, y, w, h, pad_x, pad_y):
    edges = []
    for edge_dir, flag in enumerate(border_flags):
        if flag == _INSIDE:
            continue
        start_flag = border_flags[(edge_dir - 1) % 4]
        end_flag = border_flags[(edge_dir + 1) % 4]
        edges.append(get_edge(edge_dir, start_flag, end_flag, x, y, w, h, pad_x, pad_y))
    return edges

def rect_cover(tile_set):
    m = []
    xlast = None
    ylast = None
    current = None
    xpos = 0
    ypos = 0
    length = 0
    for x, y in sorted(tile_set) + [('end', 'end')]:
        if x == xlast and y == ylast + 1:
            length += 1
        else:
            if length:
                current[1].append((ypos, length))
            ypos = y
            length = 1
        if x != xlast:
            if current:
                m.append(current)
            xpos = x
            current = [x, []]
        xlast = x
        ylast = y

    last = None
    lastx = None
    rects = []
    length = 0
    for x, slots in m:
        if lastx == x - 1 and slots == last:
            length += 1
        else:
            if last:
                for y, l in last:
                    rects.append([lastx - length + 1, y, length, l])
            length = 1
        last = slots
        lastx = x
    if last:
        for y, l in last:
            rects.append([lastx - length + 1, y, length, l])
    return rects


