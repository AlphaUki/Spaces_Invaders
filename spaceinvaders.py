from os.path import abspath, dirname
from PIL import Image, ImageDraw, ImageFont, ImageTk
from random import randrange, sample
from time import time
from threading import Thread
from tkinter import BooleanVar, Canvas, Frame, Tk
from typing import List, Tuple

try:
    # playsound version 1.2.2 -> pip install playsound==1.2.2
    import playsound as _ps

    def playsound(sound: str) -> None:
        def tryplay():
            try: _ps.playsound(sound)
            except: print("Try an older version of playsound (ex: 1.2.2)")
        Thread(target=tryplay).start()
except:
    def playsound(sound: str) -> None: pass

################################################################
#                           Configs                            #
################################################################

IMAGE_SCALE = 5
SPEED_SCALE = 1

BASE_PATH = abspath(dirname(__file__))
IMAGE_PATH = BASE_PATH + '/images/'
FONT_PATH = BASE_PATH + '/fonts/'
SOUND_PATH = BASE_PATH + '/sounds/'

################################################################
#                            Utils                             #
################################################################

def bbox_x_diff_to_center(bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> int:
    return bbox2[0] - bbox1[0] + ((bbox2[2] - bbox2[0]) - (bbox1[2] - bbox1[0])) // 2

def bbox_y_diff_to_center(bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> int:
    return bbox2[1] - bbox1[1] + ((bbox2[3] - bbox2[1]) - (bbox1[3] - bbox1[1])) // 2

def bbox_diff_to_center(bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> Tuple[int, int]:
    return bbox_x_diff_to_center(bbox1, bbox2), bbox_y_diff_to_center(bbox1, bbox2)

def get_photoimage(image: Image.Image) -> ImageTk.PhotoImage:
    return ImageTk.PhotoImage(image)

def get_photoimages(images: List[Image.Image]) -> List[ImageTk.PhotoImage]:
    return [ImageTk.PhotoImage(img) for img in images]

################################################################
#                     Ressources - Images                      #
################################################################

def load_image(file: str) -> Image.Image:
    image = Image.open(IMAGE_PATH + file)
    return image.resize((int(image.width * IMAGE_SCALE), int(image.height * IMAGE_SCALE)), resample=Image.NEAREST)
    
def load_images(file_format: str, nb: int) -> List[Image.Image]:
    return [load_image(file_format % i) for i in range(1, nb + 1)]

class Images:
    obstacle = load_image("obstacle.png")
    defender = load_image("defender.png")
    defender_explosion = load_images("defender_explosion_%d.png", 2)
    bullet = load_image("bullet.png")
    bullet_explosion = load_image("bullet_explosion.png")
    alien_squid = load_images("alien_squid_%d.png", 2)
    alien_crab = load_images("alien_crab_%d.png", 2)
    alien_octopus = load_images("alien_octopus_%d.png", 2)
    alien_explosion = load_image("alien_explosion.png")
    bomb_1 = load_images("bomb_1_%d.png", 4)
    bomb_2 = load_images("bomb_2_%d.png", 4)
    bomb_3 = load_images("bomb_3_%d.png", 4)
    bomb_explosion = load_image("bomb_explosion.png")
    alien_ufo = load_image("alien_ufo.png")
    alien_ufo_explosion = load_image("alien_ufo_explosion.png")

################################################################
#                      Ressources - Font                       #
################################################################

class Font:
    size = int(6 * IMAGE_SCALE)
    _font = ImageFont.truetype(FONT_PATH + "space_invaders.ttf", size)

    # Converts the required chars into images
    _chars_as_imgs = {}
    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789=*?-":
        _img = Image.new('RGBA', (size, size), '#00000000')
        ImageDraw.Draw(_img).text(((size - _font.getlength(char)) / 2, 0), char, "#FFFFFF", _font)
        _chars_as_imgs[char] = _img

    @staticmethod
    def text_as_image(text: str, color: str = None) -> Image.Image:
        text = "?" if not text else str.upper(text)
        img = Image.new('RGBA', (Font.size * len(text), Font.size), '#00000000')

        for char_index, char in enumerate(text):
            if not str.isspace(char):
                if char not in Font._chars_as_imgs:
                    char = '?'
                img.paste(Font._chars_as_imgs[char], (Font.size * char_index, 0))
        
        if color: # format unchecked !
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            a = int(color[7:9], 16) if len(color) == 9 else 255

            img_rgba = img.split()
            img = Image.merge('RGBA', (
                img_rgba[0].point(lambda p: 0 if p == 0 else r),
                img_rgba[1].point(lambda p: 0 if p == 0 else g),
                img_rgba[2].point(lambda p: 0 if p == 0 else b),
                img_rgba[3].point(lambda p: 0 if p == 0 else a)
            ))

        return img

################################################################
#                     Ressources - Sounds                      #
################################################################

def load_sound(file: str) -> str:
    return SOUND_PATH + file

def load_sounds(file_format: str, nb: int) -> List[str]:
    return [load_sound(file_format % i) for i in range(1, nb + 1)]

class Sounds:
    defender_killed = load_sound("defender_killed.wav")
    defender_shoot = load_sound("defender_shoot.wav")
    alien_move = load_sounds("alien_move_%d.wav", 4)
    alien_killed = load_sound("alien_killed.wav")
    alien_ufo_move = load_sound("alien_ufo_move.wav")
    alien_ufo_killed = load_sound("alien_ufo_killed.wav")

################################################################
#                             Core                             #
################################################################

class Defender:
    def __init__(self, canvas: Canvas) -> None:
        self.canvas = canvas
        self.image = get_photoimage(Images.defender)
        self.images_explosion = get_photoimages(Images.defender_explosion)
        self.delta_x = 20 * SPEED_SCALE
        self.lives = 3
        self.score = 0
        self.alive = True
        self.explodes = False
        self.bullet = None
        self.id = self._create_id()

    def _create_id(self) -> int:
        return self.canvas.create_image(self.canvas.winfo_reqwidth() / 2, self.canvas.winfo_reqheight() - self.image.height() / 2, image=self.image)

    def isAlive(self) -> None:
        return self.alive and not self.explodes

    def kill(self) -> None:
        if self.alive:
            self.alive = False
            self.lives = 0
            self.canvas.delete(self.id)

    def explode(self) -> None:
        if self.isAlive():
            self.explodes = True
            playsound(Sounds.defender_killed)
            self.lives -= 1
            animating = BooleanVar(self.canvas, True)
            time = 0
            for _ in range(5):
                self.canvas.after(time, lambda: self.canvas.itemconfigure(self.id, image=self.images_explosion[0]))
                time += 120
                self.canvas.after(time, lambda: self.canvas.itemconfigure(self.id, image=self.images_explosion[1]))
                time += 120
            self.canvas.after(time - 60, lambda: animating.set(False))
            self.canvas.wait_variable(animating)
            if self.lives > 0:
                self.canvas.itemconfigure(self.id, image=self.image)
                self.explodes = False
            else:
                self.kill()

    def move(self, dx: float) -> None:
        if self.isAlive():
            bbox = self.canvas.bbox(self.id)
            x2_max = self.canvas.winfo_reqwidth()
            if bbox[0] + dx < 0:
                dx -= bbox[0] + dx
            elif bbox[2] + dx > x2_max:
                dx -= bbox[2] + dx - x2_max
            self.canvas.move(self.id, dx, 0)

    def fire(self) -> None:
        if self.isAlive() and self.bullet is None:
            self.bullet = Bullet(self.canvas, self)
            playsound(Sounds.defender_shoot)

    def touched_by(self, bomb: 'Bomb') -> bool:
        if self.isAlive() and bomb.isAlive():
            a_bbox = self.canvas.bbox(self.id)
            b_bbox = self.canvas.bbox(bomb.id)
            inXRange = a_bbox[0] <= b_bbox[0] <= a_bbox[2] or a_bbox[0] <= b_bbox[2] <= a_bbox[2]
            inYRange = a_bbox[1] <= b_bbox[1] <= a_bbox[3] or a_bbox[1] <= b_bbox[3] <= a_bbox[3]
            return inXRange and inYRange
        return False

class Bullet:
    def __init__(self, canvas: Canvas, defender: Defender) -> None:
        self.canvas = canvas
        self.defender = defender
        self.image = get_photoimage(Images.bullet)
        self.image_explosion = get_photoimage(Images.bullet_explosion)
        self.delta_y = 18 * SPEED_SCALE
        self.alive = True
        self.explodes = False
        self.id = self._create_id()

    def _create_id(self) -> int:
        bbox = self.canvas.bbox(self.defender.id)
        return self.canvas.create_image(bbox[0] + int((bbox[2] - bbox[0]) / 2), bbox[1] - self.image.height() / 2, image=self.image)

    def isAlive(self):
        return self.alive and not self.explodes

    def kill(self) -> None:
        if self.alive:
            self.alive = False
            self.canvas.delete(self.id)
            self.defender.bullet = None

    def explode(self) -> None:
        if self.isAlive():
            self.explodes = True
            self.canvas.itemconfigure(self.id, image=self.image_explosion)
            self.canvas.after(60, lambda: self.kill())

    def move(self) -> None:
        if self.isAlive():
            bbox = self.canvas.bbox(self.id)
            if bbox[1] > self.delta_y:
                self.canvas.move(self.id, 0, -self.delta_y)
            else:
                self.explode()

class Alien:
    def __init__(self, canvas: Canvas, x: float, y: float, frames: List[Image.Image], tag: str, worth: int) -> None:
        self.canvas = canvas
        self.start_pos = x, y
        self.frames = get_photoimages(frames)
        self.current_frame = 0
        self.image_explosion = get_photoimage(Images.alien_explosion)
        self.tag = tag
        self.worth = worth
        self.alive = True
        self.explodes = False
        self.id = self._create_id()

    def _create_id(self) -> int:
        return self.canvas.create_image(*self.start_pos, image=self.frames[0], tags=self.tag)

    def isAlive(self):
        return self.alive and not self.explodes

    def kill(self) -> None:
        if self.alive:
            self.alive = False
            self.current_frame = 0
            self.canvas.itemconfigure(self.id, state='hidden', image=self.frames[0])
            
    def explode(self) -> None:
        if self.isAlive():
            self.explodes = True
            self.canvas.itemconfigure(self.id, image=self.image_explosion)
            self.canvas.after(60, lambda: self.kill())

    def move(self, dx: float, dy: float) -> None:
        if self.alive:
            self.canvas.move(self.id, dx, dy)

    def animate(self) -> None:
        if self.isAlive():
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.canvas.itemconfigure(self.id, image=self.frames[self.current_frame])

    def touched_by(self, bullet: Bullet) -> bool:
        if self.isAlive() and bullet.isAlive():
            a_bbox = self.canvas.bbox(self.id)
            b_bbox = self.canvas.bbox(bullet.id)
            inXRange = a_bbox[0] <= b_bbox[0] <= a_bbox[2] or a_bbox[0] <= b_bbox[2] <= a_bbox[2]
            inYRange = a_bbox[1] <= b_bbox[1] <= a_bbox[3] or a_bbox[1] <= b_bbox[3] <= a_bbox[3]
            return inXRange and inYRange
        return False

class Bomb:
    def __init__(self, canvas: Canvas, fleet: 'Fleet', alien: Alien) -> None:
        self.canvas = canvas
        self.fleet = fleet
        self.alien = alien
        self.current_frame = 0
        self.frames = get_photoimages([Images.bomb_1, Images.bomb_2, Images.bomb_3][randrange(3)])
        self.image_explosion = get_photoimage(Images.bomb_explosion)
        self.delta_y = 8 * SPEED_SCALE
        self.alive = True
        self.explodes = False
        self.id = self._create_id()

    def _create_id(self) -> int:
        bbox = self.canvas.bbox(self.alien.id)
        return self.canvas.create_image(bbox[0] + (bbox[2] - bbox[0]) // 2, bbox[3] + self.frames[0].height() / 2, image=self.frames[0])

    def isAlive(self):
        return self.alive and not self.explodes

    def kill(self) -> None:
        if self.alive:
            self.alive = False
            self.canvas.delete(self.id)
            self.fleet.dropped_bombs.remove(self)

    def explode(self) -> None:
        if self.isAlive():
            self.explodes = True
            self.canvas.itemconfigure(self.id, image=self.image_explosion)
            self.canvas.after(60, lambda: self.kill())

    def move(self) -> None:
        if self.isAlive():
            bbox = self.canvas.bbox(self.id)
            if bbox[3] + self.delta_y < self.canvas.winfo_reqheight():
                self.canvas.move(self.id, 0, self.delta_y)
            else:
                self.explode()

    def animate(self) -> None:
        if self.isAlive():
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.canvas.itemconfigure(self.id, image=self.frames[self.current_frame])

class Fleet:
    rows = 5
    columns = 11
    inner_gap = 4 * IMAGE_SCALE
    frames_max_width = max(max(Images.alien_squid[0].width, Images.alien_crab[0].width), Images.alien_octopus[0].width)

    def __init__(self, canvas: Canvas) -> None:
        self.canvas = canvas
        self.delta_x = 3 * SPEED_SCALE
        self.delta_y = 15 * SPEED_SCALE
        self.animation_last_time = 0.0
        self.animation_delay = 0.8
        self.current_sound = 0
        self.dropped_bombs = []
        self.dropped_bombs_max = 3
        self.dropped_bombs_last_time = 0.0
        self.dropped_bombs_delay = 0.4
        self.tag = 'fleet'
        self.aliens = self._create_fleet()
        
    def _create_fleet(self) -> None:
        aliens = []
        for row in range(Fleet.rows):
            worth, frames = (
                (30, Images.alien_squid) if row < 1 else
                (20, Images.alien_crab) if row < 3 else
                (10, Images.alien_octopus)
            )
            for column in range(Fleet.columns):
                x = column * (Fleet.frames_max_width + self.inner_gap) + Fleet.frames_max_width / 2
                y = row * (frames[0].height + self.inner_gap) + frames[0].height / 2
                alien = Alien(self.canvas, x, y, frames, self.tag, worth)
                aliens.append(alien)
        return aliens

    def _rand_bomb_drop(self) -> None:
        if len(self.dropped_bombs) < self.dropped_bombs_max and time() - self.dropped_bombs_last_time >= self.dropped_bombs_delay:
            lowest_aliens = []
            for column in range(Fleet.columns):
                for row in range(Fleet.rows - 1, -1, -1):
                    alien = self.aliens[Fleet.columns * row + column]
                    if alien.isAlive():
                        lowest_aliens.append(alien)
                        break
            if lowest_aliens != []:
                selected_aliens = sample(lowest_aliens, randrange(0, min(len(lowest_aliens), self.dropped_bombs_max - len(self.dropped_bombs)) + 1))
                for alien in selected_aliens:
                    self.dropped_bombs.append(Bomb(self.canvas, self, alien))
                self.dropped_bombs_last_time = time()

    def move(self) -> None:
        bbox = self.canvas.bbox(self.tag)
        animate = time() - self.animation_last_time >= self.animation_delay
        if bbox is not None:
            change_direction = bbox[0] + self.delta_x <= 0 or bbox[2] + self.delta_x >= self.canvas.winfo_reqwidth()
            for alien in self.aliens:
                if change_direction:
                    alien.move(0, self.delta_y)
                else:
                    alien.move(self.delta_x, 0)
                if animate:
                    alien.animate()
            if change_direction:
                self.delta_x = -self.delta_x
            self._rand_bomb_drop()
        if animate:
            self.animation_last_time = time()
            playsound(Sounds.alien_move[self.current_sound])
            self.current_sound = (self.current_sound + 1) % len(Sounds.alien_move)

    def manage_touched_aliens_by(self, defender: Defender) -> None:
        if defender.bullet is not None:
            for alien in self.aliens:
                if alien.touched_by(defender.bullet):
                    playsound(Sounds.alien_killed)
                    alien.explode()
                    defender.bullet.kill()
                    defender.score += alien.worth
                    break
    
    @staticmethod
    def get_width() -> int:
        return Fleet.columns * (Fleet.frames_max_width + Fleet.inner_gap) - Fleet.inner_gap

    @staticmethod
    def get_height() -> int:
        height = -Fleet.inner_gap
        for row in range(Fleet.rows):
            img = Images.alien_squid[0] if row < 1 else Images.alien_crab[0] if row < 3 else Images.alien_octopus[0]
            height += img.height + Fleet.inner_gap
        return height

class Game(Frame):
    class TopBar(Canvas):
        def __init__(self, game: 'Game') -> None:
            super().__init__(game, width=game.default_width, height=0, bg='#000000', highlightthickness=0)
            self.label_score_img = get_photoimage(Font.text_as_image("SCORE"))
            self.value_score_img = get_photoimage(Font.text_as_image("0000"))
            self.label_high_score_img = get_photoimage(Font.text_as_image("HI-SCORE"))
            self.value_high_score_img = get_photoimage(Font.text_as_image("0000"))

            label_score = self.create_image(Font.size, 0, image=self.label_score_img, anchor='nw', tags='content')
            
            self.value_score = self.create_image(0, 0, image=self.value_score_img, anchor='n', tags='content')
            bbox_label_score = self.bbox(label_score)
            self.move(self.value_score, bbox_x_diff_to_center(self.bbox(self.value_score), bbox_label_score), bbox_label_score[3] + Font.size)
            
            label_high_score = self.create_image(0, 0, image=self.label_high_score_img, anchor='nw', tags='content')
            self.move(label_high_score, bbox_label_score[2] + Font.size, bbox_y_diff_to_center(self.bbox(label_high_score), bbox_label_score))
            
            self.value_high_score = self.create_image(0, 0, image=self.value_high_score_img, anchor='n', tags='content')
            bbox_label_high_score = self.bbox(label_high_score)
            self.move(self.value_high_score, bbox_x_diff_to_center(self.bbox(self.value_high_score), bbox_label_high_score), bbox_label_high_score[3] + Font.size)
            
            self.configure(height=self.bbox('content')[3])

        def set_score(self, score: int) -> None:
            score %= 10000
            self.value_score_img = get_photoimage(Font.text_as_image(str(score).zfill(4)))
            self.itemconfigure(self.value_score, image=self.value_score_img)

        def set_high_score(self, score: int) -> None:
            score %= 10000
            self.value_high_score_img = get_photoimage(Font.text_as_image(str(score).zfill(4)))
            self.itemconfigure(self.value_high_score, image=self.value_high_score_img)

    class PlayMenu(Canvas):
        def __init__(self, game: 'Game') -> None:
            self.game = game
            super().__init__(self.game, width=self.game.default_width, height=self.game.default_height, bg='#000000', highlightthickness=0)
            self.images = {
                'btn': {
                    'play': get_photoimage(Font.text_as_image("PLAY")),
                    'play_hover': get_photoimage(Font.text_as_image("PLAY", "#FF0000"))
                },
                'img': {
                    'ufo': get_photoimage(Images.alien_ufo),
                    'squid': get_photoimage(Images.alien_squid[1]),
                    'crab': get_photoimage(Images.alien_crab[0]),
                    'octopus': get_photoimage(Images.alien_octopus[1])
                },
                'label': {
                    'title': get_photoimage(Font.text_as_image("SPACES  INVADERS")),
                    'sat': get_photoimage(Font.text_as_image("*SCORE ADVANCE TABLE*")),
                    'ufo': get_photoimage(Font.text_as_image("=? MYSTERY")),
                    'squid': get_photoimage(Font.text_as_image("=30 POINTS")),
                    'crab': get_photoimage(Font.text_as_image("=20 POINTS")),
                    'octopus': get_photoimage(Font.text_as_image("=10 POINTS"))
                }
            }

            self.btn_play = self.create_image(0, 0, image=self.images['btn']['play'], anchor='n', tags='content')
            label_title = self.create_image(0, self.bbox(self.btn_play)[3] + Font.size * 2, image=self.images['label']['title'], anchor='n', tags='content')
            label_sat = self.create_image(0, self.bbox(label_title)[3] + Font.size * 3, image=self.images['label']['sat'], anchor='n', tags='content')
            bbox_label_sat = self.bbox(label_sat)

            img_ufo = self.create_image(0, bbox_label_sat[3] + Font.size, image=self.images['img']['ufo'], anchor='n', tags=['score_table_img', 'score_table', 'content'])
            bbox_img_ufo = self.bbox(img_ufo)
            img_squid = self.create_image(0, bbox_img_ufo[3] + Font.size, image=self.images['img']['squid'], anchor='n', tags=['score_table_img', 'score_table', 'content'])
            bbox_img_squid = self.bbox(img_squid)
            img_crab = self.create_image(0, bbox_img_squid[3] + Font.size, image=self.images['img']['crab'], anchor='n', tags=['score_table_img', 'score_table', 'content'])
            bbox_img_crab = self.bbox(img_crab)
            img_octopus = self.create_image(0, bbox_img_crab[3] + Font.size, image=self.images['img']['octopus'], anchor='n', tags=['score_table_img', 'score_table', 'content'])
            bbox_img_octopus = self.bbox(img_octopus)

            bbox_imgs = self.bbox('score_table_img')
            label_ufo = self.create_image(bbox_imgs[2], bbox_label_sat[3] + Font.size, image=self.images['label']['ufo'], anchor='nw', tags=['score_table_label', 'score_table', 'content'])
            bbox_label_ufo = self.bbox(label_ufo)
            label_squid = self.create_image(bbox_imgs[2], bbox_label_ufo[3] + Font.size, image=self.images['label']['squid'], anchor='nw', tags=['score_table_label', 'score_table', 'content'])
            bbox_label_squid = self.bbox(label_squid)
            label_crab = self.create_image(bbox_imgs[2], bbox_label_squid[3] + Font.size, image=self.images['label']['crab'], anchor='nw', tags=['score_table_label', 'score_table', 'content'])
            bbox_label_crab = self.bbox(label_crab)
            label_octopus = self.create_image(bbox_imgs[2], bbox_label_crab[3] + Font.size, image=self.images['label']['octopus'], anchor='nw', tags=['score_table_label', 'score_table', 'content'])
            bbox_label_octopus = self.bbox(label_octopus)

            bbox_labels = self.bbox('score_table_label')
            if bbox_imgs[3] > bbox_labels[3]:
                self.move(label_ufo, 0, bbox_y_diff_to_center(bbox_label_ufo, bbox_img_ufo))
                self.move(label_squid, 0, bbox_y_diff_to_center(bbox_label_squid, bbox_img_squid))
                self.move(label_crab, 0, bbox_y_diff_to_center(bbox_label_crab, bbox_img_crab))
                self.move(label_octopus, 0, bbox_y_diff_to_center(bbox_label_octopus, bbox_img_octopus))
            elif bbox_imgs[3] < bbox_labels[3]:
                self.move(img_ufo, 0, bbox_y_diff_to_center(bbox_img_ufo, bbox_label_ufo))
                self.move(img_squid, 0, bbox_y_diff_to_center(bbox_img_squid, bbox_label_squid))
                self.move(img_crab, 0, bbox_y_diff_to_center(bbox_img_crab, bbox_label_crab))
                self.move(img_octopus, 0, bbox_y_diff_to_center(bbox_img_octopus, bbox_label_octopus))
            
            self.move('score_table', bbox_x_diff_to_center(self.bbox('score_table'), bbox_label_sat), 0)
            self.move('content', *bbox_diff_to_center(self.bbox('content'), (0, 0, self.winfo_reqwidth(), self.winfo_reqheight())))

            self.init_bindings()
        
        def init_bindings(self) -> None:
            self.bind('<Motion>', lambda e: self.on_move(e.x, e.y))
            self.bind('<Button-1>', lambda e: self.on_click(e.x, e.y))
            self.focus_set()

        def on_move(self, x: int, y: int) -> None:
            btn_play_bbox = self.bbox(self.btn_play)
            if btn_play_bbox[0] <= x <= btn_play_bbox[2] and btn_play_bbox[1] <= y <= btn_play_bbox[3]:
                self.itemconfigure(self.btn_play, image=self.images['btn']['play_hover'])
            else:
                self.itemconfigure(self.btn_play, image=self.images['btn']['play'])

        def on_click(self, x: int, y: int) -> None:
            btn_play_bbox = self.bbox(self.btn_play)
            if btn_play_bbox[0] <= x <= btn_play_bbox[2] and btn_play_bbox[1] <= y <= btn_play_bbox[3]:
                self.game.play()

    class MainGame(Canvas):
        def __init__(self, game: 'Game') -> None:
            self.game = game
            super().__init__(self.game, width=self.game.default_width, height=self.game.default_height, bg='#000000', highlightthickness=0)
            self.gameover_img = get_photoimage(Font.text_as_image("GAME OVER", "#FF0000"))
            self.gameover = False
            self.fleet = Fleet(self)
            self.defender = Defender(self)
            self.left_key_pressed = False
            self.right_key_pressed = False
            self.space_key_pressed = False
            self.init_bindings()

        def init_bindings(self) -> None:
            def setLeftKeyPressed(b): self.left_key_pressed = b
            def setRightKeyPressed(b): self.right_key_pressed = b
            def setSpaceKeyPressed(b): self.space_key_pressed = b
            self.bind('<KeyPress-Left>', lambda e: setLeftKeyPressed(True))
            self.bind('<KeyRelease-Left>', lambda e: setLeftKeyPressed(False))
            self.bind('<KeyPress-Right>', lambda e: setRightKeyPressed(True))
            self.bind('<KeyRelease-Right>', lambda e: setRightKeyPressed(False))
            self.bind('<KeyPress-space>', lambda e: setSpaceKeyPressed(True))
            self.bind('<KeyRelease-space>', lambda e: setSpaceKeyPressed(False))
            self.focus_set()

        def move_bombs(self) -> None:
            for bomb in self.fleet.dropped_bombs:
                if self.defender.touched_by(bomb):
                    bomb.kill()
                    self.defender.explode()
                    if self.defender.bullet is not None:
                        self.defender.bullet.explode()
                    for bomb in self.fleet.dropped_bombs.copy():
                        bomb.explode()
                    break
                bomb.move()
                bomb.animate()

        def move_aliens(self) -> None:
            self.fleet.manage_touched_aliens_by(self.defender)
            self.game.top_bar.set_score(self.defender.score)
            self.fleet.move()

        def action_defender(self) -> None:
            if self.left_key_pressed and not self.right_key_pressed:
                self.defender.move(-self.defender.delta_x)
            if not self.left_key_pressed and self.right_key_pressed:
                self.defender.move(self.defender.delta_x)
            if self.space_key_pressed:
                self.defender.fire()

        def move_bullet(self) -> None:
            if self.defender.bullet is not None:
                self.defender.bullet.move()

        def check_status(self) -> None:
            bbox_fleet = self.bbox(self.fleet.tag)
            bbox_defender = self.bbox(self.defender.id)
            self.gameover = self.defender.lives == 0 or (bbox_fleet is not None and bbox_fleet[3] >= bbox_defender[1])

        def animation(self) -> None:
            if not self.gameover:
                self.move_bombs()
                self.move_aliens()
                self.move_bullet()
                self.action_defender()
                self.check_status()
                self.after(30, self.animation)
            else:
                self.create_image(self.winfo_reqwidth() / 2, 0, image=self.gameover_img, anchor='n')
            
        def play(self) -> None:
            self.after(10, self.animation)

    def __init__(self, root: Tk) -> None:
        super().__init__(root, highlightthickness=0)
        self.pack(fill='both', expand=True)
        self.default_width = Fleet.get_width() * 1.5
        self.default_height = Fleet.get_height() * 2.5
        self.top_bar = Game.TopBar(self)
        self.top_bar.pack(side='top')
        self.menu_play = Game.PlayMenu(self)
        self.menu_play.pack(side='top')
        self.main_game = Game.MainGame(self)

    def play(self) -> None:
        self.menu_play.pack_forget()
        self.main_game.pack_configure(side='top')
        self.main_game.play()

class SpaceInvaders(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.wm_title('Space Invaders')
        self.wm_resizable(False, False)
        self.game = Game(self)

    def play(self) -> None:
        self.mainloop()

if __name__ == '__main__':
    SpaceInvaders().play()