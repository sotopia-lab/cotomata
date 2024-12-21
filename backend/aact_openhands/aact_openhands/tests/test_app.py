import unittest
from typing import Dict, Any
import requests

class TestFlaskApp(unittest.TestCase):
    base_url: str
    headers: Dict[str, str]

    def setUp(self) -> None:
        """Set up test case - runs before each test"""
        self.base_url = 'http://localhost:5000'
        self.headers = {'Content-Type': 'application/json'}

    def test_01_initialize_endpoint(self) -> None:
        """Test the initialize endpoint with valid data"""
        payload: Dict[str, Any] = {
            "output_channels": ["Runtime1234:Agent"],
            "input_channels": ["Agent:Runtime1234"],
            "node_name": "runtime",
            "modal_session_id": "arpan"
        }
        
        response = requests.post(
            f'{self.base_url}/initialize',
            json=payload,
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'initialized')

    def test_02_initialize_with_invalid_data(self) -> None:
        """Test the initialize endpoint with invalid data"""
        invalid_payload: Dict[str, Any] = {
            "output_channels": ["Runtime1234:Agent"]
            # Missing other required fields
        }
        
        response = requests.post(
            f'{self.base_url}/initialize',
            json=invalid_payload,
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_03_status_endpoint(self) -> None:
        """Test the status endpoint"""
        response = requests.get(f'{self.base_url}/status')
        
        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertIn('status', status_data)
        self.assertIn('output', status_data)
        self.assertIn('success', status_data)

    def test_04_health_endpoint(self) -> None:
        """Test the health endpoint"""
        response = requests.get(f'{self.base_url}/health')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_05_stop_endpoint(self) -> None:
        """Test the stop endpoint"""
        response = requests.post(f'{self.base_url}/stop')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'stopped')

if __name__ == '__main__':
    unittest.main(verbosity=2) 