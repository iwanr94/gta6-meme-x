from PIL import Image, ImageDraw, ImageFont
import os

# Create 1024x1024 square image
img = Image.new('RGB', (1024, 1024), (255, 255, 255))
draw = ImageDraw.Draw(img)

# Load DejaVu Sans Bold font (large text)
try:
    font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 96)
    font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 56)
    font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
except Exception as e:
    print(f"Warning: Could not load DejaVu font: {e}")
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()

# Define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
MAGENTA = (255, 0, 255)

# Helper function to draw 4-pointed star (sparkle)
def draw_four_pointed_star(draw, x, y, size=30, color=BLACK):
    # Draw a 4-pointed star with alternating points
    points = [
        (x, y - size),      # Top point
        (x + size//2, y),   # Right point  
        (x, y + size),      # Bottom point
        (x - size//2, y),   # Left point
        (x, y - size//3)    # Inner top point
    ]
    draw.polygon(points, fill=color)

# Helper function to draw ghost (proper ghost shape)
def draw_ghost(draw, x, y, size=240):
    # Ghost body - curved top, wavy bottom
    ghost_width = size
    ghost_height = size * 1.5
    
    # Create ghost shape: top curved (semicircle), bottom wavy
    # Top half: semicircle (curve)
    top_radius = size * 0.6
    # For arcs without outline parameter, we need to use a different approach
    # Draw white arc and then draw outline separately
    draw.arc([x - top_radius, y - size*0.3, x + top_radius, y + size*0.3], 180, 360, fill=WHITE)
    # Draw outline (using rectangle lines for ghost outline)
    draw.line([x - top_radius, y + size*0.3, x + top_radius, y + size*0.3], fill=BLACK, width=4)
    draw.line([x - top_radius, y - size*0.3, x - top_radius, y + size*0.3], fill=BLACK, width=4)
    draw.line([x + top_radius, y - size*0.3, x + top_radius, y + size*0.3], fill=BLACK, width=4)
    
    # Bottom part: wavy like ghost
    # Draw multiple small arcs to create wavy bottom
    bottom_y = y + size * 0.3
    for i in range(6):
        wave_x = x - ghost_width * (i / 6) * 0.267
        wave_radius = size * 0.2
        # Draw white arc
        draw.arc([wave_x - wave_radius, bottom_y, wave_x + wave_radius, bottom_y + wave_radius*2], 
               0, 180, fill=WHITE)
        # Draw outline for each wave
        draw.line([wave_x - wave_radius, bottom_y + wave_radius*2, wave_x + wave_radius, bottom_y + wave_radius*2], fill=BLACK, width=4)
        draw.line([wave_x - wave_radius, bottom_y, wave_x - wave_radius, bottom_y + wave_radius*2], fill=BLACK, width=4)
        draw.line([wave_x + wave_radius, bottom_y, wave_x + wave_radius, bottom_y + wave_radius*2], fill=BLACK, width=4)
    
    # Eyes - 4-pointed stars
    draw_four_pointed_star(draw, x - 35, y - 70, size=15, color=BLACK)
    draw_four_pointed_star(draw, x + 35, y - 70, size=15, color=BLACK)
    
    # Hand - simple curved shape
    hand_x = x + 90
    hand_y = y + 60
    # Simple curved hand
    for i in range(5):
        cx = hand_x + i * 10
        cy = hand_y + 20 + i * 3
        draw.ellipse([cx - 8, cy - 12, cx + 8, cy + 8], fill=WHITE, outline=BLACK, width=2)
    
    # Coin - large magenta circle with white star
    coin_x = x + 90
    coin_y = y - 80
    coin_radius = 25
    draw.ellipse([coin_x - coin_radius, coin_y - coin_radius, coin_x + coin_radius, coin_y + coin_radius], fill=MAGENTA)
    
    # White star in coin (larger)
    star_points = [
        (coin_x, coin_y - 12), (coin_x + 6, coin_y - 6),
        (coin_x + 12, coin_y), (coin_x + 6, coin_y + 6),
        (coin_x, coin_y + 12), (coin_x - 6, coin_y + 6),
        (coin_x - 12, coin_y), (coin_x - 6, coin_y - 6)
    ]
    draw.polygon(star_points, fill=WHITE)
    
    return coin_x, coin_y

# Draw the meme background and elements
# Background gradient effect - simple white

# Top half: 2013 - GTA V era
draw.rectangle([0, 0, 1024, 512], fill=(240, 240, 255))

# Main title "13 TAHUN" - LARGE centered at top
draw.text((300, 50), "13 TAHUN", fill=BLACK, font=font_large)

# 2013 section
draw.text((50, 140), "2013", fill=BLACK, font=font_medium)
draw.text((50, 210), "GTA V", fill=BLACK, font=font_small)

# Simple GTA V controller icon
draw.rectangle([50, 250, 150, 350], fill=BLACK)
draw.polygon([(75, 300), (125, 300), (75, 340), (125, 340)], fill=BLACK)

# Bottom half: 2026 - GTA VI era
draw.rectangle([0, 512, 1024, 1024], fill=(255, 240, 240))

draw.text((50, 600), "2026", fill=BLACK, font=font_medium)
draw.text((50, 670), "GTA VI", fill=BLACK, font=font_small)

# Older person with beard - simple figure
def draw_person(draw, x, y, age_description):
    # Head
    draw.ellipse([x - 30, y - 80, x + 30, y - 20], fill=(200, 180, 160), outline=BLACK, width=2)
    # Beard/hair
    if "older" in age_description or "beard" in age_description or "gray" in age_description:
        # Gray hair with beard shape
        draw.ellipse([x - 40, y - 60, x + 40, y - 30], fill=GRAY)
        # Simple beard line
        draw.arc([x - 25, y - 50, x + 25, y - 30], 0, 180, fill=GRAY, width=3)
    else:
        # Young hair
        draw.arc([x - 25, y - 60, x + 25, y - 40], 180, 360, fill=BLACK, width=2)
    
    # Body
    draw.rectangle([x - 20, y - 50, x + 20, y + 50], fill=(100, 150, 255), outline=BLACK, width=2)
    
    # Arms holding controller
    draw.rectangle([x - 35, y + 10, x - 20, y + 40], fill=(100, 150, 255), outline=BLACK, width=2)
    draw.rectangle([x + 20, y + 10, x + 35, y + 40], fill=(100, 150, 255), outline=BLACK, width=2)

# Draw older person (2026)
draw_person(draw, 450, 680, "older, beard, gray")

# Beard indicator
draw.arc([50, 720, 150, 780], 0, 180, fill=GRAY, width=3)

# Grey hair
draw.ellipse([80, 630, 200, 660], fill=GRAY)

# Make.fun ghost in the scene
ghost_x, ghost_y = draw_ghost(draw, 800, 650)

# Ghost holding coin and saying caption
draw.text((480, 800), "sambil nunggu, aku cari duit di make.fun", fill=BLACK, font=font_medium)

# Save the image
output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'meme.png')
img.save(output_path, 'PNG')
print(f"Meme saved to: {output_path}")