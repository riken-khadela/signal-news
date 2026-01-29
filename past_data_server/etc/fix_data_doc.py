def fix_data_doc(data_doc):
    """
    Ensures all required keys exist in the data_doc dictionary.
    If any key is missing, it will be added with default values.
    
    Args:
        data_doc (dict): The input dictionary to validate and fix
        
    Returns:
        dict: A properly structured data_doc with all required keys
    """
    # Define the template structure
    template = {
        "author": "",
        "image": "",
        "url": "",
        "title": "",
        "time": "",
        "description": {
            "summary": "",
            "details": ""
        }
    }
    
    # Create a fixed data_doc starting with the template
    fixed_doc = {}
    
    # Check and add top-level keys
    for key in ["author", "image", "url", "title", "time"]:
        fixed_doc[key] = data_doc.get(key, template[key])
    
    # Handle the nested 'description' key
    if "description" in data_doc and isinstance(data_doc["description"], dict):
        fixed_doc["description"] = {
            "summary": data_doc["description"].get("summary", ""),
            "details": data_doc["description"].get("details", "")
        }
    else:
        fixed_doc["description"] = template["description"].copy()
    
    return fixed_doc


# Example usage:
if __name__ == "__main__":
    # Test case 1: Missing some keys
    incomplete_doc = {
        "title": "Sample News",
        "url": "https://example.com",
        "description": {
            "summary": "A brief summary"
        }
    }
    
    print("Test 1 - Incomplete document:")
    print(fix_data_doc(incomplete_doc))
    print()
    
    # Test case 2: Missing description entirely
    no_description = {
        "title": "Another News",
        "author": "John Doe"
    }
    
    print("Test 2 - No description:")
    print(fix_data_doc(no_description))
    print()
    
    # Test case 3: Complete document
    complete_doc = {
        "author": "Jane Smith",
        "image": "https://example.com/image.jpg",
        "url": "https://example.com/article",
        "title": "Complete Article",
        "time": "2026-01-29",
        "description": {
            "summary": "Summary text",
            "details": "Detailed text"
        }
    }
    
    print("Test 3 - Complete document:")
    print(fix_data_doc(complete_doc))
