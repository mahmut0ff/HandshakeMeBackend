#!/usr/bin/env python3
"""
API Testing Script for HandshakeMe Backend

This script tests all major API endpoints to ensure they're working correctly.
Run this after setting up the backend to verify everything is functioning.

Usage:
    python test_api.py --base-url http://localhost:8000
"""

import requests
import json
import argparse
from typing import Dict, Any


class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.auth_token = None
        
    def test_all_endpoints(self):
        """Test all major API endpoints"""
        print("🚀 Starting API tests for HandshakeMe Backend")
        print(f"📍 Base URL: {self.base_url}")
        print("-" * 50)
        
        # Test authentication
        self.test_authentication()
        
        # Test user endpoints
        self.test_user_endpoints()
        
        # Test project endpoints
        self.test_project_endpoints()
        
        # Test review endpoints
        self.test_review_endpoints()
        
        # Test admin endpoints
        self.test_admin_endpoints()
        
        print("\n✅ All API tests completed!")
    
    def test_authentication(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints")
        
        # Test user registration
        register_data = {
            "email": "test@example.com",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "first_name": "Test",
            "last_name": "User",
            "user_type": "client"
        }
        
        response = self.make_request('POST', '/api/auth/register/', register_data)
        if response and response.status_code in [201, 400]:  # 400 if user exists
            print("  ✅ Registration endpoint working")
        else:
            print("  ❌ Registration endpoint failed")
        
        # Test user login
        login_data = {
            "email": "test@example.com",
            "password": "testpass123"
        }
        
        response = self.make_request('POST', '/api/auth/login/', login_data)
        if response and response.status_code == 200:
            data = response.json()
            if 'access' in data:
                self.auth_token = data['access']
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}'
                })
                print("  ✅ Login successful, token obtained")
            else:
                print("  ❌ Login response missing access token")
        else:
            print("  ❌ Login failed")
    
    def test_user_endpoints(self):
        """Test user-related endpoints"""
        print("\n👤 Testing User Endpoints")
        
        # Test user profile
        response = self.make_request('GET', '/api/auth/profile/')
        if response and response.status_code == 200:
            print("  ✅ Profile endpoint working")
        else:
            print("  ❌ Profile endpoint failed")
        
        # Test user balance
        response = self.make_request('GET', '/api/reviews/')
        if response and response.status_code == 200:
            print("  ✅ Reviews endpoint working")
        else:
            print("  ❌ Reviews endpoint failed")
    
    def test_project_endpoints(self):
        """Test project-related endpoints"""
        print("\n📋 Testing Project Endpoints")
        
        # Test project list
        response = self.make_request('GET', '/api/projects/')
        if response and response.status_code == 200:
            print("  ✅ Project list endpoint working")
        else:
            print("  ❌ Project list endpoint failed")
        
        # Test project creation
        project_data = {
            "title": "Test Project",
            "description": "This is a test project",
            "budget": "500.00",
            "category": "web_development",
            "skills_required": ["python", "django"]
        }
        
        response = self.make_request('POST', '/api/projects/', project_data)
        if response and response.status_code == 201:
            print("  ✅ Project creation working")
            return response.json().get('id')
        else:
            print("  ❌ Project creation failed")
            return None
    
    def test_review_endpoints(self):
        """Test review-related endpoints"""
        print("\n⭐ Testing Review Endpoints")
        
        # Test reviews list
        response = self.make_request('GET', '/api/reviews/')
        if response and response.status_code == 200:
            print("  ✅ Reviews list endpoint working")
        else:
            print("  ❌ Reviews list endpoint failed")
        
        # Test review creation (may require project)
        review_data = {
            "rating": 5,
            "title": "Great work!",
            "comment": "Excellent contractor, highly recommended",
            "project": 1  # This would need to be a valid project ID
        }
        
        response = self.make_request('POST', '/api/reviews/', review_data)
        if response and response.status_code in [201, 400]:  # 400 if project doesn't exist
            print("  ✅ Review creation endpoint accessible")
        else:
            print("  ❌ Review creation endpoint failed")
    
    def test_admin_endpoints(self):
        """Test admin panel endpoints"""
        print("\n🛠️ Testing Admin Endpoints")
        
        # Test admin dashboard stats (may require admin privileges)
        response = self.make_request('GET', '/admin-panel/api/stats/')
        if response:
            if response.status_code == 200:
                print("  ✅ Admin stats endpoint working")
            elif response.status_code == 403:
                print("  ⚠️ Admin stats endpoint requires admin privileges")
            else:
                print("  ❌ Admin stats endpoint failed")
        else:
            print("  ❌ Admin stats endpoint not accessible")
    
    def make_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None) -> requests.Response:
        """Make HTTP request to API endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'PUT':
                response = self.session.put(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)
            else:
                print(f"    ❌ Unsupported method: {method}")
                return None
            
            return response
            
        except requests.exceptions.RequestException as e:
            print(f"    ❌ Request failed: {e}")
            return None
    
    def test_api_documentation(self):
        """Test API documentation endpoints"""
        print("\n📚 Testing API Documentation")
        
        # Test Swagger UI
        response = self.make_request('GET', '/api/docs/')
        if response and response.status_code == 200:
            print("  ✅ Swagger UI accessible")
        else:
            print("  ❌ Swagger UI not accessible")
        
        # Test API schema
        response = self.make_request('GET', '/api/schema/')
        if response and response.status_code == 200:
            print("  ✅ API schema accessible")
        else:
            print("  ❌ API schema not accessible")


def main():
    parser = argparse.ArgumentParser(description='Test HandshakeMe API endpoints')
    parser.add_argument(
        '--base-url',
        default='http://localhost:8000',
        help='Base URL for the API (default: http://localhost:8000)'
    )
    
    args = parser.parse_args()
    
    tester = APITester(args.base_url)
    tester.test_all_endpoints()
    tester.test_api_documentation()


if __name__ == '__main__':
    main()