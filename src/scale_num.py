import pygame
from pygame.locals import *

W = 28
for x in range(10):
    file = 'files/text/%d.png' %x

    img = pygame.image.load(file)
    w, h = img.get_size()

    surf = pygame.Surface((W, h), SRCALPHA)
    surf.blit(img, ((W-w)//2, 0))
    pygame.image.save(surf, file)
