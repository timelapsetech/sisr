from PIL import Image, ImageDraw
import os

def create_icon(size):
    # Create a new image with a transparent background
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Calculate dimensions
    padding = size // 8
    film_width = size - (2 * padding)
    film_height = size - (2 * padding)
    
    # Draw film frame (black rectangle with white border)
    draw.rectangle(
        [(padding, padding), (size - padding, size - padding)],
        fill='black',
        outline='white',
        width=max(2, size // 64)
    )
    
    # Draw scissors
    # Scissors handle
    handle_width = size // 3
    handle_height = size // 4
    handle_x = (size - handle_width) // 2
    handle_y = (size - handle_height) // 2
    
    # Draw scissors handles (two circles for the handles)
    handle_radius = size // 8
    left_handle_x = handle_x + handle_radius
    right_handle_x = handle_x + handle_width - handle_radius
    handle_y = size // 2
    
    # Left handle
    draw.ellipse(
        [(left_handle_x - handle_radius, handle_y - handle_radius),
         (left_handle_x + handle_radius, handle_y + handle_radius)],
        fill='white',
        outline='white',
        width=max(2, size // 64)
    )
    
    # Right handle
    draw.ellipse(
        [(right_handle_x - handle_radius, handle_y - handle_radius),
         (right_handle_x + handle_radius, handle_y + handle_radius)],
        fill='white',
        outline='white',
        width=max(2, size // 64)
    )
    
    # Draw scissors blades
    blade_length = size // 3
    blade_width = size // 16
    blade_x = handle_x + handle_width // 2
    blade_y = handle_y
    
    # Left blade
    draw.rectangle(
        [(blade_x - blade_length, blade_y - blade_width),
         (blade_x, blade_y + blade_width)],
        fill='white',
        outline='white',
        width=max(2, size // 64)
    )
    
    # Right blade
    draw.rectangle(
        [(blade_x, blade_y - blade_width),
         (blade_x + blade_length, blade_y + blade_width)],
        fill='white',
        outline='white',
        width=max(2, size // 64)
    )
    
    return image

def main():
    # Create icons directory if it doesn't exist
    icons_dir = 'icons'
    os.makedirs(icons_dir, exist_ok=True)
    
    # Generate icons in different sizes required for macOS
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    for size in sizes:
        icon = create_icon(size)
        icon.save(f'{icons_dir}/icon_{size}x{size}.png')
        print(f'Created {size}x{size} icon')

if __name__ == '__main__':
    main() 