"""
Basic tests for the BioNet Fauna Query toolbox.

Note: These tests verify structure and basic functionality but do not require ArcGIS Pro.
Full integration tests require ArcGIS Pro environment.
"""

import json
import urllib.request
import urllib.parse
import sys
import os

# Add current directory to path to import the toolbox
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_bionet_api_availability():
    """Test that the BioNet OData API endpoint is accessible"""
    print("Testing BioNet OData API availability...")
    
    base_url = "https://data.bionet.nsw.gov.au/biosvcapp/odata/SpeciesSightings_CoreData"
    
    # Simple test query - get count
    test_url = f"{base_url}?$top=1&$select=ScientificName"
    
    try:
        req = urllib.request.Request(test_url)
        req.add_header('Accept', 'application/json')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        if 'value' in result:
            print(f"✓ OData API is accessible. Retrieved sample data.")
            return True
        else:
            print(f"✗ Unexpected OData API response: {result}")
            return False
            
    except Exception as e:
        print(f"✗ OData API is not accessible: {str(e)}")
        return False


def test_api_fauna_query():
    """Test querying fauna species from the OData API"""
    print("\nTesting fauna species query...")
    
    base_url = "https://data.bionet.nsw.gov.au/biosvcapp/odata/SpeciesSightings_CoreData"
    
    # Query for mammals using OData syntax
    query_params = {
        "$filter": "Class eq 'Mammalia'",
        "$select": "ScientificName,CommonName,BCActStatus,EPBCActStatus",
        "$top": "10"
    }
    
    query_string = urllib.parse.urlencode(query_params)
    full_url = f"{base_url}?{query_string}"
    
    try:
        req = urllib.request.Request(full_url)
        req.add_header('Accept', 'application/json')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        if 'value' in result:
            records = len(result['value'])
            print(f"✓ Successfully retrieved {records} mammal records")
            
            # Show first record as example
            if records > 0:
                first_record = result['value'][0]
                print(f"  Example: {first_record.get('ScientificName', 'N/A')} "
                      f"({first_record.get('CommonName', 'N/A')})")
                print(f"    BC Act Status: {first_record.get('BCActStatus', 'Not listed')}")
                print(f"    EPBC Act Status: {first_record.get('EPBCActStatus', 'Not listed')}")
            return True
        else:
            print(f"✗ No data in OData API response")
            return False
            
    except Exception as e:
        print(f"✗ Query failed: {str(e)}")
        return False


def test_fauna_groups():
    """Test different fauna group queries using OData"""
    print("\nTesting different fauna groups...")
    
    base_url = "https://data.bionet.nsw.gov.au/biosvcapp/odata/SpeciesSightings_CoreData"
    
    fauna_groups = {
        "Mammals": "Class eq 'Mammalia'",
        "Birds": "Class eq 'Aves'",
        "Reptiles": "Class eq 'Reptilia'",
        "Amphibians": "Class eq 'Amphibia'"
    }
    
    results = {}
    
    for group_name, odata_filter in fauna_groups.items():
        query_params = {
            "$filter": odata_filter,
            "$top": "1",
            "$select": "ScientificName"
        }
        
        query_string = urllib.parse.urlencode(query_params)
        full_url = f"{base_url}?{query_string}"
        
        try:
            req = urllib.request.Request(full_url)
            req.add_header('Accept', 'application/json')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            if 'value' in result and len(result['value']) > 0:
                results[group_name] = 1  # Got at least one record
                print(f"  {group_name}: ✓ Data available")
            else:
                print(f"  {group_name}: No data")
                results[group_name] = 0
                
        except Exception as e:
            print(f"  {group_name}: Error - {str(e)}")
            results[group_name] = 0
    
    # Check if we got results for at least some groups
    success_count = sum(1 for count in results.values() if count > 0)
    if success_count >= 3:
        print(f"✓ Successfully queried {success_count} fauna groups")
        return True
    else:
        print(f"✗ Only {success_count} fauna groups returned data")
        return False


def test_conservation_status_fields():
    """Test that conservation status fields are available in OData"""
    print("\nTesting conservation status fields...")
    
    base_url = "https://data.bionet.nsw.gov.au/biosvcapp/odata/SpeciesSightings_CoreData"
    
    # Query for species with BC Act status using OData syntax
    query_params = {
        "$filter": "BCActStatus ne null and BCActStatus ne ''",
        "$select": "ScientificName,CommonName,BCActStatus,EPBCActStatus",
        "$top": "5"
    }
    
    query_string = urllib.parse.urlencode(query_params)
    full_url = f"{base_url}?{query_string}"
    
    try:
        req = urllib.request.Request(full_url)
        req.add_header('Accept', 'application/json')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        if 'value' in result and len(result['value']) > 0:
            print(f"✓ Found {len(result['value'])} species with BC Act status")
            
            # Show examples
            for i, record in enumerate(result['value'][:3], 1):
                print(f"  {i}. {record.get('ScientificName', 'N/A')}")
                print(f"     BC Act: {record.get('BCActStatus', 'N/A')}")
                print(f"     EPBC Act: {record.get('EPBCActStatus', 'N/A')}")
            
            return True
        else:
            print("✗ No species with conservation status found")
            return False
            
    except Exception as e:
        print(f"✗ Status field test failed: {str(e)}")
        return False


def test_toolbox_structure():
    """Test that the toolbox file has proper structure"""
    print("\nTesting toolbox file structure...")
    
    toolbox_path = os.path.join(os.path.dirname(__file__), "BionetFaunaQuery.pyt")
    
    if not os.path.exists(toolbox_path):
        print(f"✗ Toolbox file not found: {toolbox_path}")
        return False
    
    try:
        # Read the file and check for required components
        with open(toolbox_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_elements = [
            "class Toolbox",
            "class BionetFaunaQueryTool",
            "def getParameterInfo",
            "def execute",
            "BCActStatus",
            "EPBCActStatus",
            "SpeciesSightings_CoreData"
        ]
        
        missing = []
        for element in required_elements:
            if element not in content:
                missing.append(element)
        
        if missing:
            print(f"✗ Missing required elements: {', '.join(missing)}")
            return False
        else:
            print("✓ Toolbox file has proper structure")
            return True
            
    except Exception as e:
        print(f"✗ Error reading toolbox file: {str(e)}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("=" * 60)
    print("NSW BioNet Fauna Query Toolbox Tests (OData API)")
    print("=" * 60)
    
    tests = [
        ("Toolbox Structure", test_toolbox_structure),
        ("API Availability", test_bionet_api_availability),
        ("Fauna Query", test_api_fauna_query),
        ("Fauna Groups", test_fauna_groups),
        ("Conservation Status", test_conservation_status_fields)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ Test '{test_name}' raised exception: {str(e)}")
            results[test_name] = False
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
