_TREE_DEF = [
    # tree name, tileset number, is evergreen, wind type
    ['americanholly', 1, True, 3],
    ['americanlinden', 2, False, 2],
    ['canadianhemlock', 3, True, 3],
    ['carolinasilverbell', 4, False, 1],
    ['cockspurhawthorn', 5, False, 2],
    ['dogwood', 6, False, 2],
    ['easternredbud', 7, False, 2],
    ['redmaple', 8, False, 2],
    ['riverbirch', 9, False, 1],
    ['virginiapine', 10, True, 1],
    ['yellowwood', 11, False, 2],
]


def get_tree(prefix, season, snow, size, evergreen):
    is_jumbo = size >= 4
    idx = size % 4
    prefix = 'e_' + prefix
    prefix += 'JUMBO_1_' if is_jumbo else '_1_'
    step = 2 if is_jumbo else 4
    if snow:
        textures = [prefix + str(idx + step)]
    else:
        textures = [prefix + str(idx)]
        if not evergreen:
            if season == 'spring':
                textures.append(prefix + str(idx + step * 2))
            if season == 'summer':
                textures.append(prefix + str(idx + step * 3))
            if season == 'summer2':
                textures.append(prefix + str(idx + step * 4))
            if season == 'autumn':
                textures.append(prefix + str(idx + step * 5))
    return textures


def add_jumbo_tree_tileset(defs, file_number, name, tileset_number, is_evergreen):
    columns = 2
    rows = 2 if is_evergreen else 6
    for row in range(rows):
        for col in range(columns):
            tileset_name = "e_" + name + "JUMBO_1"
            tile_num = row * columns + col
            defs[file_number * 512 * 512 + tileset_number * 512 + tile_num] = tileset_name + "_" + str(tile_num)


def jumbo_tree_defs(file_number):
    # zombie/iso/IsoWorld.java: JumboTreeDefinitions(sprMan, fileNumber) function
    defs = {}
    defs[file_number * 512 * 512 + 12 * 512 + 0] = 'jumbo_tree_01_0'
    for name, tileset_number, is_evergreen, wind_type in _TREE_DEF:
        add_jumbo_tree_tileset(defs, file_number, name, tileset_number, is_evergreen)
    return defs


class PlantsInfo(object):
    def __init__(self, conf):
        '''
            supported conf:

            season: one of ['spring', 'summer', 'summer2', 'autumn', 'winter']
            snow, flower, large_bush: True or False
            tree_size: one of [0, 1, 2, 3]
            jumbo_size: one of [0, 1, 2, 3, 4, 5]
            jumbo_type: index of tree (in _TREE_DEF), start from 1
                        which is used to render jumbo tree

        '''

        # conf
        season = conf.get('season', 'summer2')
        snow = conf.get('snow', False)
        flower = conf.get('flower', False)
        large_bush = conf.get('large_bush', False)
        tree_size = conf.get('tree_size', 2)
        jumbo_size = conf.get('jumbo_tree_size', 3)
        jumbo_type = min(11, max(1, conf.get('jumbo_tree_type', 1)))
        no_grass = conf.get('no_ground_cover', False)
        unify_tree = min(11, max(0, conf.get('unify_tree_type', 0)))

        self.mapping = {}
        # bushes
        _bush = 'f_bushes_1_{}'
        bush = []
        for i in range(16):
            textures = []
            trunk = i % 8
            offset1 = 0
            offset2 = 0
            if large_bush:
                offset1 = 8
                offset2 = 32
            if snow:
                textures = [_bush.format(trunk + offset1 + 16)]
            else:
                textures = [_bush.format(trunk + offset1)]
                if season == 'spring':
                    textures.append(_bush.format(trunk + offset1 + 32))
                if season in ['summer', 'summer2']:
                    textures.append(_bush.format(i + offset2 + 64))
                if season == 'autumn':
                    textures.append(_bush.format(trunk + offset1 + 48))
                if flower:
                    textures.append(_bush.format(i + offset2 + 80))
            bush.append(textures)

        for i in range(16):
            textures = [] if no_grass else bush[i]
            self.mapping['vegetation_foliage_01_{}'.format(i)] = textures

        # grass
        _grass = 'd_plants_1_{}'
        grass = []
        for i in range(24):
            textures = []
            offset = (i // 8) * 16 + 16
            imod8 = i % 8
            if season == 'spring':
                textures.append(_grass.format(imod8))
            if season in ['summer', 'summer2']:
                textures.append(_grass.format(offset + imod8))
            if season == 'autumn':
                textures.append(_grass.format(8 + imod8))
            if flower:
                textures.append(_grass.format(offset + 8 + imod8))
            grass.append(textures)

        # randomize map vegetation_groundcover_01_0 ~ _47
        for i in range(48):
            textures = [] if no_grass else grass[i % 24]
            self.mapping['vegetation_groundcover_01_{}'.format(i)] = textures

        # small tree
        tree = []
        tree_size = max(0, min(3, int(tree_size)))
        for prefix, idx, evergreen, wind in _TREE_DEF:
            tree.append(get_tree(prefix, season, snow, tree_size, evergreen))

        # randomize map vegetation_trees_01_0 ~ _32
        for i in range(33):
            textures = tree[i % len(_TREE_DEF)]
            if unify_tree > 0:
                textures = tree[unify_tree - 1]
            self.mapping['vegetation_trees_01_{}'.format(i)] = textures

        # jumbo tree
        jumbo_size = max(tree_size, min(5, int(jumbo_size)))
        if unify_tree > 0:
            jumbo_type = unify_tree
        prefix, idx, evergreen, wind = _TREE_DEF[jumbo_type - 1]
        jumbo = get_tree(prefix, season, snow, jumbo_size, evergreen)
        self.mapping['jumbo_tree_01_0'] = jumbo
