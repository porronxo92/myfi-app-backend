#!/usr/bin/env python
"""
Script para verificar configuración de CORS en el backend
Realiza peticiones HTTP simples para verificar headers de CORS
"""

import requests
import json
from typing import Dict, List

def check_cors(url: str, origin: str = "http://localhost:4200") -> Dict:
    """Verificar headers de CORS en una petición OPTIONS"""
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type"
    }
    
    try:
        response = requests.options(url, headers=headers, timeout=5)
        
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
            "Access-Control-Expose-Headers": response.headers.get("Access-Control-Expose-Headers"),
            "Access-Control-Max-Age": response.headers.get("Access-Control-Max-Age"),
        }
        
        return {
            "status": response.status_code,
            "success": response.status_code == 200,
            "cors_headers": cors_headers,
            "other_headers": {k: v for k, v in response.headers.items() 
                            if not k.startswith("Access-Control") and k not in ["Content-Type", "Date", "Server"]}
        }
    except Exception as e:
        return {
            "status": None,
            "success": False,
            "error": str(e),
            "cors_headers": {}
        }


def main():
    """Ejecutar pruebas de CORS"""
    backend_url = "http://localhost:8000"
    frontend_origin = "http://localhost:4200"
    
    endpoints = [
        "/api/users/login",
        "/api/investments",
        "/api/investments/search",
        "/api/investments/quote",
        "/api/accounts",
        "/api/categories",
        "/api/transactions",
        "/api/analytics/summary",
    ]
    
    print("=" * 80)
    print("CORS Configuration Verification")
    print("=" * 80)
    print(f"Backend URL: {backend_url}")
    print(f"Frontend Origin: {frontend_origin}\n")
    
    all_passed = True
    
    for endpoint in endpoints:
        print(f"\nChecking: {endpoint}")
        print("-" * 80)
        
        result = check_cors(f"{backend_url}{endpoint}", frontend_origin)
        
        if result["success"]:
            print(f"✅ Status: {result['status']}")
            cors = result["cors_headers"]
            
            checks = [
                ("Allow Origin", cors["Access-Control-Allow-Origin"], frontend_origin),
                ("Allow Credentials", cors["Access-Control-Allow-Credentials"], "true"),
                ("Allow Methods", cors["Access-Control-Allow-Methods"], None),
                ("Allow Headers", cors["Access-Control-Allow-Headers"], None),
                ("Max Age", cors["Access-Control-Max-Age"], None),
            ]
            
            for check_name, header_value, expected in checks:
                if header_value:
                    if expected:
                        status = "✓" if expected in str(header_value) else "✗"
                        print(f"  {status} {check_name}: {header_value}")
                        if expected not in str(header_value):
                            all_passed = False
                    else:
                        print(f"  ✓ {check_name}: {header_value}")
                else:
                    print(f"  ✗ {check_name}: MISSING")
                    all_passed = False
        else:
            print(f"❌ Failed to connect: {result.get('error')}")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ All CORS checks passed!")
    else:
        print("❌ Some CORS checks failed. Review the output above.")
    print("=" * 80)


if __name__ == "__main__":
    main()
