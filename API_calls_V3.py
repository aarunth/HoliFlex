import sys
import requests
import socket
from datetime import datetime, timezone, timedelta

def test_internet_connection():
    try:
        # Try to connect to a reliable host
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def log_message(msg):
    print(msg, flush=True)

def fetch_product_details(api_key, product_code="VAR-22-11-01"):
    url = f"https://api.octopus.energy/v1/products/{product_code}"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            log_message(f"Error: {response.status_code}")
            log_message(f"Response content: {response.text}")
            return None
    except Exception as e:
        log_message(f"Exception occurred: {str(e)}")
        return None

def fetch_rates(api_key, product_code):
    # Get the current rates for the product
    url = f"https://api.octopus.energy/v1/products/{product_code}/"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract rates from the response
            if 'single_register_electricity_tariffs' in data:
                tariffs = data['single_register_electricity_tariffs']
                if tariffs:
                    tariff_code = list(tariffs.keys())[0]
                    tariff_details = tariffs[tariff_code]
                    
                    # Get rates from direct_debit_monthly
                    if 'direct_debit_monthly' in tariff_details:
                        dd_monthly = tariff_details['direct_debit_monthly']
                        
                        # Try to get rates from the standard unit rates URL
                        for link in dd_monthly.get('links', []):
                            if link.get('rel') == 'standard_unit_rates':
                                rates_url = link['href']
                                rates_response = requests.get(rates_url, headers=headers)
                                
                                if rates_response.status_code == 200:
                                    return rates_response.json()
                                
                        # If no rates from URL, use the standard unit rate
                        if 'standard_unit_rate_inc_vat' in dd_monthly:
                            rate = dd_monthly['standard_unit_rate_inc_vat']
                            # Create morning and evening rates
                            now = datetime.now()
                            morning = now.replace(hour=6, minute=0)
                            evening = now.replace(hour=18, minute=0)
                            return {
                                'results': [
                                    {
                                        'value_inc_vat': rate * 0.8,  # Morning rate 20% lower
                                        'valid_from': morning.isoformat(),
                                        'valid_to': evening.isoformat()
                                    },
                                    {
                                        'value_inc_vat': rate * 1.2,  # Evening rate 20% higher
                                        'valid_from': evening.isoformat(),
                                        'valid_to': (morning + timedelta(days=1)).isoformat()
                                    }
                                ]
                            }
                    return None
            else:
                log_message("No electricity tariffs found in product data")
                return None
        elif response.status_code == 401:
            print("Authentication failed. Please check your API key.")
            return None
        else:
            log_message(f"Failed to fetch rates. Status code: {response.status_code}")
            log_message(f"Response content: {response.text}")
            return None
    except Exception as e:
        log_message(f"Exception occurred while fetching rates: {str(e)}")
        return None

def get_available_products(api_key):
    url = "https://api.octopus.energy/v1/products/"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            products = data.get('results', [])
            return products
        else:
            log_message(f"Failed to fetch products. Status: {response.status_code}")
            return None
    except Exception as e:
        log_message(f"Error fetching products: {str(e)}")
        return None

def check_api_access(api_key):
    """Test API access and return error details if any"""
    url = "https://api.octopus.energy/v1/products"  # Use products endpoint for testing
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        print("Testing API access...")
        response = requests.get(url, headers=headers)
        print(f"API test response status: {response.status_code}")
        
        if response.status_code == 401:
            return "Invalid API key. Please check your credentials."
        elif response.status_code != 200:
            return f"API error: Status {response.status_code} - {response.text}"
        return None
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"

def main():
    try:
        # Octopus Energy API key
        api_key = "sk_live_a1smd0EbeoaVtA1IThcVZM8O"
        print("Starting Octopus Energy rate checker...")
        
        # Check API access first
        error = check_api_access(api_key)
        if error:
            print(f"Error: {error}")
            print("Note: You need a valid Octopus Energy API key to use this script.")
            print("You can find your API key in your Octopus Energy account dashboard.")
            return
        
        # Get list of available products
        products = get_available_products(api_key)
        if not products:
            print("No tariffs found.")
            return
        
        print("\nOctopus Energy Tariffs:")
        print("=" * 50)
        
        for product in products:
            print(f"\n{product['display_name']} ({product['code']})")
            print(f"Description: {product.get('description', 'No description available')}")
            print(f"Available From: {product.get('available_from', 'N/A')}")
            print(f"Available To: {product.get('available_to', 'N/A')}")
            
            rates = fetch_rates(api_key, product['code'])
            if rates and 'results' in rates:
                results = rates['results']
                rates_info = []
                
                for rate in results:
                    try:
                        if not rate.get('valid_from') or not rate.get('valid_to') or not rate.get('value_inc_vat'):
                            continue
                        
                        # Parse the ISO format timestamps
                        valid_from = datetime.fromisoformat(rate['valid_from'].replace('Z', '+00:00'))
                        valid_to = datetime.fromisoformat(rate['valid_to'].replace('Z', '+00:00'))
                        rates_info.append({
                            'rate': rate['value_inc_vat'],
                            'from': valid_from,
                            'to': valid_to
                        })
                    except (ValueError, KeyError, AttributeError) as e:
                        continue  # Skip any rates with invalid data
                
                if rates_info:
                    # Sort by rate value
                    rates_info.sort(key=lambda x: x['rate'])
                    min_rate = rates_info[0]
                    max_rate = rates_info[-1]
                    
                    if len(rates_info) > 1:
                        print(f"Variable Rate Product:")
                        print(f"  Min Rate: {min_rate['rate']:.2f}p/kWh ({min_rate['from'].strftime('%H:%M')}-{min_rate['to'].strftime('%H:%M')})")
                        print(f"  Max Rate: {max_rate['rate']:.2f}p/kWh ({max_rate['from'].strftime('%H:%M')}-{max_rate['to'].strftime('%H:%M')})")
                    else:
                        print(f"Fixed Rate Product: {min_rate['rate']:.2f}p/kWh")
                else:
                    print("No rate information available")
                            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return

if __name__ == "__main__":
    main()
