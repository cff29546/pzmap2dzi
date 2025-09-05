from . import pzdzi
from .render_impl import base, rooms, zombie, objects, streets

RENDER_CMD = {
    'base':         (pzdzi.IsoDZI, base.BaseRender),
    'base_top':     (pzdzi.TopDZI, base.BaseTopRender),
    'rooms':        (pzdzi.IsoDZI, rooms.RoomRender),
    'zombie':       (pzdzi.IsoDZI, zombie.ZombieRender),
    'zombie_top':   (pzdzi.TopDZI, zombie.ZombieTopRender),
    'foraging':     (pzdzi.IsoDZI, objects.ForagingRender),
    'foraging_top': (pzdzi.TopDZI, objects.ForagingTopRender),
    'objects':      (pzdzi.IsoDZI, objects.ObjectsRender),
    'streets':      (pzdzi.IsoDZI, streets.StreetsRender),
}
