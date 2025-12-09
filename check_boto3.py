import sys
import os

python_path = r"C:\Program Files\Odoo 19\python\python.exe"
site_packages = r"C:\Program Files\Odoo 19\python\Lib\site-packages"

print("=" * 60)
print("Checking boto3 installation")
print("=" * 60)
print(f"Python path: {python_path}")
print(f"Site-packages: {site_packages}")
print()

# Check if site-packages exists
if os.path.exists(site_packages):
    print(f"✓ Site-packages directory exists")
    
    # Check for boto3 folder
    boto3_path = os.path.join(site_packages, "boto3")
    if os.path.exists(boto3_path):
        print(f"✓ boto3 folder found at: {boto3_path}")
    else:
        print(f"✗ boto3 folder NOT found at: {boto3_path}")
    
    # List all packages starting with 'b'
    print("\nPackages starting with 'b':")
    try:
        packages = [d for d in os.listdir(site_packages) if d.startswith('b') and os.path.isdir(os.path.join(site_packages, d))]
        for pkg in sorted(packages):
            print(f"  - {pkg}")
    except Exception as e:
        print(f"Error listing packages: {e}")
else:
    print(f"✗ Site-packages directory does not exist!")

print()
print("Attempting to import boto3...")
try:
    import boto3
    print(f"✓ boto3 imported successfully!")
    print(f"  Version: {boto3.__version__}")
    print(f"  Location: {boto3.__file__}")
except ImportError as e:
    print(f"✗ Failed to import boto3: {e}")
except Exception as e:
    print(f"✗ Error: {e}")

print()
print("=" * 60)
