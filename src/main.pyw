import os
import pygame
import numpy as np

from pygame.math import Vector3

from math import *
from OpenGL.GL import *
from OpenGL.GLU import *
from pygame.locals import *

from maze import *
from entities import *

def initOpenGl():
    glViewport(0, 0, W, H)

    # enable the use of colors and textures
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_TEXTURE_2D)

    glClearColor(0.15, 0.2, 0.1, 0.0)
    glColor(base_color)

    # lights: set up camera light
    glEnable(GL_LIGHT0)
    glLight(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.6, 0.4))
    glLight(GL_LIGHT0, GL_LINEAR_ATTENUATION, 1)

    glEnable(GL_LIGHT1)
    glEnable(GL_LIGHT2)
    glEnable(GL_LIGHT3)

    # fog
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, (0.15, 0.2, 0.1))
    glFogi(GL_FOG_MODE, GL_EXP2)
    glFogf(GL_FOG_DENSITY, 0.2)

    # set up 3d shader
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)

    # set up transparent surfaces handling
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glLoadIdentity()

def init3d():
    # lighting
    glEnable(GL_LIGHTING)

    # projection mode
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV + 10*player.sprint, W/H, 0.01, render_distance)
    glMatrixMode(GL_MODELVIEW)

    # depth test (draw nearest surfaces on top)
    glEnable(GL_DEPTH_TEST)

    glLoadIdentity()

    # get the camera matrix after rotating
    cosx, sinx, cosy, siny = cos(player.cam_rot.x), sin(player.cam_rot.x), cos(player.cam_rot.y), sin(player.cam_rot.y)
    matrix = np.array([[ cosy,         0,            -siny,        0 ],  # right
                       [ sinx*siny,    cosx,         sinx*cosy,    0 ],  # top
                       [ cosx*siny,    -sinx,        cosx*cosy,    0 ],  # front
                       [ player.cam.x, player.cam.y, player.cam.z, 1 ]]) # pos
    glLoadMatrixd(sum([list(row) for row in np.linalg.inv(matrix)], start=[]))

    # light from the camera
    glLight(GL_LIGHT0, GL_POSITION, (player.cam.x, player.cam.y, player.cam.z, 1))

    # lights from the nearest light sources
    places = sorted(lights, key=lambda pos: pos.distance_to(player.cam))[:3]
    for var, pos in zip([GL_LIGHT1, GL_LIGHT2, GL_LIGHT3], places):
        glLight(var, GL_POSITION, (pos.x, pos.y, pos.z, 1))
        glLight(var, GL_DIFFUSE, (0.8, 0.8, 1))
        glLight(var, GL_QUADRATIC_ATTENUATION, 3)

def init2d():
    # projection mode
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, W, H, 0)
    glMatrixMode(GL_MODELVIEW)

    # disable lighting
    glDisable(GL_LIGHTING)

    # disable depth test (incompatible with 2d blending)
    glDisable(GL_DEPTH_TEST)

def load_options():
    global options
    # default values
    options = {'move_keys': 'wasd', 'fov': 70, 'render_distance': 20, 'fullscreen': True, 'discord': 'True'}

    try:
        # read options file
        with open('files/options.txt') as f:
            for line in f.read().split('\n'):
                name, value = line.split('=')
                options[name.strip()] = value.strip()

        # format options
        options['fov'] = min(max(int(options['fov']), 30), 120)
        options['render_distance'] = int(options['render_distance'])
        for option in ['fullscreen', 'discord']: # bollean values
            options[option] = 'true' in options[option].lower()
    except Exception as e:
        print('Error reading options.txt:')
        print(type(e), e)

    # add missing values
    save_options()

def save_options():
    with open('files/options.txt', 'w') as f:
        f.write('\n'.join(['%s = %s' %(key, value) for key, value in options.items()]))

def init_tex():
    global textures
    # maze textures
    names = walls_names+['floor', 'mossyfloor', 'ceil', 'lightceil']+['liftfloor', 'liftwall', 'liftceil', 'lifthidden', 'gate']
    textures = {name: to_texture(pygame.image.load('files/flats/%s.png' %name)) for name in names}

    # text
    for name in [str(x) for x in range(10)]+['level']:
        surf = pygame.image.load('files/text/%s.png' %name)
        textures[name] = [to_texture(surf), surf.get_size()]

    # other textures: plain colors need a white texture
    for name in ['white', 'overlay']:
        textures[name] = to_texture(pygame.image.load('files/textures/%s.png' %name))

    # monsters textures: {[ID, size] for each texture}
    for name, texname in monsters_names:
        group = {}
        for x in range(8): # here are all the oriented textures
            x_ = str(x+1)
            for anim in range(4):
                group['walk%s%d' %(anim, x)] = 'ABCD'[anim]+x_
            group['aim%d' %x] = 'E'+x_
            group['shoot%d' %x] = 'F'+x_
            group['dmg%d' %x] = 'G'+x_
        for die in range(9):
            group['die%d' %die] = 'MNOPQRSTU'[die]+'0'

        for tex in group:
            surf = pygame.image.load('files/monsters/%s/%s%s.png' %(name, texname, group[tex]))
            group[tex] = [to_texture(surf), surf.get_size()]
        textures[name] = group

def to_texture(surf):
    # makes a texture readable by OpenGl
    texture_data = pygame.image.tostring(surf, 'RGBA', True)
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

    w, h = surf.get_size()
    gluBuild2DMipmaps(GL_TEXTURE_2D, 4, w, h, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)

    return texture_id

def update_hud(first=False):
    # update HUD from its surface
    global hud
    if not first:
        glDeleteTextures(1, [hud])
    hud = to_texture(hud_surf)

def make_maze(m, n):
    display_list = glGenLists(1) # create a display list
    glNewList(display_list, GL_COMPILE)
    maze = to_blocks(gen(n, m), len(walls_names)) # generate a maze
    lights = [] # where the ceiling lights are

    # draw the maze
    normals = [(0, 0, -1), (1, 0, 0), (0, 0, 1), (-1, 0, 0)]
    # positions are inverted because we are seeing the outside of the cubes
    offset = [[(1, 0), (0, 0)], [(1, 1), (1, 0)], [(0, 1), (1, 1)], [(0, 0), (0, 1)]]
    n, m = n*2 + 1, m*2 + 1
    for z in range(n):
        for x in range(m):
            todo = [] # walls to draw
            value = maze[z][x]
            if value > 0:
                # blocks next to
                next_to = [(x, z-1), (x+1, z), (x, z+1), (x-1, z)]
                if (0, 1) in next_to or (m-1, n-2) in next_to: # next to lift: lift wall textures
                    tex = textures['liftwall']
                else:
                    tex = textures[walls_names[value-1]] # "normal" wall texture
                if not z or (maze[z-1][x] <= 0):
                    todo.append((0, tex))
                if x == m-1 or (maze[z][x+1] <= 0):
                    todo.append((1, tex))
                if z == n-1 or (maze[z+1][x] <= 0):
                    todo.append((2, tex))
                if not x or (maze[z][x-1] <= 0):
                    todo.append((3, tex))
            elif value < 0:
                spawn = Vector3(x+0.5, 0, z+0.5)
                if value == -1:
                    entities.append(Monster(spawn, 'SoldierGun', 50))
                if value == -2:
                    entities.append(Monster(spawn, 'SoldierShotgun', 100))

            for face, tex in todo:
                a, b = offset[face]

                glBindTexture(GL_TEXTURE_2D, tex)
                glBegin(GL_QUADS)
                glNormal3dv(normals[face])
                glTexCoord2f(0, 0)
                glVertex3f(x+a[0], 0, z+a[1])
                glTexCoord2f(1, 0)
                glVertex3f(x+b[0], 0, z+b[1])
                glTexCoord2f(1, 1)
                glVertex3f(x+b[0], 1, z+b[1])
                glTexCoord2f(0, 1)
                glVertex3f(x+a[0], 1, z+a[1])
                glEnd()

            # floor and ceiling: only add them if visible
            if value <= 0:
                if (x, z) in [(0, 1), (m-1, n-2)]: # lift
                    floor = 'liftfloor'
                    ceil = 'liftceil'
                    lights.append(Vector3(x+0.5, 0.7, z+0.5))
                else:
                    if randint(0, 4):
                        floor = 'floor'
                    else:
                        floor = 'mossyfloor'
                    if randint(0, 8) and (x, z) != (m-1, n-2):
                        ceil = 'ceil'
                    else:
                        ceil = 'lightceil'
                        lights.append(Vector3(x+0.5, 0.7, z+0.5))
                for y, normal, name in [(0, 1, floor), (1, -1, ceil)]:
                    glBindTexture(GL_TEXTURE_2D, textures[name])
                    glBegin(GL_QUADS)
                    glNormal3f(0, normal, 0)
                    for dx, dz in [(0, 0), (1, 0), (1, 1), (0, 1)]:
                        glTexCoord2f(dx, dz)
                        glVertex3f(x+dx, y, z+dz)
                    glEnd()

    # lift walls leading to outside of the maze
    for x, z0, z1 in [(0, 2, 1), (m, n-2, n-1)]:
        glBindTexture(GL_TEXTURE_2D, textures['lifthidden'])
        glNormal3f(z0-z1, 0, 0)
        glBegin(GL_QUADS)
        for y, dz in [(0, 0), (1, 0), (1, 1), (0, 1)]:
            glTexCoord2f(dz, y)
            glVertex(x, y, [z0, z1][dz])
        glEnd()

    # end the display list
    glEndList()

    # prevent entities form going inside the exit elevator when closed
    maze[1][1] = maze[-2][-1] = 1

    return maze, lights, display_list

def new_level():
    global level, maze, entities, lights, maze_display, doors
    level += 1

    if maze_display is not None: # need to delete previous maze
        glDeleteLists(maze_display, 1)

    entities = [player]
    maze, lights, maze_display = make_maze(2 + floor(level/2), 2 + ceil(level/2))
    send_lists(maze, entities)

    # reset doors
    doors = [[Vector3(1, 0, 1), -1], [Vector3(len(maze[0])-1, 0, len(maze)-2), -1]]

def lift(first=False):
    global lights, door_trigger
    lights_old = lights[:] # backup them to reuse

    # generate a lift
    lift = glGenLists(1)
    glNewList(lift, GL_COMPILE)

    if first:
        delay, floors = 6300, 5 # follow the music
    else:
        delay, floors = 3000, 3

    for y in range(floors):
        for x in [0, 1]:
            if (y, x) in [(floors-1, 0), (0, 1)]:
                tex = textures['gate']
            else:
                tex = textures['lifthidden']
            glBindTexture(GL_TEXTURE_2D, tex)
            glBegin(GL_QUADS)
            glNormal3f(1 - x*2, 0, 0)
            glTexCoord2f(0, 0)
            glVertex3f(x, y, 1-x)
            glTexCoord2f(1, 0)
            glVertex3f(x, y, x)
            glTexCoord2f(1, 1)
            glVertex3f(x, y+1, x)
            glTexCoord2f(0, 1)
            glVertex3f(x, y+1, 1-x)
            glEnd()

    glEndList()

    # info for the moving parts of the lift: bottom, top, left, right
    normals = [(0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    pos = [[(0, 0), (0, 1)], [(1, 0), (1, 1)], [(0, 0), (1, 0)], [(0, 1), (1, 1)]]

    # genereate text
    sizes = [textures['level'][1], textures['0'][1]]
    w = sizes[0][0] + 10 + sizes[1][0]*len(str(level))
    x = (W-w) // 2
    text = [(textures['level'][0], x, sizes[0])]
    x += sizes[0][0]+10
    for char in str(level):
        text.append((textures[char][0], x, sizes[1]))
        x += sizes[1][0]

    player.pos = Vector3(player.pos.x%1, floors, player.pos.z%1)
    w, h = player.size
    time_passed = 0
    running = True
    start = ticks()+2000

    while running:
        if ticks() < start:
            state = 0 # waiting to descend
            alpha = 1 - (start-ticks())/1000
        elif ticks()-start < delay:
            if state == 0:
                lifton.play()
                if first:
                    # if first level, start the music
                    pygame.mixer.music.play(-1)
                    start = ticks() # prevent lag when playing music
            state = 1 # descending
            alpha = min(start+delay-ticks(), 1000)/1000
        else:
            if state == 1:
                liftoff.play()
            state = 2 # waiting to open the door
            alpha = 0

        events = pygame.event.get()
        for event in events:
            if event.type == QUIT:
                pygame.quit()
                quit()
            elif event.type == MOUSEBUTTONDOWN and event.button == 3 and state == 2:
                running = False

        player.update(events, time_passed, False)

        # the player must stay in this cell
        player.pos.x = min(max(player.pos.x, w/2), 1 - w/2)
        player.pos.z = min(max(player.pos.z, w/2), 1 - w/2)
        if state == 0:
            player.cam.y = floors-1+h
        elif state == 1:
            progress = (ticks()-start) / delay
            player.cam.y = (floors-1) * (1 + cos(pi * progress))**2 / 4 + h
        else:
            player.cam.y = h
        lights = [Vector3(0.5, player.cam.y-h+0.7, 0.5)]

        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

        glPushMatrix()
        init3d()

        # draw the static lift walls
        glCallList(lift)

        # draw the moving lift walls
        y = player.cam.y-h
        for face, tex in [(0, 'liftfloor'), (1, 'liftceil'), (2, 'liftwall'), (3, 'liftwall')]:
            y0, z0 = pos[face][0]
            y1, z1 = pos[face][1]
            glBindTexture(GL_TEXTURE_2D, textures[tex])
            glBegin(GL_QUADS)
            glNormal3dv(normals[face])
            glTexCoord2f(0, 0)
            glVertex(face == 3, y+y0, z0)
            glTexCoord2f(1, 0)
            glVertex(face !=3, y+y0, z0)
            glTexCoord2f(1, 1)
            glVertex(face != 3, y+y1, z1)
            glTexCoord2f(0, 1)
            glVertex(face == 3, y+y1, z1)
            glEnd()

        glPopMatrix()
        glPushMatrix()
        init2d()
        render2d()

        y = H/2 - 100
        glColor4f(1, 1, 1, alpha) # text fade in/out
        for tex, x, size in text:
            glBindTexture(GL_TEXTURE_2D, tex)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 1)
            glVertex2f(x, y)
            glTexCoord2f(1, 1)
            glVertex2f(x+size[0], y)
            glTexCoord2f(1, 0)
            glVertex2f(x+size[0], y + size[1])
            glTexCoord2f(0, 0)
            glVertex2f(x, y + size[1])
            glEnd()
        glColor(base_color)

        glPopMatrix()

        time_passed = clock.tick(FPS) / 1000
        pygame.display.flip()

    # prepare for the game
    player.pos = Vector3(player.pos.x, 0, player.pos.z+1)
    lights = lights_old

    # open the door
    door_trigger = [0, ticks()]
    door.play()

def render3d():
    # draw maze
    glCallList(maze_display)

    # draw doors
    for pos, normx in doors:
        if pos.y == 1:
            continue

        z0, z1 = pos.z + (normx == 1), pos.z + (normx == -1)
        glBindTexture(GL_TEXTURE_2D, textures['gate'])
        glBegin(GL_QUADS)
        glNormal3f(normx, 0, 0)
        glTexCoord2f(0, 0)
        glVertex(pos.x, pos.y, z0)
        glTexCoord2f(1, 0)
        glVertex(pos.x, pos.y, z1)
        glTexCoord2f(1, 1)
        glVertex(pos.x, pos.y+1, z1)
        glTexCoord2f(0, 1)
        glVertex(pos.x, pos.y+1, z0)
        glEnd()

    # draw entities last (avoid transparency issues)
    for entity in entities:
        entity.render()
    for particle in particles:
        particle.render()

def render2d():
    # render HUD
    glBindTexture(GL_TEXTURE_2D, hud)
    glBegin(GL_QUADS)

    glTexCoord2f(0, 1)
    glVertex2f(0, 0)
    glTexCoord2f(1, 1)
    glVertex2f(W, 0)
    glTexCoord2f(1, 0)
    glVertex2f(W, H)
    glTexCoord2f(0, 0)
    glVertex2f(0, H)

    glEnd()

    # render HP bar
    hp = 500*player.hp/player.max_hp
    glBindTexture(GL_TEXTURE_2D, textures['white'])
    glBegin(GL_QUADS)

    glColor(0.3, 0.3, 0.3)
    glTexCoord2f(0, 1)
    glVertex2f(15, 7)
    glTexCoord2f(1, 1)
    glVertex2f(525, 7)
    glTexCoord2f(1, 0)
    glVertex2f(515, 33)
    glTexCoord2f(0, 0)
    glVertex2f(5, 33)

    glColor(1, 0, 0.2)
    glTexCoord2f(0, 1)
    glVertex2f(18, 10)
    glTexCoord2f(1, 1)
    glVertex2f(18+hp, 10)
    glTexCoord2f(1, 0)
    glVertex2f(10+hp, 30)
    glTexCoord2f(0, 0)
    glVertex2f(10, 30)

    if player.dying: # show black fadeout
        glColor(0.1, 0, 0, (ticks()-player.dying)/1000)
        glTexCoord2f(0, 1)
        glVertex2f(0, H)
        glTexCoord2f(1, 1)
        glVertex2f(W, H)
        glTexCoord2f(1, 1)
        glVertex2f(W, 0)
        glTexCoord2f(0, 1)
        glVertex2f(0, 0)

    glEnd()

    # show low health overlay
    alpha = max(0.5 - player.hp/player.max_hp, 0)*2
    if alpha:
        glBindTexture(GL_TEXTURE_2D, textures['overlay'])
        glColor(1, 1, 1, alpha)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1)
        glVertex(0, 0)
        glTexCoord2f(1, 1)
        glVertex(W, 0)
        glTexCoord2f(1, 0)
        glVertex(W, H)
        glTexCoord2f(0, 0)
        glVertex(0, H)
        glEnd()

    glColor(base_color)


load_options()
FOV, render_distance, fullscreen = options['fov'], options['render_distance'], options['fullscreen']
if options['discord'] == True:
    try:
        from pypresence import Presence
        from time import time
        RPC = Presence('1077969171591217162')
        RPC.connect()
        RPC.update(state='In game', start=time(), instance=True, large_image='large_image')
    except: # module not installed or Discord not found
        options['discord'] = False
        save_options()

pygame.init()
if fullscreen:
    info = pygame.display.Info()
    W, H = info.current_w, info.current_h
    screen = pygame.display.set_mode((W, H), HWSURFACE|OPENGL|DOUBLEBUF|FULLSCREEN)
else:
    W, H = 900, 500
    screen = pygame.display.set_mode((W, H), HWSURFACE|OPENGL|DOUBLEBUF)
pygame.display.set_caption('Maze')
pygame.display.set_icon(pygame.image.load('files/textures/icon.png'))
pygame.event.set_grab(1) # lock all events to this window
pygame.mouse.set_visible(0)
clock = pygame.time.Clock()
ticks = pygame.time.get_ticks

# music
pygame.mixer.music.load('files/sfx/music.mp3')
pygame.mixer.music.set_volume(0.5)
lifton, liftoff, door, bullet = [pygame.mixer.Sound('files/sfx/%s.wav' %name) for name in ['lifton', 'liftoff', 'door', 'bullet']]

door_trigger = None # used for door animations
doors = None # start and exit doors: [pos, normal x]
time_passed = 0
FPS = 120
level = 0
maze_display = None
base_color = (1, 1, 1)
initOpenGl()

walls_names = ['bricks', 'slimybricks', 'ironplates', 'concrete']
monsters_names = [('SoldierGun', 'POSS'), ('SoldierShotgun', 'SPOS')]
init_tex() # generate all textures
hud_surf = pygame.Surface((W, H), SRCALPHA)
crosshair = pygame.image.load('files/textures/crosshair.png')
w, h = crosshair.get_size()
hud_surf.blit(crosshair, ((W-w) // 2, (H-h) // 2))
update_hud(True)

send_tex(textures)

particles = []
player = Player()
entities = [player]

new_level()
send_vars(W, H, ticks, player, particles, bullet, options)
lift(True)

while True:
    events = pygame.event.get()
    for event in events:
        if event.type == QUIT:
            pygame.quit()
            quit()
        elif event.type == MOUSEBUTTONDOWN:
            pygame.event.set_grab(1) # refresh mouse grab
        elif event.type == USEREVENT: # exit door opened
            door_trigger = [1, ticks()]
            door.play()

            maze[-2][-1] = 0 # allow the player to walk into the exit

    for entity in entities:
        if entity == player:
            player.update(events, time_passed)
        elif entity.pos.distance_to(player.pos) <= 14: # simulation distance
            entity.update(time_passed)
    for particle in particles:
        particle.update(time_passed)

    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

    # render 3d elements
    glPushMatrix()
    init3d()
    render3d()
    glPopMatrix()

    # render 2d elements
    glPushMatrix()
    init2d()
    render2d()
    glPopMatrix()

    if door_trigger:
        index, when = door_trigger
        progress = (ticks()-when)/400

        if progress > 1: # the door is fully opened
            if index == 0: # entrance door opened
                door_trigger = None
                doors[0][0].y = 1
                maze[1][1] = 0 # allow to go in the maze

            elif index == 1: # exit door opened
                doors[1][0].y = 1
                if player.pos.x - player.size[0]/2 > len(maze[0])-1: # if player is in the lift
                    # close the exit door
                    door_trigger = [2, ticks()]
                    door.play()

                    doors[1][1] = 1 # the door will face the player
                    maze[-2][-2] = 1 # prevent the player from going back in the maze

            elif index == 2: # exit door closed
                new_level()
                lift()

        else: # door animation
            if index == 0: # start door opening
                doors[0][0].y = progress
            elif index == 1: # exit door opening
                doors[1][0].y = progress
            elif index == 2: # exit door closing
                doors[1][0].y = 1-progress

    time_passed = clock.tick(FPS) / 1000
    pygame.display.flip()
