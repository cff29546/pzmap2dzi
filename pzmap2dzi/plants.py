
_TREE_DEF = [
    ('American Holly', 'e_americanholly', True),
    ('Canadian Hemlock', 'e_canadianhemlock', True),
    ('Virginia Pine', 'e_virginiapine', True),
    ('Riverbirch', 'e_riverbirch', False),
    ('Cockspur Hawthorn', 'e_cockspurhawthorn', False),
    ('Dogwood', 'e_dogwood', False),
    ('Carolina Silverbell', 'e_carolinasilverbell', False),
    ('Yellowwood', 'e_yellowwood', False),
    ('Eastern Redbud', 'e_easternredbud', False),
    ('Redmaple', 'e_redmaple', False),
    ('American Linden', 'e_americanlinden', False),
]

def get_tree(prefix, season, snow, size, evergreen):
    is_jumbo = size >= 4
    idx = size % 4
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

class PlantsInfo(object):
    def __init__(self, season='summer2', snow=False, flower=False, large_bush=False,
                 tree_size=2, jumbo_size=3, jumbo_type=3):
        """
            season: one of ['spring', 'summer', 'summer2', 'autumn', 'winter']
            snow, flower, large_bush: True or False
            tree_size: one of [0, 1, 2, 3]
            jumbo_size: one of [0, 1, 2, 3, 4, 5]
            jumbo_type: index of tree (in _TREE_DEF) which is used to render jumbo tree

        """
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
            self.mapping['vegetation_foliage_01_{}'.format(i)] = bush[i]

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
        
        # base on game version 41.68, only following vegetation_groundcover tiles are used:
        # vegetation_groundcover_01_8 ~ _27
        # vegetation_groundcover_01_32 ~ _39
        # 8 ~ 15 : grass 0 ~ 7
        for i in range(8, 16):
            self.mapping['vegetation_groundcover_01_{}'.format(i)] = grass[i - 8]
                
        # 16 ~ 19 : grass 21
        for i in range(16, 20):
            self.mapping['vegetation_groundcover_01_{}'.format(i)] = grass[21]

        # 20 ~ 27 : grass 8 ~ 15
        for i in range(20, 28):
            self.mapping['vegetation_groundcover_01_{}'.format(i)] = grass[i - 12]

        # 32 ~ 39 : grass 16 ~ 23
        for i in range(32, 40):
            self.mapping['vegetation_groundcover_01_{}'.format(i)] = grass[i - 16]


        # small tree
        tree = []
        tree_size = max(0, min(3, int(tree_size)))
        for _, prefix, evergreen in _TREE_DEF:
            tree.append(get_tree(prefix, season, snow, tree_size, evergreen))

        # base on game version 41.68, only following vegetation_trees tiles are used:
        # vegetation_trees_01_0, _2, _3
        # vegetation_trees_01_8 ~ _15
        # 0, 2, 3 : tree 0, 1, 2
        self.mapping['vegetation_trees_01_0'] = tree[0]
        self.mapping['vegetation_trees_01_2'] = tree[1]
        self.mapping['vegetation_trees_01_3'] = tree[2]

        # 8 ~ 15 : tree 3 ~ 10
        for i in range(8, 16):
            self.mapping['vegetation_trees_01_{}'.format(i)] = tree[i - 5]

        # jumbo tree
        jumbo_size = max(tree_size, min(5, int(jumbo_size)))
        _, prefix, evergreen = _TREE_DEF[jumbo_type]
        self.mapping['jumbo_tree_01_0'] = get_tree(prefix, season, snow, jumbo_size, evergreen)

            

