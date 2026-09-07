import pygame

from pygame.math import Vector2, Vector3

from math import *
from random import *
from OpenGL.GL import *
from OpenGL.GLU import *
from pygame.locals import *
from a_star import a_star

def send_tex(tex): # at the very start
    global textures
    textures = tex

def send_vars(*args): # at the start
    global W, H, ticks, player, particles, bullet, move_keys, fov
    W, H, ticks, player, particles, bullet, options = args
    fov = options['fov']
    move_keys = [ord(char.lower()) for char in options['move_keys']]

def send_lists(*args): # when changing level
    global maze, entities
    maze, entities = args

class FloatRect:
    # pygame Rect doesn't support float coordinates

    def __init__(self, x, y, w, h):
        self.x = self.left = x
        self.y = self.top = y
        self.w, self.h = w, h
        self.right, self.bottom = x+w, y+h

    def colliderect(self, rect):
        return self.right > rect.left and self.left < rect.right and \
               self.top < rect.bottom and self.bottom > rect.top

class Entity:
    def __init__(self):
        self.movement = Vector3()
        self.hitbox = FloatRect(0, 0, 0, 0)

        self.weapon_delay = 800
        self.last_shot = 0
        self.damage = 30 # dealt by bullets
        self.hit = 0

    def get_camera(self):
        return self.pos, self.rot

    def collide(self, *ignore):
        # also set up the hitbox: center at the bottom
        w, h = self.size
        self.hitbox = FloatRect(self.pos.x - w/2, self.pos.z - w/2, w, w)
        m, n = len(maze[0]), len(maze)

        touch = [] # find out which blocks are touched
        X, Z = floor(self.hitbox.left), floor(self.hitbox.top)
        for x in range(X, X+2):
            for z in range(Z, Z+2):
                if 0 <= x < m and 0 <= z < n and maze[z][x] > 0:
                    touch.append(FloatRect(x, z, 1, 1))

        # check if out of bounds
        out_bounds = False
        if self.pos.x < w/2 or self.pos.x > m - w/2:
            out_bounds = True
            self.pos.x = min(max(self.pos.x, w/2), m - w/2)

        if self.pos.y < 0 or self.pos.y > 1-h:
            out_bounds = True
            self.pos.y = min(max(self.pos.y, 0), 1-h)

        # also check if hit (other) entity
        hit_entity = None

        touch_ = [] # used to do the collisions in a specific order
        for current in touch+entities:
            if current in entities:
                if current == self or current in ignore or type(current) in [Particle, Bullet]:
                    continue
                hit = current.hitbox
            else:
                hit = current

            if self.hitbox.colliderect(hit):
                if self.movement.x < 0: # right side
                    dx = self.hitbox.left-hit.right
                else: # left side
                    dx = self.hitbox.right-hit.left
                if self.movement.z < 0: # front side
                    dz = self.hitbox.top-hit.bottom
                else:
                    dz = self.hitbox.bottom-hit.top

                if current in entities: # entity has been hit
                    hit_entity = current
                else: # wall: collide
                    touch_.append((dx, dz))

        for dx, dz in sorted(touch_, key=lambda block: max(map(abs, block)), reverse=True):
            if abs(dx) > abs(dz):
                self.pos.z -= dz
                self.movement.z = 0
            else:
                self.pos.x -= dx
                self.movement.x = 0

        # return code: 0 = none, 1 = wall, obj = entity
        return (hit_entity is not None and hit_entity) or bool(len(touch_)) or out_bounds

    def update(self, *args):
        pass

    def render(self):
        pass

class Player(Entity):
    def __init__(self):
        super().__init__()
        self.pos = Vector3(0.5, 0, 1.5)
        self.rot = Vector3(0, -pi/2, 0) # radians
        self.base_height = 0.6
        self.size = [0.4, self.base_height]

        # camera following self.pos + alterations done to it
        self.cam = Vector3(self.pos)
        self.cam_rot = Vector3(self.rot)
        self.pos_offset = Vector3()
        self.rot_offset = Vector3()

        self.sensi = 1
        self.sprint = False

        self.hp = self.max_hp = 100
        self.last_hit = 0 # time of last hit taken
        self.dying = 0 # time of death start
        self.died = False

        self.sounds = {name: pygame.mixer.Sound('files/sfx/%s.wav' %name) for name in ['hit', 'death']}
        self.sounds['shot'] = pygame.mixer.Sound('files/sfx/shotgun.wav')
        for s in self.sounds.values():
            s.set_volume(0.08)
        self.channels = [pygame.mixer.Channel(x) for x in (0, 1)] # weapon, body
        for c in self.channels:
            c.set_volume(0.08)

    def move(self, events, time_passed):
        # rotation
        for event in events:
            if event.type == MOUSEMOTION:
                # pan camera
                x, y = event.rel
                self.rot.x -= y/H*2*pi*self.sensi*0.7
                self.rot.y -= x/W*2*pi*self.sensi
                self.rot.x = min(radians(90), max(radians(-90), self.rot.x))
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1 and ticks()-self.last_shot > self.weapon_delay:
                    # send a bullet
                    particles.append(Bullet(self, self.size[1]))

                    # recall
                    self.channels[0].play(self.sounds['shot'])
                    self.rot_offset.x = pi/20

                    self.last_shot = ticks()
                elif event.button == 3 and (floor(self.pos.x), floor(self.pos.z)) == (len(maze[0])-2, len(maze)-2):
                    pygame.event.post(pygame.event.Event(USEREVENT)) # tell that the exit door has been opened

        # movement
        movement = Vector3() # this frame
        pressed = pygame.key.get_pressed()
        if pressed[K_LCTRL]: # sprint
            self.sprint = True

        if pressed[move_keys[0]]: # forwards (walks faster)
            movement.z -= 1
        else: # reset sprint
            self.sprint = False
        if pressed[move_keys[1]]: # left
            movement.x -= 0.8
        if pressed[move_keys[2]]: # backwards
            movement.z += 0.8
        if pressed[move_keys[3]]: # right
            movement.x += 0.8

        if pressed[K_LSHIFT]: # sneak
            movement *= 0.5
            self.pos_offset = Vector3(0, -0.1, 0)
        else:
            self.pos_offset *= 0.8**(100*time_passed)

        return movement

    def update(self, events, time_passed, check_collide=True):
        global hud_surf

        if self.dying:
            progress = (ticks()-self.dying)/2000

            if progress >= 1:
                # killed: end of animation
                self.pos = Vector3(0.5, 0, 1.5)
                self.hp = self.max_hp
                self.size[1] = self.base_height
                self.rot_offset = Vector3()
                self.dying = 0
                return

            # make the progress more interesting
            progress = sin(pi*progress/2) + sin(8*pi*progress)/20

            self.rot_offset.x = (-pi/2 - self.rot.x) * progress
            self.size[1] = self.base_height * (1-progress)
            movement = Vector3()
        else: # only allow to pan / move when alive
            movement = self.move(events, time_passed)

        # add rotated movement to self.pos
        self.movement += movement.rotate(self.rot.y*180/pi, Vector3(0, 1, 0)) * 40 * time_passed
        self.pos += self.movement * time_passed * (1 + 0.3*self.sprint)
        if check_collide:
            self.collide()

        # slowly cancel movements
        self.movement *= 0.85**(100*time_passed)
        self.rot_offset *= 0.9**(100*time_passed)

        # regen
        self.hp = min(self.hp + time_passed * (0.1 + (ticks()-self.last_hit) / 7000), self.max_hp)

        self.cam = (self.pos+self.pos_offset)+Vector3(0, self.size[1], 0)
        self.cam_rot = self.rot+self.rot_offset

        # damage
        if self.hit and not self.dying:
            self.hp -= self.hit
            self.hit = 0
            self.last_hit = ticks()

            if self.hp <= 0:
                self.hp = 0
                self.dying = ticks()
                self.channels[1].play(self.sounds['death'])
            else:
                self.channels[1].play(self.sounds['hit'])

class Monster(Entity):
    def __init__(self, pos, name, hp):
        super().__init__()
        self.pos = pos
        self.rot = Vector3(0, 0, 0)

        self.textures = textures[name]
        self.size = (0.4, 0.6)

        self.hp = hp
        self.speed = 1.5

        self.sounds = {name: pygame.mixer.Sound('files/sfx/monsters/%s.wav' %name) for name in ['notice', 'death']}
        self.sounds['shot'] = pygame.mixer.Sound('files/sfx/pistol.wav')
        for s in self.sounds.values():
            s.set_volume(0.08)
        self.channels = [pygame.mixer.Channel(x) for x in (2, 3)] # all monsters share the same
        for c in self.channels:
            c.set_volume(0.08)

        self.reaction = 700
        self.track_dist = 14
        self.shoot_dist = 4  #para ele não atirar de tão longe
        self.start_see = 0 # when
        self.last_see = None # where (vector)
        self.walk_goal = None # where to wander around: either None or [pos, when]

        # A* pathfinding
        self.path = []
        self.last_path_calc = 0
        self.path_calc_interval = 300

        self.texupdate = 0 # when to update the texture
        self.walk = 0 # walk animation index
        self.type_ = 0 # 0 = walking, 1->3 = shooting, 4 = damage, 5+ = death

    def accessible(self, pos):
        # break down the movement into steps and see if they fall in a block
        m, n = len(maze[0]), len(maze)
        start = Vector2(self.pos.x, self.pos.z)
        move = Vector2(pos.x, pos.z)-start
        dist = move.length()

        if dist > self.track_dist:
            return False

        steps = max(int(dist * 5), 15)
        margin = 0.2 # margem para evitar mirar ou atirar atraves de quinas
        for i in range(1, steps):
            p = start + move*i/steps
            x, y = floor(p.x), floor(p.y)
            if 0 <= x < m and 0 <= y < n and maze[y][x] > 0:
                return False

            dist_from_start = dist * (i / steps)
            dist_to_target = dist - dist_from_start
            if dist_from_start > 0.3 and dist_to_target > 0.3:
                for dx, dy in ((-margin, 0), (margin, 0), (0, -margin), (0, margin)):
                    nx, ny = floor(p.x + dx), floor(p.y + dy)
                    if 0 <= nx < m and 0 <= ny < n and maze[ny][nx] > 0:
                        return False
        return True

    def aim_at(self, pos):
        start = Vector2(self.pos.x, self.pos.z)
        goal = Vector2(pos.x, pos.z)
        self.rot.y = -pi/2 - radians(Vector2().angle_to(goal-start))

    def update(self, time_passed):
        if self.hit:
            self.hp -= self.hit
            self.hit = 0
            self.type_ = 4
            self.texupdate = ticks()+250

            if self.last_see is None: # track player if shot in the back
                self.last_see = Vector3(player.pos)

            if self.hp <= 0: # killed
                self.type_ = 5
                self.texupdate = ticks()+50

        if ticks() >= self.texupdate: # update current texture
            if self.type_ == 1: # shoot
                self.type_ = 2
                self.texupdate = ticks()+100

                particles.append(Bullet(self, self.size[1]*0.65))
                self.channels[0].play(self.sounds['shot'])
                self.last_shot = ticks()

            elif self.type_ == 2: # after shooting
                self.type_ = 3
                self.texupdate = ticks()+100

            elif self.type_ >= 5: # dying
                if self.type_ == 5:
                    self.channels[1].stop()
                    self.channels[1].play(self.sounds['death'])
                if self.type_ == 13:
                    entities.remove(self)
                else:
                    self.type_ += 1
                self.texupdate = ticks()+50
                return # don't do anything when dying

            else: # walk
                if self.movement.length():
                    self.walk = (self.walk+1) % 4 # walk animation
                else:
                    self.walk = 1 # still
                self.type_ = 0
                self.texupdate = ticks()+250

        self.movement = Vector3()

        dist_to_player = self.pos.distance_to(player.pos)
        has_line_of_sight = self.accessible(player.pos) and not player.dying

        # Perde o rastro se o jogador morrer ou se afastar demais
        if player.dying or dist_to_player > self.track_dist:
            if self.last_see is not None:
                self.last_see = None
                self.path = []

        if has_line_of_sight:
            if self.last_see is None: # not aggroed: needs to be in FOV range or close sound
                see_angle = atan2(self.pos.z-player.pos.z, player.pos.x-self.pos.x)
                in_fov = abs(see_angle - self.rot.y - pi/2) <= pi/3 or dist_to_player <= 2.5

                if in_fov: # just got aggroed
                    self.last_see = Vector3(player.pos)
                    self.channels[1].play(self.sounds['notice'])
            else: # don't need to check for FOV range once aggroed
                in_fov = True

            if in_fov and self.type_ == 0 and ticks()-self.start_see >= self.reaction:
                # aim at the player
                self.aim_at(player.pos)

                if dist_to_player > self.shoot_dist:
                    move_dir = player.pos - self.pos
                    move_dir.y = 0
                    if move_dir.length() > 0:
                        self.movement = move_dir.normalize()
                elif ticks()-self.last_shot >= self.weapon_delay:
                    # Dentro do alcance de tiro e pronto para disparar
                    self.type_ = 1
                    self.texupdate = ticks()+250
                elif dist_to_player > 1.2:
                    # Enquanto a arma recarrega, continua se aproximando
                    move_dir = player.pos - self.pos
                    move_dir.y = 0
                    if move_dir.length() > 0:
                        self.movement = move_dir.normalize()

                self.last_see = Vector3(player.pos)
                self.walk_goal = None
                self.path = []
        else:
            self.start_see = ticks()

            if self.last_see is not None and not player.dying and dist_to_player <= self.track_dist:
                # Persegue o jogador pelo labirinto usando A*
                now = ticks()
                if now - self.last_path_calc >= self.path_calc_interval:
                    self.last_path_calc = now
                    start_node = (floor(self.pos.x), floor(self.pos.z))
                    goal_node = (floor(player.pos.x), floor(player.pos.z))
                    calc_path = a_star(maze, start_node, goal_node)
                    if len(calc_path) > 1 and calc_path[0] == start_node:
                        self.path = calc_path[1:]
                    else:
                        self.path = calc_path

                if self.path:
                    target_node = self.path[0]
                    target_pos = Vector3(target_node[0] + 0.5, 0, target_node[1] + 0.5)

                    dx = self.pos.x - target_pos.x
                    dz = self.pos.z - target_pos.z
                    if dx*dx + dz*dz < 0.09: # chegou perto do centro da celula
                        self.path.pop(0)
                        if self.path:
                            target_node = self.path[0]
                            target_pos = Vector3(target_node[0] + 0.5, 0, target_node[1] + 0.5)

                    direction = target_pos - self.pos
                    direction.y = 0
                    if direction.length() > 0:
                        self.movement = direction.normalize()
                        self.aim_at(target_pos)
                else:
                    if self.pos.distance_to(self.last_see) < 0.3:
                        self.last_see = None
                    else:
                        self.movement = (self.last_see-self.pos).normalize()
                        self.movement.y = 0
                        self.aim_at(self.last_see)

            elif self.last_see is None: # wander around
                self.path = []
                if self.walk_goal is None: # set a new goal
                    m, n = len(maze[0]), len(maze)
                    ok = [] # where it could go
                    X, Z = floor(self.pos.x), floor(self.pos.z)

                    for x in range(X-2, X+3):
                        for z in range(Z-2, Z+3):
                            if (x, z) == (X, Z):
                                continue
                            if 0 <= x < m and 0 <= z < n: # stay in the maze
                                pos = Vector3(x+0.5, 0, z+0.5)
                                if maze[z][x] <= 0 and self.accessible(pos): # if air and accessible
                                    ok.append(pos)

                    if len(ok):
                        self.walk_goal = [choice(ok), ticks()+randint(0, 2000)]

                elif ticks() >= self.walk_goal[1]: # walk towards goal
                    if self.pos.distance_to(self.walk_goal[0]) < 0.2: # reached spot
                        self.walk_goal = None
                    else:
                        self.movement = (self.walk_goal[0]-self.pos).normalize()
                        self.movement.y = 0
                        self.aim_at(self.walk_goal[0])
            else:
                self.last_see = None
                self.path = []

        self.pos += self.movement*time_passed*self.speed
        collide = self.collide()
        if type(collide) != bool and collide != player: # entity is blocking it
            self.path = [] # recalcula rota ao bater em outra entidade

    def render(self):
        # get the "side" of the entity that is seen by the camera
        # offset to make it show the front when aiming slightly on both sides
        angle = (player.rot.y - self.rot.y + pi + pi/8) % (2*pi)
        angle = angle*8 // (2*pi)

        # get the angle at which the texture must be drawn to face the camera
        v = Vector3(cos(player.rot.y), 0, -sin(player.rot.y))
        top = Vector3(0, self.size[1], 0)

        if self.type_ == 0:
            texture, size = self.textures['walk%d%d' %(self.walk, angle)]
        elif self.type_ >= 5:
            texture, size = self.textures['die%d' %(self.type_-5)]
        else:
            texture, size = self.textures[['aim%d', 'shoot%d', 'aim%d', 'dmg%d'][self.type_-1] %(angle)]

        glBindTexture(GL_TEXTURE_2D, texture)
        glBegin(GL_QUADS)
        glNormal3f(-v.z, 0, v.x) # normal rotated 90°
        v *= self.size[1]*size[0]/size[1]/2
        glTexCoord2f(0, 0)
        glVertex(self.pos-v)
        glTexCoord2f(1, 0)
        glVertex(self.pos+v)
        glTexCoord2f(1, 1)
        glVertex(self.pos+v+top)
        glTexCoord2f(0, 1)
        glVertex(self.pos-v+top)
        glEnd()

class Particle(Entity):
    def __init__(self, *args):
        super().__init__()
        self.timer = None # once non-None, will despawn after some time
        self.ttl = 1000

        # normal particle: specifies position (calling from other classes will have no arguments passed
        if len(args):
            self.size = (0.01, 0.02)
            self.color = args[1]
            speed = args[2]

            self.pos = Vector3(args[0])
            self.movement = Vector3(randint(-100, 100)/50*speed,
                                    randint(0, 100*speed)/100,
                                    randint(-100, 100)/50*speed)
            self.dy = randint(10, 30) # fall at random speed

    def update(self, time_passed):
        self.movement *= 0.9**(100*time_passed)
        self.movement.y -= self.dy*time_passed
        self.pos += self.movement*time_passed

        if self.collide(*entities) == 1 and self.timer is None:
            self.timer = ticks()+self.ttl

        if self.timer is not None and ticks() >= self.timer:
            particles.remove(self)

    def render(self):
        size = self.size[0]

        normals = [(0, 0, -1), (1, 0, 0), (0, 0, 1), (-1, 0, 0)]
        offset = [[(-1, -1), (1, -1)], [(1, -1), (1, 1)], [(1, 1), (-1, 1)], [(-1, 1), (-1, -1)]]
        x, y, z = self.pos

        glBindTexture(GL_TEXTURE_2D, textures['white'])
        glColor3dv(self.color)
        # sides
        for face in range(4):
            glBegin(GL_QUADS)
            glNormal3dv(normals[face])
            a, b = offset[face]
            glVertex(x + size*a[0], y-size, z + size*a[1])
            glVertex(x + size*b[0], y-size, z + size*b[1])
            glVertex(x + size*b[0], y+size, z + size*b[1])
            glVertex(x + size*a[0], y+size, z + size*a[1])
            glEnd()
        # top and bottom
        for face in [-1, 1]:
            glBegin(GL_QUADS)
            glNormal3f(0, face, 0)
            glVertex(x - size, y - size*face, z - size)
            glVertex(x + size, y - size*face, z - size)
            glVertex(x + size, y - size*face, z + size)
            glVertex(x - size, y - size*face, z + size)
            glEnd()
        glColor3f(1, 1, 1)

class Bullet(Particle):
    def __init__(self, master, y):
        super().__init__()
        self.master = master # the bullet shooter
        self.pos = Vector3(master.pos)
        self.pos.y += y
        self.size = (0.02, 0.02)
        self.speed = 20
        self.color = (0.6, 0.3, 0.1)
        self.ttl = 5000

        self.power = master.damage

        x, y, z = master.rot
        self.movement = Vector3(-sin(y)*cos(x), sin(x), -cos(y)*cos(x))

    def update(self, time_passed):
        self.pos += self.movement*time_passed*self.speed
        collide = self.collide(self.master)
        if collide and self.timer is None:
            self.movement = Vector3()
            self.timer = ticks()+self.ttl

            if type(collide) != bool:
                collide.hit = self.power
                color = (1, 0, 0)

                # delete bullet to avoid it staying in the air
                particles.remove(self)
            else:
                color = (0.3, 0.3, 0.3)
                bullet.play()

            for x in range(10):
                particles.append(Particle(self.pos, color, 1))

        if self.timer is not None and ticks() >= self.timer:
            # despawn
            particles.remove(self)
