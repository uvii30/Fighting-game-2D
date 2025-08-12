
import pygame
import sys
import math
import random

# ---------- CONFIG ----------
WIDTH, HEIGHT = 960, 540
FPS = 60

GROUND_Y = HEIGHT - 80
GRAVITY = 0.9

PLAYER_WIDTH, PLAYER_HEIGHT = 48, 72
WALK_SPEED = 5
JUMP_VEL = -16
ATTACK_RANGE = 60
ATTACK_DURATION = 14  # frames
HIT_STUN = 20  # frames the hit player is stunned
INVULN_AFTER_HIT = 30  # frames of invulnerability after being hit
KNOCKBACK = 10

MAX_HEALTH = 100
ROUND_TIME = 60  # seconds per round
ROUNDS_TO_WIN = 2

FONT_NAME = None  # default font

# Colors
WHITE = (245, 245, 245)
BLACK = (10, 10, 10)
BG = (30, 34, 40)
BLUE = (60, 135, 255)
RED = (255, 90, 90)
DARK = (20, 22, 26)
HEALTH_GREEN = (60, 220, 120)
HEALTH_RED = (220, 60, 60)
GLOW = (255, 230, 120)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Minimal 2D Fighter — Python/Pygame")
clock = pygame.time.Clock()
font = pygame.font.Font(FONT_NAME, 20)
big_font = pygame.font.Font(FONT_NAME, 48)


# ---------- Utility ----------
def clamp(x, a, b):
    return max(a, min(b, x))


# ---------- Player Class ----------
class Player:
    def __init__(self, x, color, controls, facing=1):
        self.x = x
        self.y = GROUND_Y - PLAYER_HEIGHT
        self.vx = 0
        self.vy = 0
        self.color = color
        self.controls = controls
        self.facing = facing  # 1 right, -1 left
        self.on_ground = True

        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT

        self.attack_timer = 0
        self.is_attacking = False

        self.health = MAX_HEALTH
        self.hit_stun = 0
        self.invuln = 0

        self.rounds = 0

        self.combo = 0
        self.combo_timer = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def center_x(self):
        return self.x + self.width / 2

    def melee_hitbox(self):
        # hitbox appears in front of player when attacking
        if not self.is_attacking:
            return pygame.Rect(0, 0, 0, 0)
        w = ATTACK_RANGE
        h = self.height * 0.6
        if self.facing == 1:
            hx = self.x + self.width
        else:
            hx = self.x - w
        hy = self.y + (self.height - h) / 2
        return pygame.Rect(int(hx), int(hy), int(w), int(h))

    def apply_gravity(self):
        self.vy += GRAVITY
        self.y += self.vy
        if self.y >= GROUND_Y - self.height:
            self.y = GROUND_Y - self.height
            self.vy = 0
            self.on_ground = True
        else:
            self.on_ground = False

    def start_attack(self):
        if not self.is_attacking and self.hit_stun <= 0:
            self.is_attacking = True
            self.attack_timer = ATTACK_DURATION
            # small forward hop on attack
            self.vx += 2 * self.facing

    def update(self, keys, opponent):
        # timers
        if self.attack_timer > 0:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.is_attacking = False

        if self.hit_stun > 0:
            self.hit_stun -= 1

        if self.invuln > 0:
            self.invuln -= 1

        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0

        # movement disabled during hit stun
        if self.hit_stun > 0:
            self.apply_gravity()
            # slow horizontal deceleration
            self.vx *= 0.9
            self.x += self.vx
            self.x = clamp(self.x, 0, WIDTH - self.width)
            return

        # input movement
        left, right, jump, attack = self.controls
        moving = False

        if keys[left]:
            self.vx = -WALK_SPEED
            self.facing = -1
            moving = True
        elif keys[right]:
            self.vx = WALK_SPEED
            self.facing = 1
            moving = True
        else:
            # friction
            self.vx *= 0.8
            if abs(self.vx) < 0.2:
                self.vx = 0

        # jump
        if keys[jump] and self.on_ground:
            self.vy = JUMP_VEL
            self.on_ground = False

        # attack
        if keys[attack]:
            self.start_attack()

        # apply movement
        self.x += self.vx
        # bounds
        self.x = clamp(self.x, 0, WIDTH - self.width)

        # gravity
        self.apply_gravity()

        # facing auto-adjust when opponent is to your left/right (small AI nicety)
        if opponent.center_x() > self.center_x():
            self.facing = 1
        else:
            self.facing = -1

    def receive_hit(self, damage, direction):
        if self.invuln > 0:
            return False
        self.health -= damage
        self.hit_stun = HIT_STUN
        self.invuln = INVULN_AFTER_HIT
        # knockback
        self.vx = direction * KNOCKBACK
        self.vy = -6
        # combo handling
        self.combo += 1
        self.combo_timer = 60
        return True

    def draw(self, surf):
        # blinking if invulnerable
        if self.invuln > 0 and (self.invuln // 6) % 2 == 0:
            rect_color = DARK
        else:
            rect_color = self.color

        # body
        pygame.draw.rect(surf, rect_color, self.rect, border_radius=6)

        # face / eye to denote facing
        eye_x = int(self.x + (self.width * (0.7 if self.facing == 1 else 0.2)))
        eye_y = int(self.y + 18)
        pygame.draw.circle(surf, BLACK, (eye_x, eye_y), 4)

        # attack overlay
        if self.is_attacking:
            hb = self.melee_hitbox()
            pygame.draw.rect(surf, GLOW, hb, border_radius=6)
            # little slash line
            sx = hb.x + 6
            sy = hb.y + hb.height // 2
            ex = hb.x + hb.width - 6
            ey = sy - 10 * self.facing
            pygame.draw.line(surf, WHITE, (sx, sy), (ex, ey), 3)

        # small health number above
        hp_text = font.render(str(max(0, int(self.health))), True, WHITE)
        surf.blit(hp_text, (self.x + (self.width - hp_text.get_width()) / 2, self.y - 22))


# ---------- Game ----------
def draw_stage(surf):
    surf.fill(BG)
    # ground
    pygame.draw.rect(surf, DARK, pygame.Rect(0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    # platform decoration
    pygame.draw.line(surf, (40, 44, 50), (0, GROUND_Y), (WIDTH, GROUND_Y), 4)


def draw_health_bar(surf, x, y, w, h, current, maxv, color_fg, color_bg):
    pygame.draw.rect(surf, color_bg, (x, y, w, h), border_radius=6)
    frac = clamp(current / maxv, 0, 1)
    inner_w = int((w - 4) * frac)
    pygame.draw.rect(surf, color_fg, (x + 2, y + 2, inner_w, h - 4), border_radius=6)


def round_reset(p1, p2):
    p1.x = WIDTH * 0.25 - p1.width / 2
    p2.x = WIDTH * 0.75 - p2.width / 2
    p1.y = GROUND_Y - p1.height
    p2.y = GROUND_Y - p2.height
    p1.vx = p1.vy = p2.vx = p2.vy = 0
    p1.health = MAX_HEALTH
    p2.health = MAX_HEALTH
    p1.is_attacking = p2.is_attacking = False
    p1.attack_timer = p2.attack_timer = 0
    p1.hit_stun = p2.hit_stun = 0
    p1.invuln = p2.invuln = 0
    p1.combo = p2.combo = 0
    p1.combo_timer = p2.combo_timer = 0


def main():
    # controls: tuple of (left, right, jump, attack)
    p1_controls = (pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s)
    p2_controls = (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN)

    p1 = Player(WIDTH * 0.25, BLUE, p1_controls, facing=1)
    p2 = Player(WIDTH * 0.75, RED, p2_controls, facing=-1)

    round_time_left = ROUND_TIME
    round_active = True
    paused = False
    winner_text = ""
    round_winner = None
    last_time = pygame.time.get_ticks()

    # small "cool" background elements
    particles = []

    while True:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_SPACE and not round_active:
                    # start next round
                    round_active = True
                    round_time_left = ROUND_TIME
                    round_winner = None
                    winner_text = ""
                    round_reset(p1, p2)

        keys = pygame.key.get_pressed()

        # Stage update
        draw_stage(screen)

        # Update players
        if round_active:
            # time decrement
            now = pygame.time.get_ticks()
            if now - last_time >= 1000:
                round_time_left -= 1
                last_time = now
                if round_time_left <= 0:
                    # decide winner by health
                    round_active = False
                    if p1.health > p2.health:
                        p1.rounds += 1
                        round_winner = "Player 1"
                    elif p2.health > p1.health:
                        p2.rounds += 1
                        round_winner = "Player 2"
                    else:
                        round_winner = "Draw"
                    winner_text = f"{round_winner} wins the round!"
            # player updates
            p1.update(keys, p2)
            p2.update(keys, p1)

            # collision: attacks hit opponent?
            # P1 attack hitting P2
            if p1.is_attacking:
                hb = p1.melee_hitbox()
                if hb.colliderect(p2.rect):
                    if p2.receive_hit(12 + p1.combo * 2, p1.facing):
                        # spawn hit particle
                        particles.append([p2.center_x(), p2.y + 30, random.uniform(-3, 3), -3, 10])
                        # prevent multi-hits per attack by turning off attack briefly
                        p1.is_attacking = False
                        p1.attack_timer = 0
            # P2 attack hitting P1
            if p2.is_attacking:
                hb = p2.melee_hitbox()
                if hb.colliderect(p1.rect):
                    if p1.receive_hit(12 + p2.combo * 2, p2.facing):
                        particles.append([p1.center_x(), p1.y + 30, random.uniform(-3, 3), -3, 10])
                        p2.is_attacking = False
                        p2.attack_timer = 0

            # check death
            if p1.health <= 0 or p2.health <= 0:
                round_active = False
                if p1.health <= 0 and p2.health <= 0:
                    round_winner = "Draw"
                elif p1.health <= 0:
                    p2.rounds += 1
                    round_winner = "Player 2"
                else:
                    p1.rounds += 1
                    round_winner = "Player 1"
                winner_text = f"{round_winner} wins the round!"

        # draw players and UI
        # background parallax / subtle particles
        # update particles
        for p in particles[:]:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.15
            p[4] -= 0.5
            if p[4] <= 0:
                particles.remove(p)
        for p in particles:
            pygame.draw.circle(screen, (255, 220, 80), (int(p[0]), int(p[1])), int(max(1, p[4])))

        # draw players
        p1.draw(screen)
        p2.draw(screen)

        # UI: health bars
        margin = 24
        bar_w = 360
        bar_h = 22
        # Player 1 - left
        draw_health_bar(screen, margin, 14, bar_w, bar_h, p1.health, MAX_HEALTH, HEALTH_GREEN, (50, 55, 60))
        # Player 2 - right
        draw_health_bar(screen, WIDTH - margin - bar_w, 14, bar_w, bar_h, p2.health, MAX_HEALTH, HEALTH_RED, (50, 55, 60))

        # player names & rounds
        p1_label = font.render(f"Player 1  Rounds: {p1.rounds}", True, WHITE)
        screen.blit(p1_label, (margin, 42))
        p2_label = font.render(f"Player 2  Rounds: {p2.rounds}", True, WHITE)
        screen.blit(p2_label, (WIDTH - margin - p2_label.get_width(), 42))

        # round timer
        timer_text = font.render(f"Time: {round_time_left}", True, WHITE)
        screen.blit(timer_text, ((WIDTH - timer_text.get_width()) / 2, 14))

        # combos
        if p1.combo > 1:
            combo_t = font.render(f"Combo x{p1.combo}", True, WHITE)
            screen.blit(combo_t, (p1.x - 10, p1.y - 50))
        if p2.combo > 1:
            combo_t = font.render(f"Combo x{p2.combo}", True, WHITE)
            screen.blit(combo_t, (p2.x - 10, p2.y - 50))

        # round finished overlay
        if not round_active:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 12, 14, 180))
            screen.blit(overlay, (0, 0))
            if round_winner == "Draw":
                text = big_font.render("Draw!", True, WHITE)
            else:
                text = big_font.render(winner_text, True, WHITE)
            sub = font.render("Press SPACE to continue", True, (200, 200, 200))
            screen.blit(text, ((WIDTH - text.get_width()) / 2, HEIGHT / 2 - 40))
            screen.blit(sub, ((WIDTH - sub.get_width()) / 2, HEIGHT / 2 + 20))

            # check tournament / match winner
            if p1.rounds >= ROUNDS_TO_WIN or p2.rounds >= ROUNDS_TO_WIN:
                champ = "Player 1" if p1.rounds > p2.rounds else "Player 2"
                champ_text = big_font.render(f"{champ} WINS MATCH!", True, GLOW)
                screen.blit(champ_text, ((WIDTH - champ_text.get_width()) / 2, HEIGHT / 2 - 120))

        # little decorative tip
        tip = font.render("P1: A/D W S  |  P2: ←/→ ↑ ↓  |  Press ESC to quit", True, (160, 160, 160))
        screen.blit(tip, ((WIDTH - tip.get_width()) / 2, HEIGHT - 36))

        pygame.display.flip()


if __name__ == "__main__":
    main()
