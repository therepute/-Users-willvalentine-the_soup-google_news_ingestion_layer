#!/usr/bin/env python3
"""
Test script to verify the new standardized ID format for Google Alerts
"""

import sys
import time
from soup_pusher import IDGenerator

def test_id_generation():
    """Test the new ID generation format"""
    print("🧪 Testing new standardized ID format for Google Alerts...")
    
    # Create ID generator
    id_gen = IDGenerator()
    
    # Generate several IDs quickly
    ids = []
    for i in range(10):
        generated_id = id_gen.generate_id()
        ids.append(generated_id)
        print(f"Generated ID {i+1}: {generated_id}")
        
        # Small delay to test counter increment
        if i == 4:
            time.sleep(1.1)  # Cross second boundary
    
    # Verify format
    print("\n🔍 Verifying ID format compliance...")
    all_valid = True
    
    for i, test_id in enumerate(ids):
        parts = test_id.split('_')
        
        # Check format: GA_YYYYMMDD_HHMMSS_XXXXXX
        if len(parts) != 4:
            print(f"❌ ID {i+1} has wrong number of parts: {test_id}")
            all_valid = False
            continue
            
        prefix, date_part, time_part, counter_part = parts
        
        # Check prefix
        if prefix != 'GA':
            print(f"❌ ID {i+1} has wrong prefix: {prefix} (should be GA)")
            all_valid = False
            
        # Check date format (YYYYMMDD)
        if len(date_part) != 8 or not date_part.isdigit():
            print(f"❌ ID {i+1} has invalid date format: {date_part}")
            all_valid = False
            
        # Check time format (HHMMSS)
        if len(time_part) != 6 or not time_part.isdigit():
            print(f"❌ ID {i+1} has invalid time format: {time_part}")
            all_valid = False
            
        # Check counter format (6 digits)
        if len(counter_part) != 6 or not counter_part.isdigit():
            print(f"❌ ID {i+1} has invalid counter format: {counter_part}")
            all_valid = False
            
        if all([
            prefix == 'GA',
            len(date_part) == 8 and date_part.isdigit(),
            len(time_part) == 6 and time_part.isdigit(), 
            len(counter_part) == 6 and counter_part.isdigit()
        ]):
            print(f"✅ ID {i+1} is valid: {test_id}")
    
    # Check for duplicates
    if len(set(ids)) != len(ids):
        print("❌ Duplicate IDs detected!")
        all_valid = False
    else:
        print("✅ No duplicate IDs found")
    
    # Final result
    if all_valid:
        print("\n🎉 ALL TESTS PASSED! ID format is compliant.")
        return True
    else:
        print("\n💥 TESTS FAILED! ID format needs fixing.")
        return False

if __name__ == "__main__":
    success = test_id_generation()
    sys.exit(0 if success else 1) 