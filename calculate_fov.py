import math

def calculate_fovx(fovy_degrees, width, height):
    # Convert FoVy from degrees to radians
    fovy_radians = math.radians(fovy_degrees)
    
    # Calculate the aspect ratio
    aspect_ratio = width / height
    
    # Calculate FoVx in radians
    fovx_radians = 2 * math.atan(math.tan(fovy_radians / 2) * aspect_ratio)
    
    # Convert FoVx back to degrees
    fovx_degrees = math.degrees(fovx_radians)
    
    return fovx_degrees

# Example usage
fovy_degrees = 60  # Vertical FOV in degrees
width = 1920       # Image width in pixels
height = 1080      # Image height in pixels

fovx_degrees = calculate_fovx(fovy_degrees, width, height)
print(f"Horizontal FOV (FoVx): {fovx_degrees:.2f} degrees") 