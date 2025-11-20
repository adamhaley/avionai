#!/usr/bin/env python3
"""
Example usage of the XLSX Generation Service API

This script demonstrates how to:
1. Check service health
2. List available templates
3. Generate XLSX files with base64 output
4. Generate XLSX files with file download
"""

import requests
import base64
import json
from pathlib import Path


# Service URL (adjust if needed)
BASE_URL = "http://localhost:8000"


def check_health():
    """Check if service is healthy"""
    print("="*70)
    print("1. Checking service health...")
    print("="*70)

    response = requests.get(f"{BASE_URL}/health")
    data = response.json()

    print(f"Status: {data['status']}")
    print(f"Version: {data['version']}")
    print(f"Templates Available: {data['templates_available']}")
    print()

    return response.status_code == 200


def list_templates():
    """List all available templates"""
    print("="*70)
    print("2. Listing available templates...")
    print("="*70)

    response = requests.get(f"{BASE_URL}/templates")
    data = response.json()

    print(f"Total Templates: {data['count']}\n")

    for template in data['templates']:
        print(f"  Name: {template['name']}")
        print(f"  Size: {template['size_bytes']} bytes")
        if template.get('sheet_name'):
            print(f"  Sheet: {template['sheet_name']}")
        if template.get('fields'):
            print(f"  Fields: {', '.join(template['fields'].keys())}")
        print()

    return data['templates']


def generate_xlsx_base64():
    """Generate XLSX and get base64 response"""
    print("="*70)
    print("3. Generating XLSX with base64 output...")
    print("="*70)

    payload = {
        "template_name": "Template.xlsx",
        "data": {
            "B3": "MSN12345",
            "B4": "Test Airline Corp",
            "B5": "Boeing 737-800",
        },
        "return_format": "base64"
    }

    print(f"Request payload:")
    print(json.dumps(payload, indent=2))
    print()

    response = requests.post(f"{BASE_URL}/generate-xlsx", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Success!")
        print(f"  File name: {data['file_name']}")
        print(f"  Base64 length: {len(data['data'])} characters")

        # Optionally decode and save
        output_path = Path("output_base64.xlsx")
        xlsx_bytes = base64.b64decode(data['data'])
        output_path.write_bytes(xlsx_bytes)
        print(f"  Saved to: {output_path}")
        print()
        return True
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")
        print()
        return False


def generate_xlsx_file():
    """Generate XLSX and download as file"""
    print("="*70)
    print("4. Generating XLSX with file download...")
    print("="*70)

    payload = {
        "template_name": "Template.xlsx",
        "data": {
            "msn": "MSN67890",  # Using field name mapping
            "lessee": "Example Airways",
            "aircraft_type": "Airbus A320",
        },
        "return_format": "file"
    }

    print(f"Request payload:")
    print(json.dumps(payload, indent=2))
    print()

    response = requests.post(f"{BASE_URL}/generate-xlsx", json=payload)

    if response.status_code == 200:
        # Save the file
        output_path = Path("output_file.xlsx")
        output_path.write_bytes(response.content)
        print(f"✓ Success!")
        print(f"  Saved to: {output_path}")
        print(f"  Size: {len(response.content)} bytes")
        print()
        return True
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.text}")
        print()
        return False


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("XLSX Generation Service - Example Usage")
    print("="*70 + "\n")

    try:
        # Check health
        if not check_health():
            print("✗ Service is not healthy. Make sure it's running.")
            print("  Start with: docker-compose up -d")
            return

        # List templates
        templates = list_templates()
        if not templates:
            print("✗ No templates found. Add .xlsx files to templates/ directory.")
            return

        # Generate examples
        generate_xlsx_base64()
        generate_xlsx_file()

        print("="*70)
        print("All examples completed!")
        print("="*70)
        print("\nGenerated files:")
        print("  - output_base64.xlsx")
        print("  - output_file.xlsx")
        print("\nOpen these files in Excel to verify the results.")
        print()

    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to service.")
        print("  Make sure the service is running:")
        print("    docker-compose up -d")
        print("  Or:")
        print("    uvicorn app.main:app --reload")
        print()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
