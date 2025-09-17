#!/usr/bin/env python3
"""
Helper script to set up test documents in the test_documents folder.
This makes them available for automated testing.
"""

import os
import shutil
import glob

def setup_test_documents():
    """Copy test documents to test_documents folder for testing."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    test_docs_dir = os.path.join(project_root, 'test_documents')
    
    # Ensure test_documents folder exists
    if not os.path.exists(test_docs_dir):
        os.makedirs(test_docs_dir)
        print(f"✅ Created test_documents folder: {test_docs_dir}")
    
    # Look for test documents in common locations
    search_paths = [
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"), 
        os.path.expanduser("~/Documents"),
        project_root
    ]
    
    # Common test document patterns
    patterns = ['EXAMPLE_IMAGE*', 'example_image*', 'test_claim*', 'claim_*', 'sample_*']
    
    found_docs = []
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            continue
            
        for pattern in patterns:
            matches = glob.glob(os.path.join(search_path, pattern + '.*'))
            for match in matches:
                if match.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    found_docs.append(match)
    
    if not found_docs:
        print("❌ No test documents found in common locations")
        print("📝 Please copy your test documents to:")
        print(f"   {test_docs_dir}")
        print("\n🎯 Supported formats: PDF, PNG, JPG, JPEG")
        print("📋 Example: EXAMPLE_IMAGE_1.pdf, EXAMPLE_IMAGE_2.pdf")
        return False
    
    # Copy documents to test_documents folder
    copied_count = 0
    for doc_path in found_docs:
        filename = os.path.basename(doc_path)
        dest_path = os.path.join(test_docs_dir, filename)
        
        if not os.path.exists(dest_path):
            try:
                shutil.copy2(doc_path, dest_path)
                print(f"✅ Copied: {filename}")
                copied_count += 1
            except Exception as e:
                print(f"❌ Failed to copy {filename}: {e}")
        else:
            print(f"ℹ️  Already exists: {filename}")
    
    print(f"\n📋 Setup complete: {copied_count} new documents copied")
    print(f"📁 Test documents folder: {test_docs_dir}")
    return True

if __name__ == "__main__":
    setup_test_documents()
