import arcade

# --- 基础参数 ---
TILE = 40
COLS, ROWS = 20, 15
SCREEN_W, SCREEN_H = COLS * TILE, ROWS * TILE
TITLE = "Arena AI - v0.21 SpriteList render"
SPEED = 5  # px/s

LEVEL = [
    "####################",
    "#..................#",
    "#....###...........#",
    "#..............###.#",
    "#.......####.......#",
    "#..................#",
    "#..#####...........#",
    "#..........#####...#",
    "#....#.............#",
    "#....#.............#",
    "#....#.............#",
    "#..###.............#",
    "#...........####...#",
    "#..................#",
    "####################",
]

class Player(arcade.SpriteSolidColor):
    def __init__(self, x, y):
        super().__init__(TILE, TILE, arcade.color.RED)
        self.center_x = x
        self.center_y = y
        # 强制色调为红色
        self.color = arcade.color.RED

class Game(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, update_rate=1/120)
        arcade.set_background_color(arcade.color.LIGHT_GRAY)

        # --- 精灵容器 ---
        self.player_list = arcade.SpriteList()
        self.wall_list   = arcade.SpriteList(use_spatial_hash=True)

        self.player = Player(SCREEN_W // 2, SCREEN_H // 2)
        self.player_list.append(self.player)

        self._build_level()
        self.physics = arcade.PhysicsEngineSimple(self.player, self.wall_list)

        self.keys: set[int] = set()

    def _build_level(self):
        for r, row in enumerate(LEVEL):
            for c, ch in enumerate(row):
                if ch == "#":
                    wall = arcade.SpriteSolidColor(TILE, TILE, arcade.color.WHITE)
                    wall.center_x = c * TILE + TILE // 2
                    wall.center_y = r * TILE + TILE // 2
                    wall.color = arcade.color.WHITE
                    self.wall_list.append(wall)

    # --- 事件 ---
    def on_draw(self):
        self.clear()
        self.wall_list.draw()
        self.player_list.draw()   # ✅ 用列表绘制

    def on_key_press(self, key, modifiers):
        self.keys.add(key)

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)

    def on_update(self, dt: float):
        vx = vy = 0
        if arcade.key.W in self.keys: vy += SPEED
        if arcade.key.S in self.keys: vy -= SPEED
        if arcade.key.A in self.keys: vx -= SPEED
        if arcade.key.D in self.keys: vx += SPEED

        self.player.change_x = vx
        self.player.change_y = vy
        self.physics.update()

        # 边界夹紧（防浮点抖动）
        self.player.center_x = max(TILE//2, min(SCREEN_W - TILE//2, self.player.center_x))
        self.player.center_y = max(TILE//2, min(SCREEN_H - TILE//2, self.player.center_y))

if __name__ == "__main__":
    Game()
    arcade.run()
