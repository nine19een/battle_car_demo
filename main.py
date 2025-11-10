import arcade
import math
import random
from arcade.hitbox import RotatableHitBox

# --- Core constants ---
TILE = 40
COLS, ROWS = 48, 27  # 48*40=1920, 27*40=1080
SCREEN_W, SCREEN_H = COLS * TILE, ROWS * TILE  # 1920x1080
TITLE = "Arena AI - v0.3 MVP (11/11)"

def _make_level(cols: int, rows: int) -> list[str]:
    rows_out: list[str] = []
    for r in range(rows):
        if r == 0 or r == rows - 1:
            rows_out.append("#" * cols)
        else:
            rows_out.append("#" + "." * (cols - 2) + "#")
    return rows_out


LEVEL = _make_level(COLS, ROWS)

class Player(arcade.SpriteSolidColor):
    def __init__(self, x, y):
        super().__init__(TILE, TILE, arcade.color.RED)
        self.center_x = x
        self.center_y = y
        # Force tint to stay red
        self.color = arcade.color.RED
        # Shrink hit box so walls do not trap the sprite (visual size unchanged)
        margin = 8  # Leave 8 px padding
        half = (TILE - margin) / 2
        hit_box = [
            (-half, -half),
            (half, -half),
            (half, half),
            (-half, half),
        ]
        self.hit_box = RotatableHitBox(hit_box)

class Enemy(arcade.SpriteSolidColor):
    def __init__(self, x: float, y: float):
        super().__init__(TILE, TILE, arcade.color.DODGER_BLUE)
        self.center_x = x
        self.center_y = y
        self.color = arcade.color.DODGER_BLUE
        self.hp = 80
        self.alive = True
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.accel = 1500.0
        self.drag = 2.6
        self.max_speed = 300.0

    def take_damage(self, dmg: float):
        if not self.alive:
            return
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False

class Game(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, update_rate=1/120)
        arcade.set_background_color(arcade.color.LIGHT_GRAY)

        # --- Sprite containers ---
        self.player_list = arcade.SpriteList()
        self.wall_list   = arcade.SpriteList(use_spatial_hash=True)
        self.enemy_list  = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList(use_spatial_hash=True)

        self.player = Player(SCREEN_W // 2, SCREEN_H // 2)
        self.player_list.append(self.player)

        # Wall occupancy (col,row) to avoid overlapping placements
        self.blocked_tiles: set[tuple[int, int]] = set()
        self.obstacle_density = 0.03  # Internal random obstacle density (reduced)

        self._build_level()
        self.physics = arcade.PhysicsEngineSimple(self.player, self.wall_list)

        self.keys: set[int] = set()

        # Enemy physics helpers
        self.enemy_engines: list[arcade.PhysicsEngineSimple] = []

        # --- Weapon: machine gun (white/green/purple) ---
        self.weapon_quality: str = "white"
        self.mg_stats = {
            "white": {"damage": 3.0,  "mag": 24, "fire_rate": 3.0,  "reload": 1.8},
            "green": {"damage": 4.0,  "mag": 30, "fire_rate": 3.3,  "reload": 1.6},
            "purple": {"damage": 5.0, "mag": 36, "fire_rate": 3.9, "reload": 1.4},
        }
        self.bullet_speed = 14
        self.firing = False
        self.fire_cd = 0.0
        self.reloading = False
        self.reload_timer = 0.0
        self.mag_size = self.mg_stats[self.weapon_quality]["mag"]
        self.ammo_in_mag = self.mag_size
        self.bullet_damage = self.mg_stats[self.weapon_quality]["damage"]
        self.fire_interval = 1.0 / self.mg_stats[self.weapon_quality]["fire_rate"]

        # --- Movement physics params ---
        self.player_vel_x = 0.0
        self.player_vel_y = 0.0
        self.move_vel_x = 0.0
        self.move_vel_y = 0.0
        self.dash_vel_x = 0.0
        self.dash_vel_y = 0.0
        self._apply_grip_preset("medium")

        # --- Dash ---
        self.dash_cooldown = 0.0
        self.dash_cd_max = 3.0
        self.dash_impulse = 900.0
        self.dash_max_speed = 700.0

        # --- Target lock & facing ---
        self.lock_target: arcade.Sprite | None = None
        self.last_move_dir: tuple[float, float] = (1.0, 0.0)

        # Round state
        self.round_active = True
        self.round_message = ""

        # Spawn initial enemies
        self._spawn_enemies(random.randint(2, 4))

    def _build_level(self):
        for r, row in enumerate(LEVEL):
            for c, ch in enumerate(row):
                if ch == "#":
                    self._add_wall_tile(c, r, arcade.color.WHITE)
        self._place_random_obstacles()

    def _apply_grip_preset(self, mode: str):
        """Apply vehicle movement preset (grip/inertia + dash behavior)."""
        presets = {
            "medium": {
                "player_max_speed": 450.0,
                "traction_accel":   2300.0,
                "roll_friction":    600.0,
                "roll_drag":        1.20,
                "steer_align":      10.0,
                "min_speed_cut":    6.0,
                "dash_decay":       5.0,
                "dash_transfer":    0.7,
            },
            "mud": {
                "player_max_speed": 200.0,
                "traction_accel":   1800.0,
                "roll_friction":    700.0,
                "roll_drag":        2.00,
                "steer_align":      11.0,
                "min_speed_cut":    7.0,
                "dash_decay":       10.0,
                "dash_transfer":    1,
            },
            "ice": {
                "player_max_speed": 600.0,
                "traction_accel":   1400.0,
                "roll_friction":    100.0,
                "roll_drag":        0.50,
                "steer_align":      3.5,
                "min_speed_cut":    2.5,
                "dash_decay":       3.5,
                "dash_transfer":    0.3,
            },
        }

        if mode not in presets:
            mode = "medium"

        p = presets[mode]
        self.player_max_speed = p["player_max_speed"]
        self.traction_accel = p["traction_accel"]
        self.roll_friction = p["roll_friction"]
        self.roll_drag = p["roll_drag"]
        self.steer_align = p["steer_align"]
        self.min_speed_cut = p["min_speed_cut"]
        self.dash_decay = p["dash_decay"]
        self.dash_transfer = p["dash_transfer"]
        self.grip_mode = mode
    def _random_open_positions(self) -> list[tuple[int, int]]:
        opens: list[tuple[int, int]] = []
        for r, row in enumerate(LEVEL):
            for c, ch in enumerate(row):
                if ch == "." and (c, r) not in self.blocked_tiles:
                    x = c * TILE + TILE // 2
                    y = r * TILE + TILE // 2
                    opens.append((x, y))
        random.shuffle(opens)
        return opens

    def _spawn_enemies(self, count: int):
        positions = self._random_open_positions()
        spawned = 0
        for (x, y) in positions:
            if math.hypot(x - self.player.center_x, y - self.player.center_y) < 5 * TILE:
                continue
            e = Enemy(x, y)
            self.enemy_list.append(e)
            self.enemy_engines.append(arcade.PhysicsEngineSimple(e, self.wall_list))
            spawned += 1
            if spawned >= count:
                break

    def _add_wall_tile(self, c: int, r: int, color=arcade.color.WHITE):
        wall = arcade.SpriteSolidColor(TILE, TILE, color)
        wall.center_x = c * TILE + TILE // 2
        wall.center_y = r * TILE + TILE // 2
        wall.color = color
        self.wall_list.append(wall)
        self.blocked_tiles.add((c, r))

    def _place_random_obstacles(self):
        safe_radius = 6 * TILE
        px, py = self.player.center_x, self.player.center_y

        def can_place_tile(col: int, row: int) -> bool:
            if col <= 0 or col >= COLS - 1 or row <= 0 or row >= ROWS - 1:
                return False
            if (col, row) in self.blocked_tiles:
                return False
            x = col * TILE + TILE // 2
            y = row * TILE + TILE // 2
            return math.hypot(x - px, y - py) >= safe_radius

        def try_place_line(col: int, row: int, dx: int, dy: int, length: int) -> bool:
            cells = []
            for i in range(length):
                cc = col + dx * i
                rr = row + dy * i
                if not can_place_tile(cc, rr):
                    return False
                cells.append((cc, rr))
            for cc, rr in cells:
                self._add_wall_tile(cc, rr, arcade.color.SILVER)
            return True

        attempts = int(self.obstacle_density * COLS * ROWS)
        for _ in range(attempts):
            col = random.randint(1, COLS - 2)
            row = random.randint(1, ROWS - 2)
            orient = random.choice([(1, 0), (0, 1)])
            length = random.randint(3, 7)
            if not try_place_line(col, row, orient[0], orient[1], length):
                continue
            # 30% chance to extend into an L-shaped corner
            if random.random() < 0.3:
                end_col = col + orient[0] * (length - 1)
                end_row = row + orient[1] * (length - 1)
                perp = (orient[1], orient[0])  # (1,0)->(0,1), (0,1)->(1,0)
                perp_len = random.randint(2, 5)
                try_place_line(end_col, end_row, perp[0], perp[1], perp_len)


    # ---- MVP 11/11 overrides & helpers ----
    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.firing = True

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.firing = False

    def on_key_press(self, key, modifiers):
        # Keep original key tracking logic
        self.keys.add(key)
        if key == arcade.key.R:
            self._start_reload()
        if key == arcade.key.SPACE:
            dirs = (arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D)
            if not any(k in self.keys for k in dirs):
                lx, ly = self.last_move_dir
                if lx or ly:
                    self.dash_vel_x += lx * self.dash_impulse
                    self.dash_vel_y += ly * self.dash_impulse
                    dash_speed = math.hypot(self.dash_vel_x, self.dash_vel_y)
                    if dash_speed > self.dash_max_speed:
                        scale = self.dash_max_speed / dash_speed
                        self.dash_vel_x *= scale
                        self.dash_vel_y *= scale
                    self.dash_cooldown = self.dash_cd_max
            else:
                self._try_dash()
        # Quality toggle hotkeys (dev helper)
        if key == arcade.key.KEY_1:
            self._set_quality("white")
        if key == arcade.key.KEY_2:
            self._set_quality("green")
        if key == arcade.key.KEY_3:
            self._set_quality("purple")

        # Grip preset hotkeys (dev helper)
        if key == arcade.key.KEY_7:
            self._apply_grip_preset("medium")
        if key == arcade.key.KEY_9:
            self._apply_grip_preset("ice")
        if key == arcade.key.KEY_0:
            self._apply_grip_preset("mud")

    def on_key_release(self, key, modifiers):
        # prevent sticky keys on release
        self.keys.discard(key)

    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.enemy_list.draw()
        self.bullet_list.draw()
        self.player_list.draw()

        if self.lock_target is not None:
            arcade.draw_lbwh_rectangle_outline(
                self.lock_target.left,
                self.lock_target.bottom,
                self.lock_target.width,
                self.lock_target.height,
                arcade.color.YELLOW,
                2,
            )

        ammo_text = f"MG[{self.weapon_quality}] {self.ammo_in_mag}/{self.mag_size}"
        if self.reloading:
            ammo_text += f"  Reloading {self.reload_timer:.1f}s"
        dash_text = f"Dash CD: {max(0.0, self.dash_cooldown):.1f}s"
        if self.round_message:
            arcade.draw_text(self.round_message, 10, SCREEN_H - 30, arcade.color.CYAN, 14)
        arcade.draw_text(ammo_text, 10, SCREEN_H - 50, arcade.color.BLACK, 14)
        arcade.draw_text(dash_text, 10, SCREEN_H - 70, arcade.color.BLACK, 14)
        arcade.draw_text(f"Grip: {getattr(self, 'grip_mode', 'medium')}", 10, SCREEN_H - 90, arcade.color.BLACK, 14)

    def on_update(self, dt: float):
        if dt <= 0:
            dt = 1 / 120

        input_x = (1 if arcade.key.D in self.keys else 0) - (1 if arcade.key.A in self.keys else 0)
        input_y = (1 if arcade.key.W in self.keys else 0) - (1 if arcade.key.S in self.keys else 0)
        vec_len = math.hypot(input_x, input_y)
        if vec_len > 0:
            input_x /= vec_len
            input_y /= vec_len
        else:
            input_x = input_y = 0.0

        if vec_len > 0:
            self.move_vel_x += input_x * self.traction_accel * dt
            self.move_vel_y += input_y * self.traction_accel * dt

            dirx, diry = input_x, input_y
            proj = self.move_vel_x * dirx + self.move_vel_y * diry
            vpx, vpy = proj * dirx, proj * diry
            vlx, vly = self.move_vel_x - vpx, self.move_vel_y - vpy
            side_decay = math.exp(-self.steer_align * dt)
            self.move_vel_x = vpx + vlx * side_decay
            self.move_vel_y = vpy + vly * side_decay
        else:
            speed = math.hypot(self.move_vel_x, self.move_vel_y)
            if speed > 0:
                decel = self.roll_friction * dt + self.roll_drag * speed * dt
                new_speed = max(0.0, speed - decel)
                if new_speed <= self.min_speed_cut:
                    self.move_vel_x = 0.0
                    self.move_vel_y = 0.0
                else:
                    scale = new_speed / speed
                    self.move_vel_x *= scale
                    self.move_vel_y *= scale

        base_speed = math.hypot(self.move_vel_x, self.move_vel_y)
        if base_speed > self.player_max_speed:
            s = self.player_max_speed / base_speed
            self.move_vel_x *= s
            self.move_vel_y *= s

        dash_decay = math.exp(-self.dash_decay * dt)
        self.dash_vel_x *= dash_decay
        self.dash_vel_y *= dash_decay

        transfer = min(self.dash_transfer * dt, 1.0)
        if transfer > 0.0:
            self.move_vel_x += self.dash_vel_x * transfer
            self.move_vel_y += self.dash_vel_y * transfer
            self.dash_vel_x *= (1.0 - transfer)
            self.dash_vel_y *= (1.0 - transfer)

        self.player_vel_x = self.move_vel_x + self.dash_vel_x
        self.player_vel_y = self.move_vel_y + self.dash_vel_y

        speed = math.hypot(self.player_vel_x, self.player_vel_y)
        max_allowed = self.dash_max_speed if speed > self.player_max_speed else self.player_max_speed
        if speed > max_allowed:
            scale = max_allowed / speed
            self.player_vel_x *= scale
            self.player_vel_y *= scale

        if self.dash_cooldown > 0:
            self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        planned_move_x = self.player_vel_x * dt
        planned_move_y = self.player_vel_y * dt
        prev_x = self.player.center_x
        prev_y = self.player.center_y

        self.player.change_x = planned_move_x
        self.player.change_y = planned_move_y
        self.physics.update()

        self.player.center_x = max(TILE//2, min(SCREEN_W - TILE//2, self.player.center_x))
        self.player.center_y = max(TILE//2, min(SCREEN_H - TILE//2, self.player.center_y))

        actual_dx = self.player.center_x - prev_x
        actual_dy = self.player.center_y - prev_y
        blocked_ratio = 0.40
        if abs(planned_move_x) > 1e-4 and abs(actual_dx) < abs(planned_move_x) * blocked_ratio:
            self.move_vel_x = 0.0
            self.dash_vel_x = 0.0
        if abs(planned_move_y) > 1e-4 and abs(actual_dy) < abs(planned_move_y) * blocked_ratio:
            self.move_vel_y = 0.0
            self.dash_vel_y = 0.0

        if dt > 0:
            self.player_vel_x = actual_dx / dt
            self.player_vel_y = actual_dy / dt
        actual_speed = math.hypot(self.player_vel_x, self.player_vel_y)
        if actual_speed > 1e-3:
            self.last_move_dir = (self.player_vel_x / actual_speed, self.player_vel_y / actual_speed)

        for enemy, engine in zip(list(self.enemy_list), list(self.enemy_engines)):
            if not enemy or not engine or not getattr(enemy, 'alive', True):
                continue
            dx = self.player.center_x - enemy.center_x
            dy = self.player.center_y - enemy.center_y
            dist = math.hypot(dx, dy)
            if dist > 0:
                dirx = dx / dist
                diry = dy / dist
            else:
                dirx = diry = 0.0
            enemy_target_x = dirx * enemy.max_speed
            enemy_target_y = diry * enemy.max_speed
            max_enemy_delta = enemy.accel * dt
            enemy.vel_x = self._approach(enemy.vel_x, enemy_target_x, max_enemy_delta)
            enemy.vel_y = self._approach(enemy.vel_y, enemy_target_y, max_enemy_delta)
            enemy_speed = math.hypot(enemy.vel_x, enemy.vel_y)
            if enemy_speed > enemy.max_speed:
                escale = enemy.max_speed / enemy_speed
                enemy.vel_x *= escale
                enemy.vel_y *= escale
            move_ex = enemy.vel_x * dt
            move_ey = enemy.vel_y * dt
            prev_ex = enemy.center_x
            prev_ey = enemy.center_y
            enemy.change_x = move_ex
            enemy.change_y = move_ey
            engine.update()
            enemy.center_x = max(TILE//2, min(SCREEN_W - TILE//2, enemy.center_x))
            enemy.center_y = max(TILE//2, min(SCREEN_H - TILE//2, enemy.center_y))
            if dt > 0:
                enemy.vel_x = (enemy.center_x - prev_ex) / dt
                enemy.vel_y = (enemy.center_y - prev_ey) / dt
        if self.fire_cd > 0:
            self.fire_cd -= dt
        if self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reloading = False
                self.ammo_in_mag = self.mag_size
        if self.firing and not self.reloading and self.fire_cd <= 0 and self.ammo_in_mag > 0:
            self._fire_bullet()

        self.bullet_list.update()
        self._resolve_bullet_collisions()
        self._update_lock_target()

        if self.round_active and len(self.enemy_list) == 0:
            self.round_active = False
            self.round_message = "Round Clear!"
            enemy.vel_x = self._approach(enemy.vel_x, enemy_target_x, max_enemy_delta)
            enemy.vel_y = self._approach(enemy.vel_y, enemy_target_y, max_enemy_delta)
            enemy_speed = math.hypot(enemy.vel_x, enemy.vel_y)
            if enemy_speed > enemy.max_speed:
                escale = enemy.max_speed / enemy_speed
                enemy.vel_x *= escale
                enemy.vel_y *= escale
            move_ex = enemy.vel_x * dt
            move_ey = enemy.vel_y * dt
            prev_ex = enemy.center_x
            prev_ey = enemy.center_y
            enemy.change_x = move_ex
            enemy.change_y = move_ey
            engine.update()
            enemy.center_x = max(TILE//2, min(SCREEN_W - TILE//2, enemy.center_x))
            enemy.center_y = max(TILE//2, min(SCREEN_H - TILE//2, enemy.center_y))
            if dt > 0:
                enemy.vel_x = (enemy.center_x - prev_ex) / dt
                enemy.vel_y = (enemy.center_y - prev_ey) / dt

        if self.fire_cd > 0:
            self.fire_cd -= dt
        if self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reloading = False
                self.ammo_in_mag = self.mag_size
        if self.firing and not self.reloading and self.fire_cd <= 0 and self.ammo_in_mag > 0:
            self._fire_bullet()

        self.bullet_list.update()
        self._resolve_bullet_collisions()
        self._update_lock_target()

        if self.round_active and len(self.enemy_list) == 0:
            self.round_active = False
            self.round_message = "Round Clear!"


    # ---- Internal helpers ----
    def _set_quality(self, q: str):
        if q not in self.mg_stats:
            return
        self.weapon_quality = q
        self.mag_size = self.mg_stats[q]["mag"]
        self.bullet_damage = self.mg_stats[q]["damage"]
        self.fire_interval = 1.0 / self.mg_stats[q]["fire_rate"]
        self.ammo_in_mag = min(self.ammo_in_mag, self.mag_size)

    def _start_reload(self):
        if self.reloading:
            return
        if self.ammo_in_mag == self.mag_size:
            return
        self.reloading = True
        self.reload_timer = self.mg_stats[self.weapon_quality]["reload"]

    def _try_dash(self):
        if self.dash_cooldown > 0:
            return
        horizontal_pos = arcade.key.D in self.keys
        horizontal_neg = arcade.key.A in self.keys
        vertical_pos = arcade.key.W in self.keys
        vertical_neg = arcade.key.S in self.keys
        if (horizontal_pos and horizontal_neg) or (vertical_pos and vertical_neg):
            return
        dirx = (1 if horizontal_pos else 0) + (-1 if horizontal_neg else 0)
        diry = (1 if vertical_pos else 0) + (-1 if vertical_neg else 0)
        length = math.hypot(dirx, diry)
        if length == 0:
            return
        dirx /= length
        diry /= length
        self.dash_vel_x += dirx * self.dash_impulse
        self.dash_vel_y += diry * self.dash_impulse
        dash_speed = math.hypot(self.dash_vel_x, self.dash_vel_y)
        if dash_speed > self.dash_max_speed:
            scale = self.dash_max_speed / dash_speed
            self.dash_vel_x *= scale
            self.dash_vel_y *= scale
        self.dash_cooldown = self.dash_cd_max

    def _aim_dir(self) -> tuple[float, float]:
        if self.lock_target is not None:
            dx = self.lock_target.center_x - self.player.center_x
            dy = self.lock_target.center_y - self.player.center_y
            l = math.hypot(dx, dy)
            if l > 0:
                return (dx / l, dy / l)
        dirx, diry = self.last_move_dir
        l = math.hypot(dirx, diry)
        if l == 0:
            return (1.0, 0.0)
        return (dirx / l, diry / l)

    def _fire_bullet(self):
        dirx, diry = self._aim_dir()
        b = arcade.SpriteSolidColor(6, 6, arcade.color.YELLOW)
        b.center_x = self.player.center_x
        b.center_y = self.player.center_y
        b.change_x = dirx * self.bullet_speed
        b.change_y = diry * self.bullet_speed
        b.damage = self.bullet_damage
        self.bullet_list.append(b)
        self.ammo_in_mag -= 1
        self.fire_cd = self.fire_interval
        if self.ammo_in_mag <= 0:
            self._start_reload()

    def _resolve_bullet_collisions(self):
        for b in list(self.bullet_list):
            if b.center_x < 0 or b.center_x > SCREEN_W or b.center_y < 0 or b.center_y > SCREEN_H:
                b.remove_from_sprite_lists()
                continue
            if arcade.check_for_collision_with_list(b, self.wall_list):
                b.remove_from_sprite_lists()
                continue
            hits = arcade.check_for_collision_with_list(b, self.enemy_list)
            if hits:
                for e in hits:
                    if hasattr(e, "take_damage"):
                        e.take_damage(b.damage)
                b.remove_from_sprite_lists()

        # Remove defeated enemies and matching physics
        survivors = arcade.SpriteList()
        new_engines: list[arcade.PhysicsEngineSimple] = []
        for e, eng in zip(self.enemy_list, self.enemy_engines):
            if getattr(e, 'alive', True):
                survivors.append(e)
                new_engines.append(eng)
        self.enemy_list = survivors
        self.enemy_engines = new_engines

    def _update_lock_target(self):
        if len(self.enemy_list) == 0:
            self.lock_target = None
            return
        px, py = self.player.center_x, self.player.center_y
        best = None
        best_d = 1e9
        for e in self.enemy_list:
            d = (e.center_x - px) ** 2 + (e.center_y - py) ** 2
            if d < best_d:
                best_d = d
                best = e
        self.lock_target = best

    @staticmethod
    def _approach(current: float, target: float, max_delta: float) -> float:
        if max_delta <= 0:
            return current
        delta = target - current
        if abs(delta) <= max_delta:
            return target
        return current + math.copysign(max_delta, delta)

    def _axis(self) -> tuple[int, int]:
        kb = getattr(self.window, "keyboard", None)
        if kb is None:
            kb = arcade.get_keyboard_state()
        dx = (1 if kb[arcade.key.D] else 0) - (1 if kb[arcade.key.A] else 0)
        dy = (1 if kb[arcade.key.W] else 0) - (1 if kb[arcade.key.S] else 0)
        return dx, dy

if __name__ == "__main__":
    Game()
    arcade.run()
