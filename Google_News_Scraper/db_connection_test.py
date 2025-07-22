#!/usr/bin/env python3
# db_connection_test.py - Test database connections

import sys
import traceback
from config_loader import ConfigLoader

def test_config_loader():
    """Test if config loader works"""
    try:
        print("🧪 Testing ConfigLoader...")
        config_loader = ConfigLoader()
        print("✅ ConfigLoader initialized successfully")
        
        supabase_config = config_loader.get_supabase_config()
        print(f"✅ Supabase config loaded: {supabase_config}")
        
        return config_loader, supabase_config
    except Exception as e:
        print(f"❌ ConfigLoader failed: {e}")
        traceback.print_exc()
        return None, None

def test_supabase_direct():
    """Test direct Supabase connection"""
    try:
        print("\n🧪 Testing direct Supabase connection...")
        
        config_loader, supabase_config = test_config_loader()
        if not config_loader:
            return False
            
        # Try to import and connect to Supabase directly
        from supabase import create_client, Client
        
        url = supabase_config['url']
        key = supabase_config['key']
        
        print(f"🔗 Connecting to: {url}")
        print(f"🔑 Using key: {key[:20]}...")
        
        supabase: Client = create_client(url, key)
        
        # Try a simple query to test connection
        table_name = supabase_config.get('table_name', 'Soup_Dedupe')
        print(f"📊 Testing query on table: {table_name}")
        
        # Simple count query to test connection
        response = supabase.table(table_name).select("*", count="exact").limit(1).execute()
        
        print(f"✅ Supabase connection successful!")
        print(f"📈 Query response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        traceback.print_exc()
        return False

def test_soup_pusher():
    """Test soup_pusher.py specifically"""
    try:
        print("\n🧪 Testing SoupPusher...")
        
        config_loader = ConfigLoader()
        supabase_config = config_loader.get_supabase_config()
        
        # Try to import and initialize SoupPusher
        from soup_pusher import SoupPusher
        
        soup_pusher = SoupPusher(supabase_config)
        print("✅ SoupPusher initialized")
        
        # Test the connection method that's failing
        if hasattr(soup_pusher, 'test_connection'):
            connection_result = soup_pusher.test_connection()
            print(f"🔍 test_connection() result: {connection_result}")
            return connection_result
        else:
            print("⚠️ SoupPusher doesn't have test_connection() method")
            return False
            
    except Exception as e:
        print(f"❌ SoupPusher failed: {e}")
        traceback.print_exc()
        return False

def main():
    print("🚀 Database Connection Diagnostics")
    print("=" * 50)
    
    # Test 1: Config loader
    config_success = test_config_loader()[0] is not None
    
    # Test 2: Direct Supabase
    if config_success:
        supabase_success = test_supabase_direct()
    else:
        supabase_success = False
    
    # Test 3: SoupPusher
    if config_success:
        soup_pusher_success = test_soup_pusher()
    else:
        soup_pusher_success = False
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY:")
    print(f"ConfigLoader: {'✅' if config_success else '❌'}")
    print(f"Direct Supabase: {'✅' if supabase_success else '❌'}")
    print(f"SoupPusher: {'✅' if soup_pusher_success else '❌'}")
    
    if all([config_success, supabase_success, soup_pusher_success]):
        print("\n🎉 All connections working! The mesh scraper should work now.")
    else:
        print("\n🔧 Issues found - check the errors above for details.")

if __name__ == "__main__":
    main()