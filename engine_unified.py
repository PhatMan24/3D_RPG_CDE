"""
UNIFIED RPG 3D ENGINE - Production Ready (FIXED v2)
Combines all features from engine.py and t3engine.py
Now includes interactive stat allocation screen with +/- buttons

Core Features:
- Full raycasting 3D engine with textures and lighting
- Character progression and stat allocation with buttons
- Combat system (melee + magic)
- Inventory and action bar management
- Enemy AI and boss battles
- Weather and time-of-day cycle
- Dynamic lighting and shadows
- Save/load functionality
"""

import pygame
import json
import os
import random
import copy
import math
from settings import *
from inventory import Inventory
from ui import ActionBar

# ============================================================================
# AUDIO SYSTEM
# ============================================================================

class DummyChannel:
    """Fallback audio channel when mixer isn't available"""
    def play(self, *args, **kwargs): pass
    def stop(self): pass
    def get_busy(self): return False
    def set_volume(self, vol): pass
    def fadeout(self, time): pass


try:
    pygame.mixer.init()
    CH_WALK = pygame.mixer.Channel(1)
    CH_RAIN = pygame.mixer.Channel(2)
    CH_CRICKETS = pygame.mixer.Channel(3)
    CH_TORCHES = pygame.mixer.Channel(4)
    MIXER_READY = True
except Exception:
    CH_WALK = DummyChannel()
    CH_RAIN = DummyChannel()
    CH_CRICKETS = DummyChannel()
    CH_TORCHES = DummyChannel()
    MIXER_READY = False


def load_audio_safe(filename):
    """Safely load audio, return None if fails"""
    if not MIXER_READY:
        return None
    try:
        return pygame.mixer.Sound(filename)
    except:
        return None


def load_image_safe(filename):
    """Safely load an image and return it, or None if it fails"""
    try:
        return pygame.image.load(filename).convert()
    except:
        return None


# Load all sound effects
SFX_PICKUP = load_audio_safe("pickup.wav")
SFX_DOOR = load_audio_safe("door.wav")
SFX_ERROR = load_audio_safe("error.wav")
SFX_USE = load_audio_safe("use.wav")
SFX_WALK = load_audio_safe("walking.mp3")
SFX_RAIN = load_audio_safe("raining.mp3")
SFX_FIREBALL = load_audio_safe("shoot_fireball.wav")
SFX_DRINK = load_audio_safe("drink.wav")
SFX_CRICKETS = load_audio_safe("Midnight_crickets.mp3")
SFX_TORCH = load_audio_safe("torches_burning_sound.mp3")
SFX_HIT_METALLIC = load_audio_safe("sword_hit_metallic.mp3")


def get_tile_color(tile_type):
    """Return color for minimap tiles based on tile type"""
    if tile_type == TileType.EMPTY.value:
        return (50, 50, 50)
    elif tile_type in [TileType.WALL_BRICK.value, TileType.WALL_STONE.value, TileType.WALL_WOOD.value]:
        return (150, 150, 150)
    elif tile_type in [TileType.TREE.value, TileType.DEAD_TREE.value, TileType.BUSH.value]:
        return (0, 150, 0)
    elif tile_type == TileType.ROCK.value:
        return (100, 100, 100)
    elif tile_type in [TileType.DOOR.value, TileType.DOOR_SILVER.value, TileType.DOOR_GOLD.value]:
        return (150, 100, 50)
    elif tile_type == TileType.STAIRS.value:
        return (200, 100, 255)
    else:
        return (50, 50, 50)


# ============================================================================
# MAIN GAME CLASS
# ============================================================================

class Game:
    """
    Unified RPG 3D Engine (FIXED v2)
    - Full 3D raycasting with textures and lighting
    - Combat, inventory, and progression systems
    - Interactive stat allocation with +/- buttons
    """

    def __init__(self):
        pygame.init()
        pygame.mouse.set_visible(False)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("RPGW3D Engine - Unified")
        self.clock = pygame.time.Clock()

        # Initialize map early
        self.map = [[TileType.EMPTY.value for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]

        # Fonts
        self.font = pygame.font.SysFont("georgia", 16)
        self.font_msg = pygame.font.SysFont("georgia", 20, bold=True)
        self.font_small_bold = pygame.font.SysFont("georgia", 14, bold=True)
        self.font_massive = pygame.font.SysFont("georgia", 60, bold=True)
        self.font_massive_win = pygame.font.SysFont("georgia", 50, bold=True)

        # Overlays
        self.game_over_overlay = pygame.Surface((WIDTH, HEIGHT))
        self.game_over_overlay.set_alpha(200)
        self.game_over_overlay.fill((100, 0, 0))

        self.level_complete_overlay = pygame.Surface((WIDTH, HEIGHT))
        self.level_complete_overlay.set_alpha(180)
        self.level_complete_overlay.fill((0, 0, 0))

        # ===== CHARACTER & PROGRESSION STATS =====
        self.stat_points = 5
        self.strength = 10
        self.intelligence = 10
        self.endurance = 10
        self.show_stat_screen = False

        self.level = 1
        self.map_level = 1
        self.xp = 0
        self.xp_to_next_level = 100

        self.recalculate_max_stats()
        self.health = self.max_health
        self.mana = self.max_mana
        self.stamina = self.max_stamina

        # ===== AUDIO & MUSIC =====
        self.sfx = {
            "pickup": SFX_PICKUP, "door": SFX_DOOR, "error": SFX_ERROR, "use": SFX_USE,
            "fireball": SFX_FIREBALL, "drink": SFX_DRINK, "torch": SFX_TORCH,
            "hit_metallic": SFX_HIT_METALLIC
        }

        self.current_bgm = "bgm.mp3"
        self.next_bgm = None
        self.bgm_fade_timer = 0
        if MIXER_READY:
            try:
                pygame.mixer.music.load(self.current_bgm)
                pygame.mixer.music.set_volume(0.15)
                pygame.mixer.music.play(-1)
            except:
                pass

        # ===== UI ICONS =====
        self.ui_icons = {
            "key": load_image_safe(KEY_PATH),
            "key_silver": load_image_safe(KEY_SILVER_PATH),
            "key_gold": load_image_safe(KEY_GOLD_PATH),
            "key_dungeon": load_image_safe(RUSTY_KEY_PATH),
            "key_rusty_2": load_image_safe(RUSTY_KEY_2_PATH),
            "sword": load_image_safe(SWORD_PATH),
            "health_potion": load_image_safe(HEALTH_POTION_PATH),
            "mana_potion": load_image_safe(MANA_POTION_PATH),
            "stamina_potion": load_image_safe(STAMINA_POTION_PATH),
            "artifact": load_image_safe(ARTIFACT_PATH),
            "fireball": load_image_safe(FIREBALL_PATH),
            "unlit_torch": load_image_safe("unlit_torch.png"),
            "lit_torch": load_image_safe("lit_torch.png"),
            "staff": load_image_safe("staff.png"),
        }

        # ===== INVENTORY & ACTION BAR =====
        self.inventory = Inventory(self.ui_icons, self.sfx)
        self.action_bar = ActionBar(self.ui_icons)

        # ===== COMBAT & PROJECTILES =====
        self.projectiles = []
        self.sparks = []
        self.attack_swing = 0.0
        self.in_combat = False
        self.game_over = False
        self.game_over_timer = 0

        # ===== MOVEMENT & INPUT =====
        # Player spawn position - will be set from map editor spawn point
        self.player_x = float(MAP_SIZE * TILE_SIZE / 2)
        self.player_y = float(MAP_SIZE * TILE_SIZE / 2)
        self.player_angle = 0.0
        self.player_speed_mod = 1.0

        # ===== TEXTURES & SPRITES =====
        self.wall_texture = load_image_safe(WALL_TEXTURE_PATH)
        self.floor_dirt_texture = load_image_safe(FLOOR_DIRT_PATH)
        self.floor_grass_texture = load_image_safe(FLOOR_GRASS_PATH)

        self.door_tex = self.load_door_texture()
        self.door_silver_tex = self.door_tex.copy()
        self.door_silver_tex.fill((100, 100, 100), special_flags=pygame.BLEND_RGB_ADD)
        self.door_gold_tex = self.door_tex.copy()
        self.door_gold_tex.fill((100, 80, 0), special_flags=pygame.BLEND_RGB_ADD)

        self.wall_textures = self.load_all_wall_textures()
        self.floor_textures = self.load_all_floor_textures()
        self.floor_tex = self.floor_textures.get('DIRT', self.floor_dirt_texture)

        self.tree_leafy_sprites = [self.load_sprite_image(p, fallback="tree") for p in TREE_LEAFY_PATHS]
        self.bush_sprites = [self.load_sprite_image(p, fallback="bush") for p in BUSH_PATHS]

        self.tree_dead_sprite = self.load_sprite_image(TREE_DEAD_PATH, fallback="dead")
        self.rock_sprite = self.load_sprite_image(ROCK_PATH, fallback="rock")
        self.torch_sprite = self.load_sprite_image("standing_torch.png", fallback="lit_torch")
        self.enemy_sprite = self.load_sprite_image("ghost_enemy_1.png", fallback="enemy")

        # ===== WEATHER SYSTEM =====
        self.weather_type = 'none'
        self.weather_time = 0
        self.weather_particles = []
        self.weather_duration = 0
        self.next_weather_time = random.randint(2000, 4000)
        self.wind_effect = 0.0
        self.particles = []

        # ===== TIME & LIGHTING =====
        self.time_of_day = 0.0
        self.sun_angle = 0.0
        self.shadow_length = 2.0
        self.ambient_light = 255
        self.global_flicker = 1.0

        # ===== RAYCASTING SURFACE =====
        self.raycasting_surface = pygame.Surface((WIDTH, HEIGHT))
        self.depth_buffer = [MAX_DEPTH] * NUM_RAYS

        # ===== INTERACTABLES =====
        self.doors = []
        self.world_torches = []
        self.hovered_interactable = None
        self.hovered_rect = None
        self.torch_timer = 0

        # ===== FOG OF WAR & MINIMAP =====
        self.fog_of_war = [[False for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        self.minimap_reveal_radius = 8
        self.minimap_x, self.minimap_y, self.minimap_size = WIDTH - 150, 20, 140

        # ===== GAME STATE =====
        self.game_over = False
        self.level_complete = False
        self.current_level = 1
        self.enemies = []
        self.world_items = []

        # Messages
        self.consume_message = ""
        self.consume_message_timer = 0

    # ========================================================================
    # STAT SYSTEM
    # ========================================================================

    def recalculate_max_stats(self):
        """Recalculate max stats based on attributes"""
        self.max_health = 50 + (self.endurance * 5)
        self.max_mana = 20 + (self.intelligence * 3)
        self.max_stamina = 50 + (self.endurance * 5)
        self.melee_dmg = 20 + int(self.strength * 1.5)
        self.magic_dmg = 25 + int(self.intelligence * 2.0)

    # ========================================================================
    # SPRITE LOADING
    # ========================================================================

    def load_sprite_image(self, path, scale=True, size=(TILE_SIZE, TILE_SIZE), fallback="tree"):
        """Load sprite with fallback generation"""
        try:
            img = pygame.image.load(path).convert_alpha()
            img.set_colorkey((0, 0, 0))
            if scale:
                return pygame.transform.scale(img, size)
            else:
                return img
        except:
            surf = pygame.Surface(size, pygame.SRCALPHA)
            if fallback == "tree":
                pygame.draw.rect(surf, (80, 50, 30), (28, 40, 8, 24))
                for _ in range(30):
                    pygame.draw.circle(surf, (34, 139, 34), (random.randint(18, 46), random.randint(8, 38)), random.randint(5, 10))
            elif fallback == "dead":
                pygame.draw.rect(surf, (60, 40, 30), (28, 40, 8, 24))
                pygame.draw.line(surf, (60, 40, 30), (32, 40), (15, 20), 4)
                pygame.draw.line(surf, (60, 40, 30), (32, 35), (45, 15), 4)
            elif fallback == "bush":
                for _ in range(20):
                    pygame.draw.circle(surf, (20, 100, 30), (random.randint(15, 49), random.randint(30, 60)), random.randint(8, 15))
            elif fallback == "rock":
                pygame.draw.polygon(surf, (100, 100, 100), [(10, 60), (32, 30), (54, 60)])
            elif fallback == "food":
                pygame.draw.circle(surf, (200, 150, 100), (size[0]//2, size[1]//2), size[0]//3)
            elif fallback == "artifact":
                pygame.draw.polygon(surf, (0, 255, 255), [(size[0]//2, 5), (size[0]-5, size[1]//2), (size[0]//2, size[1]-5), (5, size[1]//2)])
            elif fallback == "enemy":
                pygame.draw.circle(surf, (200, 50, 50), (size[0]//2, size[1]//2), size[0]//3)
                pygame.draw.circle(surf, (255, 255, 0), (size[0]//2 - 6, size[1]//2 - 4), 3)
                pygame.draw.circle(surf, (255, 255, 0), (size[0]//2 + 6, size[1]//2 - 4), 3)
            elif fallback == "unlit_torch":
                pygame.draw.rect(surf, (100, 50, 20), (size[0]//2 - 4, 10, 8, size[1] - 20))
            elif fallback == "lit_torch":
                pygame.draw.rect(surf, (100, 50, 20), (size[0]//2 - 4, 10, 8, size[1] - 20))
                pygame.draw.circle(surf, (255, 150, 0), (size[0]//2, 10), 8)
            elif fallback == "none":
                return None
            else:
                pygame.draw.circle(surf, (150, 50, 150), (size[0]//2, size[1]//2), size[0]//3)
            return surf

    # ========================================================================
    # TEXTURE LOADING
    # ========================================================================

    def load_door_texture(self):
        """Generate door texture"""
        tex = pygame.Surface((TILE_SIZE, TILE_SIZE))
        tex.fill((100, 50, 20))
        for x in range(0, TILE_SIZE, 16):
            pygame.draw.line(tex, (60, 30, 10), (x, 0), (x, TILE_SIZE), 2)
        pygame.draw.rect(tex, (100, 100, 100), (0, TILE_SIZE//2 - 4, TILE_SIZE, 8))
        pygame.draw.circle(tex, (200, 180, 50), (TILE_SIZE - 12, TILE_SIZE//2), 6)
        return tex

    def load_all_wall_textures(self):
        """Load or generate all wall textures"""
        textures = {}
        try:
            textures[TileType.WALL_BRICK.value] = pygame.transform.scale(
                pygame.image.load(WALL_TEXTURE_PATH).convert(), (TILE_SIZE, TILE_SIZE))
        except:
            tex = pygame.Surface((TILE_SIZE, TILE_SIZE))
            tex.fill((90, 45, 35))
            for y in range(0, TILE_SIZE, 16):
                pygame.draw.line(tex, (50, 25, 20), (0, y), (TILE_SIZE, y), 2)
            textures[TileType.WALL_BRICK.value] = tex

        # Stone wall
        stone = pygame.Surface((TILE_SIZE, TILE_SIZE))
        stone.fill((100, 100, 100))
        for y in range(0, TILE_SIZE, 16):
            pygame.draw.line(stone, (50, 50, 50), (0, y), (TILE_SIZE, y), 2)
            for x in range(16 if (y // 16) % 2 == 0 else 0, TILE_SIZE, 32):
                pygame.draw.line(stone, (50, 50, 50), (x, y), (x, y+16), 2)
        textures[TileType.WALL_STONE.value] = stone

        # Wood wall
        wood = pygame.Surface((TILE_SIZE, TILE_SIZE))
        wood.fill((120, 70, 30))
        for x in range(0, TILE_SIZE, 16):
            pygame.draw.line(wood, (80, 40, 15), (x, 0), (x, TILE_SIZE), 2)
        textures[TileType.WALL_WOOD.value] = wood

        # Cracked variants
        def make_cracked(base_surf):
            cracked = base_surf.copy()
            pygame.draw.lines(cracked, (15, 15, 15), False,
                            [(TILE_SIZE//2, 0), (TILE_SIZE//2 + 10, TILE_SIZE//3),
                             (TILE_SIZE//2 - 5, TILE_SIZE//2), (TILE_SIZE//2 + 8, TILE_SIZE)], 3)
            return cracked

        textures[TileType.WALL_BRICK_CRACKED.value] = make_cracked(textures[TileType.WALL_BRICK.value])
        textures[TileType.WALL_STONE_CRACKED.value] = make_cracked(textures[TileType.WALL_STONE.value])
        textures[TileType.WALL_WOOD_CRACKED.value] = make_cracked(textures[TileType.WALL_WOOD.value])

        # Force field
        ff = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        ff.fill((0, 150, 255, 180))
        for y in range(0, TILE_SIZE, 8):
            pygame.draw.line(ff, (100, 255, 255, 200), (0, y), (TILE_SIZE, y), 1)
        for x in range(0, TILE_SIZE, 8):
            pygame.draw.line(ff, (100, 255, 255, 200), (x, 0), (x, TILE_SIZE), 1)
        textures[TileType.FORCE_FIELD.value] = ff

        # Stairs
        stairs_tex = stone.copy()
        for y in range(0, TILE_SIZE, 16):
            pygame.draw.rect(stairs_tex, (30, 30, 30), (0, y, TILE_SIZE, 8))
        textures[TileType.STAIRS.value] = stairs_tex

        # Wall torch
        w_torch = textures[TileType.WALL_STONE.value].copy()
        pygame.draw.rect(w_torch, (80, 80, 80), (28, 20, 8, 20))
        pygame.draw.circle(w_torch, (255, 150, 0), (32, 16), 10)
        pygame.draw.circle(w_torch, (255, 255, 100), (32, 18), 5)
        textures[TileType.WALL_TORCH.value] = w_torch

        return textures

    def load_all_floor_textures(self):
        """Load or generate floor textures"""
        textures = {}
        try:
            textures['DIRT'] = pygame.transform.scale(
                pygame.image.load(FLOOR_DIRT_PATH).convert(), (TILE_SIZE, TILE_SIZE))
        except:
            textures['DIRT'] = self.generate_stone_dirt_texture()

        try:
            textures['GRASS'] = pygame.transform.scale(
                pygame.image.load(FLOOR_GRASS_PATH).convert(), (TILE_SIZE, TILE_SIZE))
        except:
            grass = pygame.Surface((TILE_SIZE, TILE_SIZE))
            grass.fill((34, 139, 34))
            for _ in range(100):
                pygame.draw.rect(grass, (random.randint(20, 60), random.randint(120, 150), random.randint(20, 60)),
                               (random.randint(0, 63), random.randint(0, 63), 2, 2))
            textures['GRASS'] = grass

        return textures

    def generate_stone_dirt_texture(self):
        """Generate dirt texture procedurally"""
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
        surf.fill((65, 38, 15))
        random.seed(42)
        for y in range(0, TILE_SIZE, 12):
            for x in range(0, TILE_SIZE, 12):
                cx = x + random.randint(-4, 4)
                cy = y + random.randint(-4, 4)
                r = random.uniform(5, 9)
                pts = [(cx + math.cos(math.radians(a))*r, cy + math.sin(math.radians(a))*r) for a in range(0, 360, 60)]
                pygame.draw.polygon(surf, random.choice([(125, 85, 30), (145, 100, 40), (110, 70, 20)]), pts)
        return surf

    # ========================================================================
    # MAP & LEVEL LOADING
    # ========================================================================

    def get_initial_map_data(self):
        """Load map from JSON or create default bordered map"""
        default_map = [[TileType.EMPTY.value for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        for i in range(MAP_SIZE):
            default_map[0][i] = default_map[MAP_SIZE-1][i] = default_map[i][0] = default_map[i][MAP_SIZE-1] = TileType.WALL_BRICK.value

        try:
            map_file = MAP_DATA_FILE if self.current_level == 1 else f"map_level_{self.current_level}.json"
            if os.path.exists(map_file):
                with open(map_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        map_data = data.get('map', default_map)
                    else:
                        map_data = data

                    if len(map_data) == MAP_SIZE and len(map_data[0]) == MAP_SIZE:
                        print(f"Map successfully loaded from {map_file}.")
                        return map_data
                    else:
                        print("Map data size mismatch! Falling back to default map.")
        except Exception as e:
            print(f"Failed to load map data: {e}")

        return default_map

    def pad_map(self, raw_map):
        """Ensure map has correct dimensions"""
        new_map = [[TileType.EMPTY.value for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        for y in range(min(MAP_SIZE, len(raw_map))):
            for x in range(min(MAP_SIZE, len(raw_map[y]))):
                new_map[y][x] = raw_map[y][x]
        return new_map

    def find_player_spawn_point(self):
        """Find the player spawn point from the map (P Spawn tile)"""
        for y in range(len(self.map)):
            for x in range(len(self.map[y])):
                if self.map[y][x] == TileType.PLAYER_SPAWN.value:
                    # Return the center of the tile, convert to world coordinates
                    return float(x * TILE_SIZE + TILE_SIZE // 2), float(y * TILE_SIZE + TILE_SIZE // 2)
        
        # Fallback to map center if no spawn point found
        print("No player spawn point found in map! Using map center.")
        return float(MAP_SIZE * TILE_SIZE / 2), float(MAP_SIZE * TILE_SIZE / 2)

    # ========================================================================
    # INTERACTABLES
    # ========================================================================

    def build_interactables(self):
        """Build list of doors and torches from map"""
        self.doors = []
        self.world_torches = []
        for y in range(len(self.map)):
            for x in range(len(self.map[y])):
                val = self.map[y][x]
                if val == TileType.DOOR.value:
                    self.doors.append({
                        "x": x * TILE_SIZE + TILE_SIZE // 2, "y": y * TILE_SIZE + TILE_SIZE // 2,
                        "name": "Brass Door", "key_required": "Brass Key", "gx": x, "gy": y
                    })
                elif val == TileType.DOOR_SILVER.value:
                    self.doors.append({
                        "x": x * TILE_SIZE + TILE_SIZE // 2, "y": y * TILE_SIZE + TILE_SIZE // 2,
                        "name": "Silver Door", "key_required": "Silver Key", "gx": x, "gy": y
                    })
                elif val == TileType.DOOR_GOLD.value:
                    self.doors.append({
                        "x": x * TILE_SIZE + TILE_SIZE // 2, "y": y * TILE_SIZE + TILE_SIZE // 2,
                        "name": "Gold Door", "key_required": "Gold Key", "gx": x, "gy": y
                    })
                elif val == TileType.STAIRS.value:
                    self.doors.append({
                        "x": x * TILE_SIZE + TILE_SIZE // 2,
                        "y": y * TILE_SIZE + TILE_SIZE // 2,
                        "name": "Stairs Down", "key_required": None, "gx": x, "gy": y, "is_stairs": True
                    })
                elif val in [TileType.STANDING_TORCH.value, TileType.WALL_TORCH.value]:
                    self.world_torches.append({
                        "x": x * TILE_SIZE + TILE_SIZE // 2, "y": y * TILE_SIZE + TILE_SIZE // 2,
                        "name": "Light Torch"
                    })

    def build_lightmap(self):
        """Build lightmap from torch positions"""
        h, w = len(self.map), len(self.map[0])
        self.lightmap = [[0 for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                val = self.map[y][x]
                if val == TileType.STANDING_TORCH.value or val == TileType.WALL_TORCH.value:
                    for ly in range(max(0, y-5), min(h, y+6)):
                        for lx in range(max(0, x-5), min(w, x+6)):
                            dist = math.hypot(x - lx, y - ly)
                            intensity = int(max(0, 255 - (dist * 40)))
                            self.lightmap[ly][lx] = min(255, self.lightmap[ly][lx] + intensity)

    # ========================================================================
    # SAVE/LOAD SYSTEM
    # ========================================================================

    def save_game_state(self):
        """Save game state to JSON"""
        state = {
            "health": self.health, "max_health": self.max_health,
            "mana": self.mana, "max_mana": self.max_mana,
            "stamina": self.stamina, "max_stamina": self.max_stamina,
            "level": self.level, "xp": self.xp, "xp_to_next_level": self.xp_to_next_level,
            "stat_points": self.stat_points, "strength": self.strength,
            "intelligence": self.intelligence, "endurance": self.endurance,
            "player_x": self.player_x, "player_y": self.player_y, "player_angle": self.player_angle,
            "current_level": self.current_level,
            "inventory": self.inventory.slots,
        }
        try:
            with open("savegame.json", "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Failed to save game: {e}")

    def load_game_state(self):
        """Load game state from JSON - but NOT player position (that comes from map spawn)"""
        if os.path.exists("savegame.json"):
            try:
                with open("savegame.json", "r") as f:
                    state = json.load(f)

                self.health = state.get("health", self.health)
                self.mana = state.get("mana", self.mana)
                self.stamina = state.get("stamina", self.stamina)
                self.level = state.get("level", self.level)
                self.xp = state.get("xp", self.xp)
                self.xp_to_next_level = state.get("xp_to_next_level", self.xp_to_next_level)
                self.stat_points = state.get("stat_points", self.stat_points)
                self.strength = state.get("strength", self.strength)
                self.intelligence = state.get("intelligence", self.intelligence)
                self.endurance = state.get("endurance", self.endurance)

                # Don't load player position - let map spawn point override it
                self.player_angle = state.get("player_angle", self.player_angle)

                self.recalculate_max_stats()
            except Exception as e:
                print(f"Failed to load game: {e}")

    # ========================================================================
    # MOVEMENT & COLLISION
    # ========================================================================

    def is_walkable(self, x, y):
        """Check if a tile is walkable"""
        grid_x = int(x / TILE_SIZE)
        grid_y = int(y / TILE_SIZE)

        if not (0 <= grid_x < MAP_SIZE and 0 <= grid_y < MAP_SIZE):
            return False

        tile = self.map[grid_y][grid_x]

        non_walkable = [
            TileType.WALL_BRICK.value, TileType.WALL_STONE.value, TileType.WALL_WOOD.value,
            TileType.WALL_BRICK_CRACKED.value, TileType.WALL_STONE_CRACKED.value,
            TileType.WALL_WOOD_CRACKED.value, TileType.TREE.value, TileType.DEAD_TREE.value,
            TileType.BUSH.value, TileType.ROCK.value, TileType.FORCE_FIELD.value
        ]

        return tile not in non_walkable

    def handle_player_movement(self, keys):
        """Handle player movement based on key input"""
        move_speed = PLAYER_SPEED * self.player_speed_mod

        # Forward/Backward movement
        if keys[pygame.K_w]:
            new_x = self.player_x + math.cos(self.player_angle) * move_speed
            new_y = self.player_y + math.sin(self.player_angle) * move_speed
            if self.is_walkable(new_x, new_y):
                self.player_x = new_x
                self.player_y = new_y

        if keys[pygame.K_s]:
            new_x = self.player_x - math.cos(self.player_angle) * move_speed
            new_y = self.player_y - math.sin(self.player_angle) * move_speed
            if self.is_walkable(new_x, new_y):
                self.player_x = new_x
                self.player_y = new_y

        # A and D keys - turn
        if keys[pygame.K_a]:
            self.player_angle -= PLAYER_ROTATION_SPEED

        if keys[pygame.K_d]:
            self.player_angle += PLAYER_ROTATION_SPEED

    # ========================================================================
    # WEATHER & ENVIRONMENT
    # ========================================================================

    def update_sun_position(self):
        """Update sun position based on time of day"""
        self.time_of_day += 0.0005
        if self.time_of_day >= 1.0:
            self.time_of_day = 0.0
        self.sun_angle = self.time_of_day * 2 * math.pi

    def update_weather(self):
        """Update weather system"""
        self.weather_time += 1

        if self.weather_time >= self.next_weather_time:
            self.weather_type = random.choice(WEATHER_TYPES)
            min_dur, max_dur = WEATHER_TRANSITIONS[self.weather_type]
            self.weather_duration = random.randint(min_dur, max_dur)
            self.weather_time = 0
            self.next_weather_time = random.randint(int(min_dur * 0.5), int(max_dur * 1.5))
            self.weather_particles = []

        particle_count = WEATHER_INTENSITY[self.weather_type].get('count', 0)
        while len(self.weather_particles) < particle_count:
            x = random.randint(0, WIDTH)
            y = random.randint(-50, HEIGHT)
            self.weather_particles.append([x, y])

        for particle in self.weather_particles[:]:
            if self.weather_type in ['rain', 'rain_heavy']:
                particle[1] += random.randint(5, 10)
                particle[0] += random.randint(-2, 2)
            elif self.weather_type == 'snow':
                particle[1] += random.randint(1, 3)
                particle[0] += random.randint(-1, 1)
            elif self.weather_type == 'sand':
                particle[1] += random.randint(2, 5)
                particle[0] += random.randint(2, 5)

            if particle[1] > HEIGHT:
                self.weather_particles.remove(particle)

    # ========================================================================
    # COMBAT SYSTEM
    # ========================================================================

    def perform_melee_attack(self):
        """Perform melee attack"""
        if self.stamina >= 15:
            self.stamina -= 15
            self.attack_swing = 1.0
            if self.sfx.get("use"):
                self.sfx["use"].play()

            check_dist = 50
            tx = self.player_x + math.cos(self.player_angle) * check_dist
            ty = self.player_y + math.sin(self.player_angle) * check_dist
            gx, gy = int(tx / TILE_SIZE), int(ty / TILE_SIZE)

            if 0 <= gx < len(self.map[0]) and 0 <= gy < len(self.map):
                tile_val = self.map[gy][gx]
                if tile_val in [TileType.WALL_BRICK_CRACKED.value, TileType.WALL_STONE_CRACKED.value, TileType.WALL_WOOD_CRACKED.value]:
                    self.map[gy][gx] = TileType.EMPTY.value
                    if self.sfx.get("door"):
                        self.sfx["door"].play()
        else:
            self.consume_message = "Too tired to swing!"
            self.consume_message_timer = 60
            if self.sfx.get("error"):
                self.sfx["error"].play()

    # ========================================================================
    # RAYCASTING & RENDERING
    # ========================================================================

    def cast_ray(self, angle):
        """Cast a single ray and return the distance to the nearest wall"""
        sin_a = math.sin(angle)
        cos_a = math.cos(angle)

        for depth in range(1, MAX_DEPTH):
            target_x = self.player_x + cos_a * depth
            target_y = self.player_y + sin_a * depth

            col = int(target_x / TILE_SIZE)
            row = int(target_y / TILE_SIZE)

            if col < 0 or col >= MAP_SIZE or row < 0 or row >= MAP_SIZE:
                return depth

            tile = self.map[row][col]
            # Check for blocking tiles (walls, trees, rocks, etc.)
            if tile in [TileType.WALL_BRICK.value, TileType.WALL_STONE.value, TileType.WALL_WOOD.value,
                       TileType.WALL_BRICK_CRACKED.value, TileType.WALL_STONE_CRACKED.value,
                       TileType.WALL_WOOD_CRACKED.value, TileType.TREE.value, TileType.DEAD_TREE.value,
                       TileType.BUSH.value, TileType.ROCK.value, TileType.FORCE_FIELD.value]:
                return depth

        return MAX_DEPTH

    def get_sun_brightness(self):
        """Get brightness multiplier based on sun position (0.3 - 1.0)"""
        sun_height = math.sin(self.time_of_day * math.pi)
        return 0.3 + sun_height * 0.7

    def render_3d_view(self):
        """Render the 3D first-person view using raycasting"""
        self.raycasting_surface.fill((50, 50, 60))
        pygame.draw.rect(self.raycasting_surface, (40, 50, 40), (0, HEIGHT // 2, WIDTH, HEIGHT // 2))

        sun_brightness = self.get_sun_brightness()

        for i in range(NUM_RAYS):
            angle = self.player_angle - (FOV / 2) + (i * DELTA_ANGLE)
            depth = self.cast_ray(angle)
            depth = depth * math.cos(angle - self.player_angle)

            if depth > 0:
                wall_height = min(int((WALL_HEIGHT_MULTIPLIER / depth)), HEIGHT)
            else:
                wall_height = HEIGHT

            col_width = WIDTH // NUM_RAYS
            x = i * col_width

            wall_normal = (angle + math.pi / 2)
            sun_alignment = math.cos(wall_normal - self.sun_angle)
            shadow_intensity = max(0, -sun_alignment)

            distance_shade = max(50, 255 - (depth / MAX_DEPTH) * 200)
            shadow_factor = 1.0 - (shadow_intensity * 0.5)
            final_shade = distance_shade * shadow_factor * sun_brightness
            final_shade = max(20, min(255, final_shade))

            if self.wall_texture:
                # Fixed texture mapping - use Y coordinate properly
                tex_x = int((self.player_x + math.cos(angle) * depth) / 2) % self.wall_texture.get_width()
                tex_y = int((self.player_y + math.sin(angle) * depth) / 2) % self.wall_texture.get_height()
                try:
                    tex_color = self.wall_texture.get_at((tex_x, tex_y))
                    color = tuple(int(c * final_shade / 255) for c in tex_color[:3])
                except:
                    color = (final_shade, final_shade * 0.7, final_shade * 0.5)
            else:
                color = (final_shade, final_shade * 0.7, final_shade * 0.5)

            rect = pygame.Rect(x, (HEIGHT - wall_height) // 2, col_width, wall_height)
            pygame.draw.rect(self.raycasting_surface, color, rect)

        self.screen.blit(self.raycasting_surface, (0, 0))

    # ========================================================================
    # HUD & UI RENDERING
    # ========================================================================

    def render_hud(self):
        """Render HUD with bars and stats"""
        hud_x = 10
        hud_y = 10
        bar_width = 330
        bar_height = 60
        spacing = 5

        hud_panel = pygame.Rect(hud_x - 5, hud_y - 5, bar_width + 10, (bar_height + spacing) * 5)

        pygame.draw.rect(self.screen, (30, 30, 35), hud_panel)
        pygame.draw.rect(self.screen, (200, 180, 100), hud_panel, 3)

        # Health Bar
        health_text = self.font_small_bold.render(f"HP: {int(self.health)}/{int(self.max_health)}", True, (255, 50, 50))
        self.screen.blit(health_text, (hud_x + 5, hud_y + 5))

        health_bar_rect = pygame.Rect(hud_x, hud_y + 25, bar_width, bar_height)
        pygame.draw.rect(self.screen, (50, 0, 0), health_bar_rect)
        health_fill = bar_width * (self.health / self.max_health)
        pygame.draw.rect(self.screen, (255, 50, 50), (hud_x, hud_y + 25, health_fill, bar_height))
        pygame.draw.rect(self.screen, (200, 180, 100), health_bar_rect, 2)

        # Mana Bar
        mana_y = hud_y + bar_height + spacing + 30
        mana_text = self.font_small_bold.render(f"Mana: {int(self.mana)}/{int(self.max_mana)}", True, (50, 150, 255))
        self.screen.blit(mana_text, (hud_x + 5, mana_y - 20))

        mana_bar_rect = pygame.Rect(hud_x, mana_y, bar_width, bar_height)
        pygame.draw.rect(self.screen, (0, 50, 100), mana_bar_rect)
        mana_fill = bar_width * (self.mana / self.max_mana)
        pygame.draw.rect(self.screen, (50, 100, 255), (hud_x, mana_y, mana_fill, bar_height))
        pygame.draw.rect(self.screen, (200, 180, 100), mana_bar_rect, 2)

        # Stamina Bar
        stamina_y = mana_y + bar_height + spacing
        stamina_text = self.font_small_bold.render(f"Stamina: {int(self.stamina)}/{int(self.max_stamina)}", True, (100, 255, 100))
        self.screen.blit(stamina_text, (hud_x + 5, stamina_y))

        stamina_bar_rect = pygame.Rect(hud_x, stamina_y + 20, bar_width, bar_height)
        pygame.draw.rect(self.screen, (0, 50, 0), stamina_bar_rect)
        stamina_fill = bar_width * (self.stamina / self.max_stamina)
        pygame.draw.rect(self.screen, (100, 255, 100), (hud_x, stamina_y + 20, stamina_fill, bar_height))
        pygame.draw.rect(self.screen, (200, 180, 100), stamina_bar_rect, 2)

        # Level info
        level_y = stamina_y + 45
        level_text = self.font_small_bold.render(f"LVL: {self.current_level}", True, (255, 255, 100))
        self.screen.blit(level_text, (hud_x + 5, level_y))

        # Time display
        hour = int(self.time_of_day * 24)
        time_text = self.font.render(f"Time: {hour:02d}:00", True, (200, 200, 200))
        self.screen.blit(time_text, (hud_x + 5, level_y + 25))

        # Weather indicator
        weather_text = self.font.render(f"Weather: {self.weather_type.upper()}", True, (150, 200, 255))
        self.screen.blit(weather_text, (hud_x + 5, level_y + 50))
        
        # CONTROLS INFO
        controls_y = HEIGHT - 60
        controls_text = self.font.render("WASD: Move | A/D: Turn | C: Stats | I: Inventory | LSHIFT+W: Run", True, (150, 200, 150))
        self.screen.blit(controls_text, (10, controls_y))

    def render_minimap(self):
        """Render minimap in top-right corner"""
        minimap_size = 150
        minimap_tile_size = minimap_size // MAP_SIZE
        minimap_x = WIDTH - minimap_size - 10
        minimap_y = 10

        pygame.draw.rect(self.screen, (20, 20, 20), (minimap_x, minimap_y, minimap_size, minimap_size))
        pygame.draw.rect(self.screen, (200, 180, 100), (minimap_x, minimap_y, minimap_size, minimap_size), 2)

        for y in range(MAP_SIZE):
            for x in range(MAP_SIZE):
                tile_type = self.map[y][x]
                tile_color = get_tile_color(tile_type)

                rect = pygame.Rect(
                    minimap_x + x * minimap_tile_size,
                    minimap_y + y * minimap_tile_size,
                    minimap_tile_size,
                    minimap_tile_size
                )
                pygame.draw.rect(self.screen, tile_color, rect)

        player_minimap_x = int((self.player_x / (MAP_SIZE * TILE_SIZE)) * minimap_size)
        player_minimap_y = int((self.player_y / (MAP_SIZE * TILE_SIZE)) * minimap_size)
        player_pos = (minimap_x + player_minimap_x, minimap_y + player_minimap_y)
        pygame.draw.circle(self.screen, (255, 255, 255), player_pos, 3)

    def render_cursor(self):
        """Render custom cursor"""
        mx, my = pygame.mouse.get_pos()
        cursor_color = (50, 255, 150)
        pygame.draw.polygon(self.screen, cursor_color, [(mx, my), (mx + 12, my + 12), (mx + 5, my + 12), (mx + 5, my + 18), (mx, my + 18)])
        pygame.draw.polygon(self.screen, (20, 100, 50), [(mx, my), (mx + 12, my + 12), (mx + 5, my + 12), (mx + 5, my + 18), (mx, my + 18)], 1)

    def render_stat_screen(self):
        """Render the stat allocation screen with interactive buttons"""
        self.screen.fill((20, 20, 25))

        title = self.font_massive.render("CHARACTER STATS", True, (255, 215, 0))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))

        # Stats with + and - buttons
        stat_rows = [
            ("Strength", self.strength, self.melee_dmg, "strength"),
            ("Intelligence", self.intelligence, self.magic_dmg, "intelligence"),
            ("Endurance", self.endurance, self.max_health, "endurance"),
        ]

        mouse_pos = pygame.mouse.get_pos()
        button_size = 40
        button_spacing = 20
        stat_y_start = 150
        row_height = 100

        # Draw stat rows with buttons
        for idx, (stat_name, stat_val, derived_val, stat_key) in enumerate(stat_rows):
            y = stat_y_start + (idx * row_height)
            
            # Stat name and value
            stat_text = self.font_msg.render(f"{stat_name}: {stat_val}", True, (100, 200, 255))
            self.screen.blit(stat_text, (WIDTH // 2 - 150, y))
            
            # Derived stat info
            if stat_name == "Strength":
                derived_text = self.font.render(f"Melee Damage: {self.melee_dmg}", True, (200, 100, 100))
            elif stat_name == "Intelligence":
                derived_text = self.font.render(f"Magic Damage: {self.magic_dmg}", True, (100, 150, 200))
            else:  # Endurance
                derived_text = self.font.render(f"Max HP: {self.max_health} | Max Stamina: {self.max_stamina}", True, (100, 200, 100))
            
            self.screen.blit(derived_text, (WIDTH // 2 - 150, y + 30))
            
            # MINUS BUTTON
            minus_x = WIDTH // 2 + 150
            minus_rect = pygame.Rect(minus_x, y + 5, button_size, button_size)
            minus_hover = minus_rect.collidepoint(mouse_pos)
            
            pygame.draw.rect(self.screen, (100, 60, 60) if minus_hover else (70, 50, 50), minus_rect)
            pygame.draw.rect(self.screen, (200, 150, 150) if minus_hover else (150, 100, 100), minus_rect, 2)
            
            minus_text = self.font_msg.render("-", True, (255, 255, 255))
            self.screen.blit(minus_text, (minus_x + button_size//2 - minus_text.get_width()//2, y + 5 + button_size//2 - minus_text.get_height()//2))
            
            # PLUS BUTTON
            plus_x = WIDTH // 2 + 200
            plus_rect = pygame.Rect(plus_x, y + 5, button_size, button_size)
            plus_hover = plus_rect.collidepoint(mouse_pos)
            plus_disabled = self.stat_points <= 0
            
            button_color = (60, 100, 60) if (plus_hover and not plus_disabled) else (50, 80, 50)
            if plus_disabled:
                button_color = (40, 50, 40)
            
            pygame.draw.rect(self.screen, button_color, plus_rect)
            border_color = (150, 200, 150) if (plus_hover and not plus_disabled) else (100, 150, 100)
            if plus_disabled:
                border_color = (70, 80, 70)
            pygame.draw.rect(self.screen, border_color, plus_rect, 2)
            
            plus_text = self.font_msg.render("+", True, (255, 255, 255) if not plus_disabled else (100, 100, 100))
            self.screen.blit(plus_text, (plus_x + button_size//2 - plus_text.get_width()//2, y + 5 + button_size//2 - plus_text.get_height()//2))
            
            # Store button rects for click detection
            setattr(self, f"minus_{stat_key}_rect", minus_rect)
            setattr(self, f"plus_{stat_key}_rect", plus_rect)

        # Points display
        points_y = stat_y_start + (3 * row_height) + 50
        points_text = self.font_msg.render(f"Points Available: {self.stat_points}", True, (0, 255, 100) if self.stat_points > 0 else (255, 100, 100))
        self.screen.blit(points_text, (WIDTH // 2 - points_text.get_width() // 2, points_y))

        # OK/CONFIRM BUTTON
        ok_button_y = points_y + 80
        ok_rect = pygame.Rect(WIDTH // 2 - 100, ok_button_y, 200, 50)
        ok_hover = ok_rect.collidepoint(mouse_pos)
        
        pygame.draw.rect(self.screen, (60, 100, 60) if ok_hover else (40, 70, 40), ok_rect)
        pygame.draw.rect(self.screen, (150, 200, 150) if ok_hover else (100, 150, 100), ok_rect, 3)
        
        ok_text = self.font_msg.render("OK - CONFIRM", True, (255, 255, 255))
        self.screen.blit(ok_text, (WIDTH // 2 - ok_text.get_width() // 2, ok_button_y + 10))
        
        self.ok_button_rect = ok_rect

        # Instructions
        instr = self.font.render("Click [+] or [-] to allocate | Click OK to confirm and play", True, (150, 200, 150))
        self.screen.blit(instr, (WIDTH // 2 - instr.get_width() // 2, HEIGHT - 40))

    def handle_stat_screen_click(self, mouse_pos):
        """Handle clicks on stat screen buttons"""
        # Check MINUS buttons
        if hasattr(self, 'minus_strength_rect') and self.minus_strength_rect.collidepoint(mouse_pos):
            if self.strength > 1:
                self.strength -= 1
                self.stat_points += 1
                self.recalculate_max_stats()
                self.health = self.max_health
                self.mana = self.max_mana
                self.stamina = self.max_stamina
                return
        
        if hasattr(self, 'minus_intelligence_rect') and self.minus_intelligence_rect.collidepoint(mouse_pos):
            if self.intelligence > 1:
                self.intelligence -= 1
                self.stat_points += 1
                self.recalculate_max_stats()
                self.health = self.max_health
                self.mana = self.max_mana
                self.stamina = self.max_stamina
                return
        
        if hasattr(self, 'minus_endurance_rect') and self.minus_endurance_rect.collidepoint(mouse_pos):
            if self.endurance > 1:
                self.endurance -= 1
                self.stat_points += 1
                self.recalculate_max_stats()
                self.health = self.max_health
                self.mana = self.max_mana
                self.stamina = self.max_stamina
                return
        
        # Check PLUS buttons
        if self.stat_points > 0:
            if hasattr(self, 'plus_strength_rect') and self.plus_strength_rect.collidepoint(mouse_pos):
                self.strength += 1
                self.stat_points -= 1
                self.recalculate_max_stats()
                self.health = self.max_health
                self.mana = self.max_mana
                self.stamina = self.max_stamina
                return
            
            if hasattr(self, 'plus_intelligence_rect') and self.plus_intelligence_rect.collidepoint(mouse_pos):
                self.intelligence += 1
                self.stat_points -= 1
                self.recalculate_max_stats()
                self.health = self.max_health
                self.mana = self.max_mana
                self.stamina = self.max_stamina
                return
            
            if hasattr(self, 'plus_endurance_rect') and self.plus_endurance_rect.collidepoint(mouse_pos):
                self.endurance += 1
                self.stat_points -= 1
                self.recalculate_max_stats()
                self.health = self.max_health
                self.mana = self.max_mana
                self.stamina = self.max_stamina
                return
        
        # Check OK button
        if hasattr(self, 'ok_button_rect') and self.ok_button_rect.collidepoint(mouse_pos):
            self.show_stat_screen = False
            return

    # ========================================================================
    # RENDERING PIPELINE
    # ========================================================================

    def render_weather(self):
        """Render weather particles"""
        if self.weather_type == 'none':
            return

        if self.weather_type in ['rain', 'rain_heavy']:
            color = RAIN_COLOR
            for particle in self.weather_particles:
                pygame.draw.line(self.screen, color, (particle[0], particle[1]), (particle[0], particle[1] + 5), 1)
        elif self.weather_type == 'snow':
            color = SNOW_COLOR
            for particle in self.weather_particles:
                pygame.draw.circle(self.screen, color, (int(particle[0]), int(particle[1])), 2)
        elif self.weather_type == 'sand':
            color = DUST_COLOR
            for particle in self.weather_particles:
                pygame.draw.circle(self.screen, color, (int(particle[0]), int(particle[1])), 1)

    def render_ui(self):
        """Render all UI elements"""
        self.render_minimap()
        self.render_hud()
        self.action_bar.draw(self.screen)
        mouse_pos = pygame.mouse.get_pos()
        self.inventory.draw(self.screen, mouse_pos, self.font)

    def draw(self):
        """Main draw function"""
        self.render_3d_view()
        self.render_weather()
        self.render_ui()

        if self.show_stat_screen:
            self.render_stat_screen()
        
        self.render_cursor()

        if self.game_over:
            self.screen.blit(self.game_over_overlay, (0, 0))
            game_over_text = self.font_massive.render("YOU DIED", True, (255, 0, 0))
            self.screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 2 - 50))

        elif self.level_complete:
            self.screen.blit(self.level_complete_overlay, (0, 0))
            complete_text = self.font_massive_win.render("LEVEL COMPLETE!", True, (0, 255, 100))
            self.screen.blit(complete_text, (WIDTH // 2 - complete_text.get_width() // 2, HEIGHT // 2 - 50))

    # ========================================================================
    # GAME LOOP
    # ========================================================================

    def update(self):
        """Update game state"""
        if self.health <= 0 and not self.game_over:
            self.game_over = True
            self.game_over_timer = 180

        if self.game_over:
            self.attack_swing = 0
            self.projectiles.clear()
            return

        # Update attack swing
        if self.attack_swing > 0:
            self.attack_swing -= 0.05

        # Handle stamina
        keys = pygame.key.get_pressed()
        is_moving = keys[pygame.K_w] or keys[pygame.K_s]
        is_running = keys[pygame.K_LSHIFT] and is_moving

        if is_running and self.stamina > 0:
            self.stamina -= 0.4
            self.player_speed_mod = 1.8
        elif is_moving and self.stamina > 0:
            self.stamina -= 0.1
            self.player_speed_mod = 1.0
        else:
            self.player_speed_mod = 1.0
            if self.stamina < self.max_stamina:
                self.stamina += 0.3

        # Natural recovery
        if self.mana < self.max_mana:
            self.mana += 0.1

        self.update_sun_position()
        self.update_weather()

    def run(self):
        """Main game loop"""
        self.map = self.get_initial_map_data()
        
        # Set player spawn position from map BEFORE loading game state
        self.player_x, self.player_y = self.find_player_spawn_point()
        
        self.load_game_state()
        self.build_lightmap()
        self.build_interactables()

        running = True
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    self.save_game_state()
                    if MIXER_READY:
                        pygame.mixer.music.stop()
                    return
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_c:
                        self.show_stat_screen = not self.show_stat_screen
                    elif e.key == pygame.K_i:
                        self.inventory.toggle()
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if self.show_stat_screen:
                        self.handle_stat_screen_click(pygame.mouse.get_pos())

            if self.show_stat_screen:
                # Allow movement even in stat screen
                keys = pygame.key.get_pressed()
                self.handle_player_movement(keys)
                self.update()
                self.draw()
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            if self.game_over:
                self.draw()
                pygame.display.flip()

                for e in pygame.event.get():
                    if e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_r:
                            self.__init__()
                            self.run()
                            return
                        elif e.key == pygame.K_ESCAPE:
                            self.save_game_state()
                            return

                self.clock.tick(FPS)
                continue

            if self.level_complete:
                self.draw()
                pygame.display.flip()

                for e in pygame.event.get():
                    if e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_SPACE:
                            self.level_complete = False
                            self.current_level += 1
                            self.map = self.get_initial_map_data()
                        elif e.key == pygame.K_ESCAPE:
                            self.save_game_state()
                            return

                self.clock.tick(FPS)
                continue

            # Normal gameplay
            keys = pygame.key.get_pressed()
            if not self.show_stat_screen:
                self.handle_player_movement(keys)

            self.update()
            self.draw()

            pygame.display.flip()
            self.clock.tick(FPS)
