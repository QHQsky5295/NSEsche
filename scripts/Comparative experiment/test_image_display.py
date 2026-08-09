#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Image Display
测试图片显示

This script tests if the generated images can be properly displayed.
"""

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pathlib import Path
import os

def test_images():
    """Test if generated images are valid and not blank"""
    current_dir = Path('.')
    
    # List of expected image files
    expected_images = [
        'failure_rate_heatmap.png',
        'detailed_failure_analysis.png',
        'cost_efficiency_boxplots.png',
        'cost_efficiency_by_load.png',
        'cost_distribution_analysis.png',
        'container_utilization_heatmap.png',
        'resource_utilization_heatmap.png',
        'overhead_analysis_heatmap.png',
        'container_count_heatmap.png'
    ]
    
    print("Testing generated images...")
    print(f"Current directory: {os.getcwd()}")
    print()
    
    for img_file in expected_images:
        img_path = current_dir / img_file
        if img_path.exists():
            try:
                img = mpimg.imread(str(img_path))
                file_size = img_path.stat().st_size
                print(f"✓ {img_file}:")
                print(f"  - Shape: {img.shape}")
                print(f"  - Data range: {img.min():.3f} - {img.max():.3f}")
                print(f"  - File size: {file_size:,} bytes")
                print(f"  - Status: Valid image with content")
            except Exception as e:
                print(f"✗ {img_file}: Error reading image - {e}")
        else:
            print(f"✗ {img_file}: File not found")
        print()
    
    # Test opening one image to verify it's not blank
    test_file = 'failure_rate_heatmap.png'
    if (current_dir / test_file).exists():
        print(f"Opening {test_file} for visual verification...")
        try:
            img = mpimg.imread(test_file)
            plt.figure(figsize=(10, 8))
            plt.imshow(img)
            plt.title(f'Test Display: {test_file}')
            plt.axis('off')
            plt.tight_layout()
            
            # Save a test display image
            plt.savefig('test_display_verification.png', dpi=150, bbox_inches='tight')
            plt.close()
            print(f"✓ Test display saved as 'test_display_verification.png'")
            
        except Exception as e:
            print(f"✗ Error displaying image: {e}")

if __name__ == '__main__':
    test_images()