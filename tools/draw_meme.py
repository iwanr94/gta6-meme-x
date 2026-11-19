from PIL import Image, ImageDraw, ImageFont
import os

# Create 1024x1024 square image
img = Image.new('RGB', (1024, 1024), (255, 255, 255))
draw = ImageDraw.Draw(img)

# Set up fonts - use default font for bold text
try:
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()
except:
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()

# Define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
MAGENTA = (255, 0, 255)

# Helper function to draw ghost (make.fun mascot)
def draw_ghost(draw, x, y, size=200):
    # Ghost body - white circle with black outline
    ghost_radius = size // 2
    # White circle
    draw.ellipse([x - ghost_radius, y - ghost_radius, x + ghost_radius, y + ghost_radius], fill=WHITE, outline=BLACK, width=3)
    
    # Eyes - black four-pointed sparkles
    eye_size = 20
    # Left eye
    eye_points = [
        (x - 30, y - 20), (x - 10, y - 20),
        (x - 20, y - 10), (x - 20, y)
    ]
    draw.polygon(eye_points, fill=BLACK)
    
    # Right eye
    eye_points = [
        (x + 10, y - 20), (x + 30, y - 20),
        (x + 20, y - 10), (x + 20, y)
    ]
    draw.polygon(eye_points, fill=BLACK)
    
    # Hand - round little hand
    hand_x = x + 60
    hand_y = y + 40
    draw.ellipse([hand_x - 15, hand_y - 20, hand_x + 15, hand_y + 10], fill=WHITE, outline=BLACK, width=2)
    
    # Coin - magenta coin with white star
    coin_x = x + 60
    coin_y = y - 40
    coin_radius = 12
    draw.ellipse([coin_x - coin_radius, coin_y - coin_radius, coin_x + coin_radius, coin_y + coin_radius], fill=MAGENTA)
    
    # White star in coin
    star_points = [
        (coin_x, coin_y - 10), (coin_x + 5, coin_y - 5),
        (coin_x + 10, coin_y), (coin_x + 5, coin_y + 5),
        (coin_x, coin_y + 10), (coin_x - 5, coin_y + 5),
        (coin_x - 10, coin_y), (coin_x - 5, coin_y - 5)
    ]
    draw.polygon(star_points, fill=WHITE)
    
    return coin_x, coin_y

# Draw the meme background and elements
# Background gradient effect - simple white

# Top half: 2013 - GTA V era
draw.rectangle([0, 0, 1024, 512], fill=(240, 240, 255))

# 2013 text
draw.text((50, 80), "2013", fill=BLACK, font=font_large)
draw.text((50, 150), "GTA V", fill=BLACK, font=font_medium)

# Simple GTA V controller icon
draw.rectangle([50, 250, 150, 350], fill=BLACK)
draw.polygon([(75, 300), (125, 300), (75, 340), (125, 340)], fill=BLACK)

# Bottom half: 2026 - GTA VI era
draw.rectangle([0, 512, 1024, 1024], fill=(255, 240, 240))

# 2026 text
draw.text((50, 600), "2026", fill=BLACK, font=font_large)
draw.text((50, 670), "GTA VI", fill=BLACK, font=font_medium)

# Beard indicator
draw.arc([50, 720, 150, 780], 0, 180, fill=GRAY, width=3)

# Grey hair
# Hair shape above head
draw.ellipse([80, 630, 200, 660], fill=GRAY)

# Make.fun ghost in the scene
ghost_x, ghost_y = draw_ghost(draw, 600, 700)

# Ghost holding coin and saying caption
draw.text((480, 750), "sambil nunggu, aku cari duit di make.fun", fill=BLACK, font=font_medium)

# Save the image
output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'meme.png')
img.save(output_path, 'PNG')
print(f"Meme saved to: {output_path}")