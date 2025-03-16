import argparse
import concurrent.futures
import os
import shutil
import warnings
from collections import defaultdict
from threading import Lock

import pandas as pd
from PIL import Image

import functions

# Global dictionary for storing hashes (thread-safe)
hashes = {}
hash_lock = Lock()

def process_logo(domain, output_folder):
    """Downloads a logo and checks for duplicates using the hash created from the image."""
    logo_path = os.path.join(output_folder, f"{domain.split(".")[0]}.png")

    # Download logo
    functions.download_logo(domain)

    # Check if file exists (download might have failed)
    if not os.path.exists(logo_path):
        return

    try:
        with Image.open(logo_path) as img:
            hash_value = functions.dhash(img)

        # Thread-safe check for duplicate images
        with hash_lock:
            if hash_value in hashes:
                os.remove(logo_path)
            else:
                hashes[hash_value] = logo_path

    except Exception:
        os.remove(logo_path)  # Remove corrupted images

def move_similar_logos(output_folder):
    """Moves similar logos to a separate folder using histogram similarity."""
    duplicates_folder = "duplicates"
    os.makedirs(duplicates_folder, exist_ok=True)

    checked_files = set()
    files = os.listdir(output_folder)

    def check_similarity(image1, image2):
        """Compare images and move duplicates."""
        file1_path = os.path.join(output_folder, image1)
        file2_path = os.path.join(output_folder, image2)

        try:
            similarity = functions.calculate_histogram_similarity(file1_path, file2_path)
            if similarity > 49 and image1[:3] == image2[:3]:  # Check first 3 chars for brand match
                print(f"Duplicate detected: {image2} ({similarity:.2f}%) -> Moving to {duplicates_folder}")
                shutil.move(file2_path, os.path.join(duplicates_folder, image2))
        except Exception as e:
            pass

    # Use ThreadPoolExecutor to speed up comparison
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for i, file1 in enumerate(files):
            if file1 in checked_files:
                continue
            for file2 in files[i + 1 :]:
                executor.submit(check_similarity, file1, file2)
            checked_files.add(file1)

def delete_corrupted_images(output_folder):
    """Deletes corrupted images from the logos folder."""
    for filename in os.listdir(output_folder):
        filepath = os.path.join(output_folder, filename)
        try:
            with Image.open(filepath):
                pass
        except Exception:
            os.remove(filepath)

def download_logos():
    """Downloads logos from websites and removes duplicates."""
    # Load dataframe
    filename = "logos.snappy.parquet"
    df = pd.read_parquet(filename).dropna().drop_duplicates()

    # Group domains by brand
    brand_dict = defaultdict(list)
    for domain in df["domain"]:
        brand = functions.extract_brand(domain)
        brand_dict[brand].append(domain)

    # Keep only one domain per brand
    selected_domains = [domains[0] for domains in brand_dict.values()]

    output_folder = "logos"
    os.makedirs(output_folder, exist_ok=True)
    print("Starting logo download...")

    # Use ThreadPoolExecutor for faster downloads
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(lambda site: process_logo(site, output_folder), selected_domains)

    print("Finished logo download.")
    print("Checking for duplicates...")

    # Move detected duplicates
    move_similar_logos(output_folder)
    delete_corrupted_images(output_folder)

    print("Duplicate check completed.")

def analyze_logos(method):
    """Analyze logos and categorize them based on color, minimalism, or emotion."""
    print(f"Starting analysis on {method} criteria...")
    input_folder = "logos"
    analysis_results = []

    for filename in os.listdir(input_folder):
        filepath = os.path.join(input_folder, filename)
        try:
            with Image.open(filepath) as img:
                if method == "color":
                    main_color = functions.get_main_color(filepath)
                    _, color_group = functions.get_colour_name(main_color)
                    analysis_results.append((filename, main_color, color_group))
                elif method == "minimalism":
                    rgb_colors = functions.extract_main_colors(filepath)
                    is_minimalist = functions.describe_logo_colors(rgb_colors)
                    analysis_results.append((filename, is_minimalist))
                elif method == "emotion":
                    emotion = functions.analyze_emotion(filepath)
                    analysis_results.append((filename, emotion))
        except Exception as e:
            pass

    # Save results
    if method == "color":
        results_df = pd.DataFrame(analysis_results, columns=["Logo", "Main_Color_RGB", "Color_Group"])
        functions.display_color_analysis("analysis_color.csv")
    elif method == "minimalism":
        results_df = pd.DataFrame(analysis_results, columns=["Logo", "Minimalist?"])
    else:
        results_df = pd.DataFrame(analysis_results, columns=["Logo", "Emotion"])

    results_df.to_csv(f"analysis_{method}.csv", index=False)
    print(f"Analysis completed. Results saved to analysis_{method}.csv")

def create_palette():
    """Create a color palette from the main colors of logos."""
    print("Starting color palette creation...")
    input_folder = "logos"
    output_folder = "palettes"
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        filepath = os.path.join(input_folder, filename)
        try:
            with Image.open(filepath):
                functions.get_color_palette(filename, output_folder)
        except Exception as e:
            pass

    print("Finished color palette creation. You can find the palettes in the 'palettes' folder.")

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    parser = argparse.ArgumentParser(description="Logo Processing Tool")
    parser.add_argument("mode", choices=["download", "analyze", "palette"], help="Choose mode: download logos or analyze logos")
    parser.add_argument("--type", choices=["color", "minimalism", "emotion"], help="Choose analysis type (for analyze mode)")

    args = parser.parse_args()

    if args.mode == "download":
        download_logos()
    elif args.mode == "analyze" and args.type:
        analyze_logos(args.type)
    elif args.mode == "palette":
        create_palette()
    else:
        print("Please provide a valid mode or analysis type.")
        parser.print_help()
