"""
Script de prueba para validar endpoints de analítica de órdenes.

Ejecuta llamadas HTTP a cada endpoint y muestra los resultados.

Uso:
    python app/scripts/test_orders_analytics.py

Requisito:
    - FastAPI debe estar corriendo en http://localhost:8000
"""

import requests
import json
import sys
from typing import Dict, Any


BASE_URL = "http://localhost:8000/kpis/orders"


def print_header(title: str):
    """Imprime un encabezado formateado."""
    print(f"\n{'='*70}")
    print(f"🔍 {title}")
    print(f"{'='*70}\n")


def print_response(response: requests.Response, endpoint: str):
    """Imprime respuesta formateada."""
    print(f"📡 Endpoint: {endpoint}")
    print(f"⏱️  Status Code: {response.status_code}")
    
    try:
        data = response.json()
        print(f"📊 Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"📄 Response: {response.text}")


def test_kpis():
    """Prueba endpoint KPIs."""
    print_header("Endpoint 1: GET /analytics/orders/kpis")
    
    try:
        endpoint = f"{BASE_URL}/kpis"
        response = requests.get(endpoint)
        print_response(response, endpoint)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ KPIs Extraídos:")
            print(f"   • Total órdenes: {data.get('total_orders')}")
            print(f"   • Tasa entrega: {data.get('delivery_rate')*100:.1f}%")
            print(f"   • Tasa pago exitoso: {data.get('payment_success_rate')*100:.1f}%")
            print(f"   • Ingresos totales: ${data.get('revenue_total'):,.2f}")
            print(f"   • SLA Compliance: {data.get('sla_compliance')*100:.1f}%")
            return True
        else:
            print("❌ Error en endpoint")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_channels():
    """Prueba endpoint Channels."""
    print_header("Endpoint 2: GET /analytics/orders/channels")
    
    try:
        endpoint = f"{BASE_URL}/channels"
        response = requests.get(endpoint)
        print_response(response, endpoint)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Canales:")
            for channel in data.get('channels', []):
                print(f"   • {channel['channel']}: "
                      f"{channel['order_count']} órdenes "
                      f"(${channel['revenue']:,.2f})")
            return True
        else:
            print("❌ Error en endpoint")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_status():
    """Prueba endpoint Status."""
    print_header("Endpoint 3: GET /analytics/orders/status")
    
    try:
        endpoint = f"{BASE_URL}/status"
        response = requests.get(endpoint)
        print_response(response, endpoint)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Estados:")
            for status in data.get('statuses', []):
                print(f"   • {status['status']}: "
                      f"{status['count']} órdenes ({status['percentage_of_total']:.1f}%)")
            return True
        else:
            print("❌ Error en endpoint")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_timeline():
    """Prueba endpoint Timeline."""
    print_header("Endpoint 4: GET /analytics/orders/timeline")
    
    try:
        # Test con días por defecto
        endpoint = f"{BASE_URL}/timeline"
        response = requests.get(endpoint)
        print_response(response, endpoint)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Timeline (últimos 30 días):")
            print(f"   • Período: {data.get('start_date')} a {data.get('end_date')}")
            print(f"   • Total órdenes: {data.get('total_orders')}")
            print(f"   • Datos por día: {len(data.get('timeline', []))} registros")
            
            # Mostrar primeros 3 días
            for point in data.get('timeline', [])[:3]:
                print(f"     - {point['date']}: "
                      f"{point['order_count']} órdenes, "
                      f"${point['revenue']:,.2f}")
            
            return True
        else:
            print("❌ Error en endpoint")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_timeline_custom():
    """Prueba endpoint Timeline con parámetro custom."""
    print_header("Endpoint 4B: GET /analytics/orders/timeline?days=7")
    
    try:
        endpoint = f"{BASE_URL}/timeline?days=7"
        response = requests.get(endpoint)
        print_response(response, endpoint)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Timeline (últimos 7 días):")
            print(f"   • Período: {data.get('start_date')} a {data.get('end_date')}")
            print(f"   • Total órdenes: {data.get('total_orders')}")
            return True
        else:
            print("❌ Error en endpoint")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_health():
    """Prueba endpoint Health."""
    print_header("Endpoint 5: GET /analytics/orders/health")
    
    try:
        endpoint = f"{BASE_URL}/health"
        response = requests.get(endpoint)
        print_response(response, endpoint)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Service Status: {data.get('status')}")
            print(f"   • Órdenes en BD: {data.get('orders_in_database')}")
            return True
        else:
            print("❌ Error en endpoint")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Función principal."""
    
    print("\n" + "="*70)
    print("🧪 TESTING ENDPOINTS DE ANALÍTICA - DOMINIO ORDERS")
    print("="*70)
    print(f"📡 Base URL: {BASE_URL}\n")
    
    # Verificar conexión
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ El servidor no responde correctamente")
            print("   Asegúrate de ejecutar: python main.py\n")
            return 1
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar a http://localhost:8000")
        print("   Asegúrate de ejecutar: python main.py\n")
        return 1
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}\n")
        return 1
    
    # Ejecutar pruebas
    results = []
    
    results.append(("KPIs", test_kpis()))
    results.append(("Channels", test_channels()))
    results.append(("Status", test_status()))
    results.append(("Timeline (30 días)", test_timeline()))
    results.append(("Timeline (7 días)", test_timeline_custom()))
    results.append(("Health", test_health()))
    
    # Resumen
    print_header("RESUMEN DE PRUEBAS")
    
    for endpoint, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {endpoint}")
    
    successful = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n📊 Resultado: {successful}/{total} pruebas exitosas")
    print("="*70 + "\n")
    
    if successful == total:
        print("✅ TODOS LOS ENDPOINTS FUNCIONAN CORRECTAMENTE")
        print("\n💡 Próximos pasos:")
        print("   1. Conéctate desde Power BI o dashboards")
        print("   2. Crea visualizaciones basadas en estos endpoints")
        print("   3. Configura actualizaciones automáticas\n")
        return 0
    else:
        print(f"⚠️  {total - successful} pruebas fallaron")
        print("\n🔧 Debugging:")
        print("   1. Verifica que hay datos en fact_orders")
        print("   2. Ejecuta: python app/scripts/mock_orders_events.py")
        print("   3. Luego: python app/scripts/run_orders_etl.py\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
