import pygame
import mido
import sys
import time
import math
import random
import ctypes
import os

# DPI 인식 설정
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# --- 1. 설정 및 기본 변수 ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
KEYBOARD_HEIGHT = 160
BLACK_KEY_HEIGHT = 100
BLACK_KEY_WIDTH_RATIO = 0.62
SPEED = 260  

MIDI_FILE = r"C:\Working\midi\sample.mid"  # 사용 중인 파일명

START_NOTE = 21
END_NOTE = 108

# 색상 팔레트
COLOR_BG = (12, 12, 14)
COLOR_NOTE_WHITE = (0, 195, 255)   # 스카이블루 바
COLOR_NOTE_BLACK = (255, 170, 0)   # 골드 바
COLOR_HIT_WHITE = (200, 240, 255)  # 흰건반 타건 시 색
COLOR_HIT_BLACK = (80, 80, 90)     # 검은건반 타건 시 색

BLACK_KEY_INDICES = {1, 3, 6, 8, 10}

def is_black_key(midi_note):
    return (midi_note % 12) in BLACK_KEY_INDICES

# --- 2. 건반 좌표 정밀 계산 ---
def compute_key_layouts(screen_width):
    total_white_keys = sum(1 for n in range(START_NOTE, END_NOTE + 1) if not is_black_key(n))
    white_w = screen_width / total_white_keys
    black_w = white_w * BLACK_KEY_WIDTH_RATIO

    key_positions = {}
    current_white_idx = 0

    for n in range(START_NOTE, END_NOTE + 1):
        if not is_black_key(n):
            key_positions[n] = {
                'x': current_white_idx * white_w,
                'width': white_w,
                'is_black': False
            }
            current_white_idx += 1

    for n in range(START_NOTE, END_NOTE + 1):
        if is_black_key(n):
            prev_white_x = key_positions[n - 1]['x']
            key_positions[n] = {
                'x': prev_white_x + white_w - (black_w / 2),
                'width': black_w,
                'is_black': True
            }

    return key_positions, white_w, black_w

# --- 3. MIDI 로드 ---
def load_midi(filename):
    mid = mido.MidiFile(filename)
    notes = []
    current_time = 0.0
    active_notes = {}
    for msg in mid:
        current_time += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            active_notes[msg.note] = current_time
        elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in active_notes:
                start_t = active_notes.pop(msg.note)
                duration = current_time - start_t
                notes.append({
                    'note': msg.note, 'start': start_t,
                    'duration': duration, 'is_black': is_black_key(msg.note)
                })
    return notes

# --- 4. 초기화 ---
pygame.mixer.pre_init(44100, -16, 2, 1024)
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Piano Visualizer - ShinSeon")

# 윈도우 창 최상단 및 전면 포커스 강제
try:
    hwnd = pygame.display.get_wm_info()['window']
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 5) # SW_SHOW
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
except Exception as e:
    print(f"포커스 설정 실패: {e}")

clock = pygame.time.Clock()
key_layouts, WHITE_WIDTH, BLACK_WIDTH = compute_key_layouts(SCREEN_WIDTH)
hit_line_y = SCREEN_HEIGHT - KEYBOARD_HEIGHT

try:
    notes = load_midi(MIDI_FILE)
    try:
        pygame.mixer.music.load(MIDI_FILE)
        pygame.mixer.music.play()
    except Exception as me:
        print(f"사운드 재생 안내: {me}")
except Exception as e:
    print(f"MIDI 로드 실패: {e}")
    sys.exit()

start_ticks = time.time()
running = True

# --- 5. 피아노 건반 렌더링 함수 ---
def draw_keyboard(surface, active_keys):
    # 1) 흰 건반
    for note_num in range(START_NOTE, END_NOTE + 1):
        if is_black_key(note_num):
            continue
        k = key_layouts[note_num]
        is_hit = note_num in active_keys
        
        bg_color = COLOR_HIT_WHITE if is_hit else (245, 245, 245)
        pygame.draw.rect(surface, bg_color, (k['x'], hit_line_y, k['width'], KEYBOARD_HEIGHT))
        pygame.draw.line(surface, (180, 180, 180), (k['x'], hit_line_y), (k['x'], hit_line_y + KEYBOARD_HEIGHT), 1)

    # 2) 검은 건반 그림자
    for note_num in range(START_NOTE, END_NOTE + 1):
        if not is_black_key(note_num):
            continue
        k = key_layouts[note_num]
        shadow_rect = pygame.Rect(k['x'] - 2, hit_line_y, k['width'] + 4, BLACK_KEY_HEIGHT + 4)
        pygame.draw.rect(surface, (150, 150, 150), shadow_rect, border_radius=2)

    # 3) 검은 건반 본체
    for note_num in range(START_NOTE, END_NOTE + 1):
        if not is_black_key(note_num):
            continue
        k = key_layouts[note_num]
        is_hit = note_num in active_keys
        
        body_color = COLOR_HIT_BLACK if is_hit else (25, 25, 28)
        top_color = (120, 120, 130) if is_hit else (45, 45, 50)

        pygame.draw.rect(surface, body_color, (k['x'], hit_line_y, k['width'], BLACK_KEY_HEIGHT), border_radius=2)
        pygame.draw.rect(surface, top_color, (k['x'] + 2, hit_line_y + 2, k['width'] - 4, BLACK_KEY_HEIGHT - 6), border_radius=1)

# 지글거리는 판정선
def draw_electric_line(surface, y, cur_time):
    points = []
    step = 8
    for x in range(0, SCREEN_WIDTH + step, step):
        wave = math.sin(x * 0.04 + cur_time * 10) * 1.5 + (random.random() - 0.5) * 1.0
        points.append((x, y + wave))
    pygame.draw.lines(surface, (255, 255, 255), False, points, 2)

# --- 6. 메인 루프 ---
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    elapsed_time = time.time() - start_ticks
    screen.fill(COLOR_BG)

    active_keys = set()

    # (1) 떨어지는 바 렌더링
    for draw_black in [False, True]:
        for n in notes:
            if n['is_black'] != draw_black:
                continue
            k_info = key_layouts.get(n['note'])
            if not k_info:
                continue

            bar_x, bar_w = k_info['x'], k_info['width']
            bar_h = n['duration'] * SPEED
            bar_y = hit_line_y - ((n['start'] - elapsed_time) * SPEED) - bar_h

            if n['start'] <= elapsed_time <= (n['start'] + n['duration']):
                active_keys.add(n['note'])

            if -bar_h <= bar_y <= hit_line_y:
                color = COLOR_NOTE_BLACK if n['is_black'] else COLOR_NOTE_WHITE
                pygame.draw.rect(screen, color, (bar_x + 1, bar_y, bar_w - 2, bar_h), border_radius=3)

    # (2) 피아노 건반 그리기
    draw_keyboard(screen, active_keys)

    # (3) 판정선 그리기
    draw_electric_line(screen, hit_line_y, elapsed_time)

    # (4) 건반 상단 프레임 섀도우
    pygame.draw.line(screen, (0, 0, 0), (0, hit_line_y), (SCREEN_WIDTH, hit_line_y), 2)

    pygame.display.flip()
    clock.tick(60)

pygame.mixer.music.stop()
pygame.quit()
