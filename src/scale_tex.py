import os
import pygame

from pygame.locals import *

path = 'files/monsters/'+input()
files = [os.path.join(path, file) for file in os.listdir(path)]

H = None
for file in files:
    img = pygame.image.load(file)
    w, h = img.get_size()
    if H is None: H = h

    surf = pygame.Surface((w, H), SRCALPHA)
    surf.blit(img, (0, H-h))
    pygame.image.save(surf, file)

    print('%d%%' %(100 * (files.index(file)+1) / len(files)))
