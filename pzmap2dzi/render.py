from . import pzdzi
from .render_impl import base, room, zombie, objects

RENDER_CMD = {
    'base':         (pzdzi.IsoDZI, base.BaseRender),
    'base_top':     (pzdzi.TopDZI, base.BaseTopRender),
    'room':         (pzdzi.IsoDZI, room.RoomRender),
    'zombie':       (pzdzi.IsoDZI, zombie.ZombieRender),
    'zombie_top':   (pzdzi.TopDZI, zombie.ZombieTopRender),
    'foraging':     (pzdzi.IsoDZI, objects.ForagingRender),
    'foraging_top': (pzdzi.TopDZI, objects.ForagingTopRender),
    'objects':      (pzdzi.IsoDZI, objects.ObjectsRender),
}
