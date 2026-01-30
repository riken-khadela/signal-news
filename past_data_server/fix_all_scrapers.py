import re
from pathlib import Path

# List of files to fix
files_to_fix = [
    "advance_materials.py", "betakit.py", "canary.py", "cleanenergywire.py",
    "cleantechnica.py", "complianceweek.py", "crunchbase.py", "fortune.py",
    "healthcareasiamagazine.py", "healthtechasia.py", "healthtechmagazine.py",
    "intelligence360.py", "mining.py", "mobihealthnews.py", "neno_werk.py",
    "next_web.py", "phocuswire.py", "quantam_insider.py", "renewableenergyworld.py",
    "rigzone.py", "tech_crunch.py", "tech_eu.py", "wired.py", "worldoil.py", "zdnet.py"
]

base_dir = Path(__file__).parent

for filename in files_to_fix:
    filepath = base_dir / filename
    if not filepath.exists():
        print(f"❌ Skipping {filename} - file not found")
        continue
    
    try:
        content = filepath.read_text(encoding='utf-8')
        
        # Pattern to find the problematic line
        old_pattern = r'(\s+)self\.page_index = self\.get_new_page_index\(self\.page_index, self\.grid_details if hasattr\(self, \'grid_details\'\) else \[\]\)'
        
        # Check if file has the old pattern
        if not re.search(old_pattern, content):
            print(f"⏭️  Skipping {filename} - pattern not found")
            continue
        
        # Replace with simple increment
        content = re.sub(old_pattern, r'\1self.page_index += 1', content)
        
        # Find the pattern for adding the call at the end
        # Look for the check_db_grid() block and add after it
        pattern_to_add_after = r'(else:\s+self\.logger\.warning\(f"No articles found on page \{self\.page_index\}"\))'
        
        if re.search(pattern_to_add_after, content):
            replacement = r'\1\n                \n                # Get next page index AFTER processing current page\n                self.page_index = self.get_new_page_index(self.page_index, self.grid_details)'
            content = re.sub(pattern_to_add_after, replacement, content)
            
            filepath.write_text(content, encoding='utf-8')
            print(f"✅ Fixed {filename}")
        else:
            print(f"⚠️  {filename} - couldn't find insertion point")
            
    except Exception as e:
        print(f"❌ Error fixing {filename}: {e}")

print("\n✅ Done!")
