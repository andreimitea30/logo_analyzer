import ast
import colorsys
import math
import os
import re
from collections import Counter
from urllib.parse import urljoin

import cv2
import numpy as np
import pandas as pd
import requests
import webcolors
from PIL import Image
from bs4 import BeautifulSoup
from colorthief import ColorThief
from sklearn.cluster import KMeans

BROAD_COLORS = {
    "Red": (220, 20, 60),
    "Orange": (255, 165, 0),
    "Yellow": (255, 255, 0),
    "Green": (34, 139, 34),
    "Blue": (30, 144, 255),
    "White": (255, 255, 255),
    "Black": (0, 0, 0),
}

COLOR_WARMTH = {
    "Red": 1,
    "Orange": 1,
    "Yellow": 1,
    "Green": -1,
    "Blue": -1,
    "White": 0,
    "Black": 0,
}

# Helper functions for logo download and duplicate removal

def extract_brand(domain):
    domain = domain.split(".")[0]  # Remove TLD (.com, .net, etc.)
    words = re.split(r"[-_]", domain)  # Split by dashes or underscores
    return words[0]  # Take the first part as the assumed brand

def get_logo_url(domain):
    """Try to extract a logo from the website"""
    url = f"https://{domain}" # Try HTTPS by default
    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return None # Skip if site is down

        soup = BeautifulSoup(response.text, "html.parser")

        logo_tags = soup.find_all("img")
        for tag in logo_tags:
            src = tag.get("src", "")
            if "logo" in src.lower():  # Look for 'logo' in filename
                return urljoin(url, src)

        icon_link = soup.find("link", rel="icon")
        if icon_link:
            return urljoin(url, icon_link["href"])

        favicon = urljoin(url, icon_link["href"])
        return favicon
    except Exception as e:
        return e

def download_logo(domain):
    """Download a logo from the website"""
    output_folder = "logos"
    os.makedirs(output_folder, exist_ok=True)
    logo_url = get_logo_url(domain)
    if logo_url:
        try:
            response = requests.get(logo_url, stream=True, timeout=5)
            if response.status_code == 200:
                file = os.path.join(output_folder, f"{domain.split(".")[0]}.png")
                with open(file, "wb") as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                print(f"Downloaded: {file}")
        except Exception as e:
            print(f"Failed to download {logo_url}: {e}")

def dhash(image, hash_size = 8):
    """Compute perceptual hash for an image"""
    image = image.convert("L").resize((hash_size + 1, hash_size), Image.LANCZOS)
    diff = [image.getpixel((x, y)) > image.getpixel((x + 1, y)) for y in range(hash_size) for x in range(hash_size)]
    return "".join(["1" if d else "0" for d in diff])

def calculate_histogram_similarity(image1, image2):
    """Calculate histogram similarity between two images"""
    img1 = cv2.imread(image1)
    img2 = cv2.imread(image2)

    # Check if images loaded successfully
    if img1 is None:
        raise FileNotFoundError(f"Error: Could not load image at {img1}")
    if img2 is None:
        raise FileNotFoundError(f"Error: Could not load image at {img2}")

    img1_hsv = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    img2_hsv = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)

    # Compute histograms for each channel (H, S, V)
    hist1 = cv2.calcHist([img1_hsv], [0, 1, 2], None, [50, 60, 60], [0, 180, 0, 256, 0, 256])
    hist2 = cv2.calcHist([img2_hsv], [0, 1, 2], None, [50, 60, 60], [0, 180, 0, 256, 0, 256])

    hist1 = cv2.normalize(hist1, hist1, 0, 255, cv2.NORM_MINMAX).flatten()
    hist2 = cv2.normalize(hist2, hist2, 0, 255, cv2.NORM_MINMAX).flatten()

    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return (similarity + 1) / 2 * 100

# Helper functions for main color analysis

def get_main_color(image_path):
    """Extracts the dominant color from an image using ColorThief."""
    try:
        color_thief = ColorThief(image_path)
        dominant_color = color_thief.get_color(quality=6)  # Adjust quality (lower = faster)
        return dominant_color
    except Exception as e:
        return None

def closest_colour(requested_colour):
    """Finds the closest color from the W3C color names using RGB distance."""
    distances = {}
    for name in webcolors.names():
        r_c, g_c, b_c = webcolors.name_to_rgb(name)
        rd = (r_c - requested_colour[0]) ** 2
        gd = (g_c - requested_colour[1]) ** 2
        bd = (b_c - requested_colour[2]) ** 2
        distances[name] = rd + gd + bd
    return min(distances, key=distances.get)

def closest_broad_color(rgb):
    """Finds the closest broad color to the given RGB value using Euclidean distance."""
    min_distance = float("inf")
    closest_color = None

    for color_name, color_rgb in BROAD_COLORS.items():
        distance = np.sqrt(sum((rgb[i] - color_rgb[i]) ** 2 for i in range(3)))
        if distance < min_distance:
            min_distance = distance
            closest_color = color_name

    return closest_color

def get_colour_name(requested_colour):
    """Returns actual color name if found, otherwise returns closest match."""
    try:
        actual_name = webcolors.rgb_to_name(requested_colour)
    except ValueError:
        actual_name = None
    closest_name = closest_colour(requested_colour)
    return actual_name, closest_name

def display_color_analysis(csv_path, output_file="color_analysis.md"):
    """Groups logos by their closest broad color and saves results in a Markdown file."""
    csv_file = pd.read_csv(csv_path)

    # Dictionary to store grouped logos
    color_groups = {color: [] for color in BROAD_COLORS.keys()}

    for logo, rgb_str in zip(csv_file["Logo"], csv_file["Main_Color_RGB"]):
        try:
            rgb_tuple = ast.literal_eval(rgb_str)  # Convert "(R, G, B)" string to tuple
            broad_color = closest_broad_color(rgb_tuple)
            color_groups[broad_color].append(logo)
        except Exception as e:
            pass

    # Generate Markdown content
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Logo Main Color Analysis\n\n")
        f.write("This document groups logos by their closest broad color category.\n\n")

        for color, logos in color_groups.items():
            f.write(f"## {color.capitalize()} Logos\n\n")
            if logos:
                for logo in logos:
                    f.write(f"- **{logo}**\n")
            else:
                f.write("_No logos in this category._\n")
            f.write("\n---\n\n")

    print(f"Color analysis saved to `{output_file}`")

# Helper functions for minimalism check

def extract_main_colors(image_path, num_colors=5):
    """Uses K-Means clustering to extract the main colors in an image."""
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pixels = image.reshape(-1, 3)

    kmeans = KMeans(n_clusters=num_colors, random_state=42)
    kmeans.fit(pixels)

    colors = kmeans.cluster_centers_.astype(int)  # Convert float to integer RGB
    return colors

def describe_logo_colors(rgb_colors):
    """Receives a list of RGB colors and decides whether a logo is minimalist or not."""
    color_counts = Counter(closest_broad_color(tuple(rgb)) for rgb in rgb_colors)

    # Get the two most dominant colors
    color_groups = color_counts.most_common(8)

    if len(color_groups) <= 2:
        return True

    return False

# Helper functions for behavioral analysis

def analyze_emotion(image_path):
    """Determines the emotion evoked by the dominant colors in the logo."""
    rgb_list = extract_main_colors(image_path)
    color_counts = Counter(closest_broad_color(tuple(rgb)) for rgb in rgb_list)

    # Get the most dominant colors
    color_groups = color_counts.most_common(8)

    # Calculate the overall warmth of the logo
    warmth_score = sum(COLOR_WARMTH[color] * count for color, count in color_groups)
    warmth_score /= len(color_groups)

    if warmth_score > 0.5:
        return "Energetic & Passionate"
    elif warmth_score > 0:
        return "Warm & Friendly"
    elif warmth_score < -0.5:
        return "Cool & Professional"
    elif warmth_score < 0:
        return "Calm & Trustworthy"
    return "Balanced & Neutral"

# Helper functions for color palette generation

def get_color_palette(image_name, output_folder, num_colors=5):
    """Generates a color palette from an image using K-Means clustering."""
    image_path = os.path.join("logos", image_name)
    colors = extract_main_colors(image_path)
    colors = [tuple(color) for color in colors]

    # Sort colors
    colors.sort(key=lambda x: step(x[0], x[1], x[2], 8))

    # Create palette image
    pil_img = Image.open(image_path)
    width, height = pil_img.size
    palette_height = height // 6  # Adjust palette height relative to image

    palette = Image.new('RGB', (width, palette_height), (255, 255, 255))
    color_block_width = width // num_colors

    # Draw color blocks without text
    x_offset = 0
    for color in colors:
        new_img = Image.new('RGB', (color_block_width, palette_height), color)
        palette.paste(new_img, (x_offset, 0))
        x_offset += color_block_width

    # Save the palette as a separate image
    palette.save(os.path.join(output_folder, image_name))

def step(r, g, b, repetitions=1):
    """Sorts colors for better visualization."""
    lum = math.sqrt(0.241 * r + 0.691 * g + 0.068 * b)
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return int(h * repetitions), int(lum * repetitions), int(v * repetitions)