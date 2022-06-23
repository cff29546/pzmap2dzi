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

