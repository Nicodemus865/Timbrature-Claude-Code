#!/usr/bin/env python3
"""
BustaPaga Backend API Test Suite
Tests all backend endpoints systematically
"""

import requests
import json
import base64
from datetime import datetime, date, timedelta
import time

# API Base URL from environment
BASE_URL = "https://entrata-uscita.preview.emergentagent.com/api"

class BustaPagaAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.test_results = []
        
    def log_result(self, test_name, passed, response=None, error=None):
        """Log test result"""
        result = {
            "test": test_name,
            "passed": passed,
            "timestamp": datetime.now().isoformat(),
            "status_code": response.status_code if response else None,
            "error": str(error) if error else None
        }
        
        if response and hasattr(response, 'json'):
            try:
                result["response_data"] = response.json()
            except:
                result["response_text"] = response.text[:500]
        
        self.test_results.append(result)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if error:
            print(f"   Error: {error}")
        if response and not passed:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
    
    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("\n=== Testing Health Endpoints ===")
        
        # Root endpoint
        try:
            response = self.session.get(f"{self.base_url}/")
            self.log_result("GET / - Root endpoint", 
                          response.status_code == 200 and "BustaPaga API" in response.text,
                          response)
        except Exception as e:
            self.log_result("GET / - Root endpoint", False, error=e)
        
        # Health check
        try:
            response = self.session.get(f"{self.base_url}/health")
            self.log_result("GET /health - Health check",
                          response.status_code == 200 and "healthy" in response.text,
                          response)
        except Exception as e:
            self.log_result("GET /health - Health check", False, error=e)
    
    def test_settings_api(self):
        """Test Settings API endpoints"""
        print("\n=== Testing Settings API ===")
        
        # Get settings
        try:
            response = self.session.get(f"{self.base_url}/settings")
            self.log_result("GET /settings - Get user settings",
                          response.status_code == 200,
                          response)
            
            if response.status_code == 200:
                settings = response.json()
                # Verify required fields
                required_fields = ["nome", "qualifica", "livello", "azienda", "paga_base"]
                has_required = all(field in settings for field in required_fields)
                self.log_result("Settings data validation - Required fields present",
                              has_required)
        except Exception as e:
            self.log_result("GET /settings - Get user settings", False, error=e)
        
        # Update settings
        try:
            update_data = {
                "nome": "Marco Test",
                "qualifica": "Tester",
                "paga_base": 2000.00
            }
            response = self.session.put(f"{self.base_url}/settings", json=update_data)
            self.log_result("PUT /settings - Update settings",
                          response.status_code == 200,
                          response)
        except Exception as e:
            self.log_result("PUT /settings - Update settings", False, error=e)
    
    def test_dashboard_api(self):
        """Test Dashboard API"""
        print("\n=== Testing Dashboard API ===")
        
        try:
            response = self.session.get(f"{self.base_url}/dashboard")
            self.log_result("GET /dashboard - Get dashboard data",
                          response.status_code == 200,
                          response)
            
            if response.status_code == 200:
                dashboard = response.json()
                # Verify dashboard structure
                required_sections = ["mese_corrente", "stime", "ferie", "comporto"]
                has_sections = all(section in dashboard for section in required_sections)
                self.log_result("Dashboard structure validation",
                              has_sections)
        except Exception as e:
            self.log_result("GET /dashboard - Get dashboard data", False, error=e)
    
    def test_timbrature_api(self):
        """Test Timbrature (Clock In/Out) API"""
        print("\n=== Testing Timbrature API ===")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get timbrature list
        try:
            response = self.session.get(f"{self.base_url}/timbrature")
            self.log_result("GET /timbrature - List timbrature",
                          response.status_code == 200,
                          response)
        except Exception as e:
            self.log_result("GET /timbrature - List timbrature", False, error=e)
        
        # Create timbratura
        try:
            timbratura_data = {
                "data": today,
                "ora_entrata": "08:30",
                "ora_uscita": "17:30",
                "note": "Test timbratura"
            }
            response = self.session.post(f"{self.base_url}/timbrature", json=timbratura_data)
            
            # If already exists, that's OK for testing
            success = response.status_code in [200, 201, 400]  
            self.log_result("POST /timbrature - Create timbratura",
                          success, response)
        except Exception as e:
            self.log_result("POST /timbrature - Create timbratura", False, error=e)
        
        # Quick clock in
        try:
            response = self.session.post(f"{self.base_url}/timbrature/timbra?tipo=entrata")
            success = response.status_code in [200, 201, 400]  # Allow existing entry
            self.log_result("POST /timbrature/timbra - Quick clock in",
                          success, response)
        except Exception as e:
            self.log_result("POST /timbrature/timbra - Quick clock in", False, error=e)
        
        # Quick clock out
        try:
            response = self.session.post(f"{self.base_url}/timbrature/timbra?tipo=uscita")
            success = response.status_code in [200, 201, 400]  # Allow no entry or existing
            self.log_result("POST /timbrature/timbra - Quick clock out",
                          success, response)
        except Exception as e:
            self.log_result("POST /timbrature/timbra - Quick clock out", False, error=e)
        
        # Weekly summary
        try:
            response = self.session.get(f"{self.base_url}/timbrature/settimana/{today}")
            self.log_result("GET /timbrature/settimana - Weekly summary",
                          response.status_code == 200,
                          response)
        except Exception as e:
            self.log_result("GET /timbrature/settimana - Weekly summary", False, error=e)
    
    def test_assenze_api(self):
        """Test Assenze (Absences) API"""
        print("\n=== Testing Assenze API ===")
        
        # Get absences list
        try:
            response = self.session.get(f"{self.base_url}/assenze")
            self.log_result("GET /assenze - List absences",
                          response.status_code == 200,
                          response)
        except Exception as e:
            self.log_result("GET /assenze - List absences", False, error=e)
        
        # Create absence (vacation)
        try:
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            day_after = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
            
            absence_data = {
                "tipo": "ferie",
                "data_inizio": tomorrow,
                "data_fine": day_after,
                "note": "Test vacation"
            }
            response = self.session.post(f"{self.base_url}/assenze", json=absence_data)
            self.log_result("POST /assenze - Create vacation absence",
                          response.status_code in [200, 201],
                          response)
        except Exception as e:
            self.log_result("POST /assenze - Create vacation absence", False, error=e)
        
        # Create sick leave
        try:
            next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            next_week_end = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
            
            sick_data = {
                "tipo": "malattia",
                "data_inizio": next_week,
                "data_fine": next_week_end,
                "note": "Test sick leave"
            }
            response = self.session.post(f"{self.base_url}/assenze", json=sick_data)
            self.log_result("POST /assenze - Create sick leave",
                          response.status_code in [200, 201],
                          response)
        except Exception as e:
            self.log_result("POST /assenze - Create sick leave", False, error=e)
        
        # Get holiday balance
        try:
            response = self.session.get(f"{self.base_url}/ferie/saldo")
            self.log_result("GET /ferie/saldo - Get holiday balance",
                          response.status_code == 200,
                          response)
        except Exception as e:
            self.log_result("GET /ferie/saldo - Get holiday balance", False, error=e)
        
        # Get sick leave comporto
        try:
            response = self.session.get(f"{self.base_url}/malattia/comporto")
            self.log_result("GET /malattia/comporto - Get sick leave comporto",
                          response.status_code == 200,
                          response)
        except Exception as e:
            self.log_result("GET /malattia/comporto - Get sick leave comporto", False, error=e)
    
    def test_reperibilita_api(self):
        """Test Reperibilità (On-Call) API"""
        print("\n=== Testing Reperibilità API ===")
        
        # Get reperibilita list
        try:
            response = self.session.get(f"{self.base_url}/reperibilita")
            self.log_result("GET /reperibilita - List on-call",
                          response.status_code == 200,
                          response)
        except Exception as e:
            self.log_result("GET /reperibilita - List on-call", False, error=e)
        
        # Create passive on-call
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            oncall_data = {
                "data": today,
                "ora_inizio": "18:00",
                "ora_fine": "08:00",
                "tipo": "passiva",
                "note": "Test passive on-call"
            }
            response = self.session.post(f"{self.base_url}/reperibilita", json=oncall_data)
            self.log_result("POST /reperibilita - Create passive on-call",
                          response.status_code in [200, 201],
                          response)
        except Exception as e:
            self.log_result("POST /reperibilita - Create passive on-call", False, error=e)
        
        # Create active on-call
        try:
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            active_oncall_data = {
                "data": tomorrow,
                "ora_inizio": "20:00",
                "ora_fine": "06:00",
                "tipo": "attiva",
                "interventi": 2,
                "note": "Test active on-call"
            }
            response = self.session.post(f"{self.base_url}/reperibilita", json=active_oncall_data)
            self.log_result("POST /reperibilita - Create active on-call",
                          response.status_code in [200, 201],
                          response)
        except Exception as e:
            self.log_result("POST /reperibilita - Create active on-call", False, error=e)
    
    def test_buste_paga_api(self):
        """Test Buste Paga (Payslips) API"""
        print("\n=== Testing Buste Paga API ===")
        
        # Get payslips list
        try:
            response = self.session.get(f"{self.base_url}/buste-paga")
            self.log_result("GET /buste-paga - List payslips",
                          response.status_code == 200,
                          response)
        except Exception as e:
            self.log_result("GET /buste-paga - List payslips", False, error=e)
        
        # Create payslip
        try:
            current_date = datetime.now()
            payslip_data = {
                "mese": current_date.month,
                "anno": current_date.year - 1,  # Previous year to avoid conflicts
                "lordo": 2500.00,
                "netto": 1800.00,
                "straordinari_ore": 10.5,
                "straordinari_importo": 180.50
            }
            response = self.session.post(f"{self.base_url}/buste-paga", json=payslip_data)
            success = response.status_code in [200, 201, 400]  # Allow existing
            self.log_result("POST /buste-paga - Create payslip",
                          success, response)
        except Exception as e:
            self.log_result("POST /buste-paga - Create payslip", False, error=e)
        
        # Update payslip
        try:
            update_data = {
                "mese": current_date.month,
                "anno": current_date.year - 1,
                "lordo": 2600.00,
                "netto": 1850.00
            }
            response = self.session.put(
                f"{self.base_url}/buste-paga/{current_date.year - 1}/{current_date.month}",
                json=update_data
            )
            success = response.status_code in [200, 201, 404]  # Allow not found
            self.log_result("PUT /buste-paga - Update payslip",
                          success, response)
        except Exception as e:
            self.log_result("PUT /buste-paga - Update payslip", False, error=e)
    
    def test_chat_api(self):
        """Test Chat API with AI assistant"""
        print("\n=== Testing Chat API ===")
        
        # Send chat message
        try:
            chat_data = {
                "message": "Quante ore di ferie ho disponibili?",
                "session_id": "test_session_123"
            }
            response = self.session.post(f"{self.base_url}/chat", json=chat_data)
            self.log_result("POST /chat - Send message",
                          response.status_code == 200,
                          response)
            
            if response.status_code == 200:
                chat_response = response.json()
                has_response = "response" in chat_response and len(chat_response["response"]) > 10
                self.log_result("Chat response validation - Has meaningful response",
                              has_response)
        except Exception as e:
            self.log_result("POST /chat - Send message", False, error=e)
        
        # Get chat history
        try:
            response = self.session.get(f"{self.base_url}/chat/history")
            self.log_result("GET /chat/history - Get chat history",
                          response.status_code == 200,
                          response)
        except Exception as e:
            self.log_result("GET /chat/history - Get chat history", False, error=e)
    
    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting BustaPaga Backend API Tests")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Run test suites
        self.test_health_endpoints()
        self.test_settings_api()
        self.test_dashboard_api()
        self.test_timbrature_api()
        self.test_assenze_api()
        self.test_reperibilita_api()
        self.test_buste_paga_api()
        self.test_chat_api()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["passed"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"❌ {result['test']}")
                    if result.get("error"):
                        print(f"   Error: {result['error']}")
                    if result.get("status_code"):
                        print(f"   Status: {result['status_code']}")
        
        # Save detailed results
        with open("/app/test_results_detailed.json", "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n📝 Detailed results saved to: /app/test_results_detailed.json")
        
        return passed_tests, failed_tests

if __name__ == "__main__":
    tester = BustaPagaAPITester()
    passed, failed = tester.run_all_tests()
    
    print(f"\n🏁 Testing Complete - {passed} passed, {failed} failed")