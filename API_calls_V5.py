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
                    all_rates = {'results': []}
                    
                    # Try all tariff codes
                    for tariff_code, tariff_details in tariffs.items():
                        # Get all available payment methods
                        payment_methods = [key for key in tariff_details.keys() if isinstance(tariff_details[key], dict)]
                        
                        for payment_method in payment_methods:
                            payment_details = tariff_details[payment_method]
                            
                            # First try to get rates from standard_unit_rates URL
                            for link in payment_details.get('links', []):
                                if link.get('rel') == 'standard_unit_rates':
                                    rates_url = link['href']
                                    rates_response = requests.get(rates_url, headers=headers)
                                    
                                    if rates_response.status_code == 200:
                                        rates_data = rates_response.json()
                                        if 'results' in rates_data and rates_data['results']:
                                            # Add payment method to each rate
                                            for rate in rates_data['results']:
                                                rate['payment_method'] = payment_method
                                            all_rates['results'].extend(rates_data['results'])
                            
                            # If no rates from URL, use the standard unit rate
                            if 'standard_unit_rate_inc_vat' in payment_details:
                                rate = payment_details['standard_unit_rate_inc_vat']
                                now = datetime.now(timezone.utc)
                                all_rates['results'].append({
                                    'value_inc_vat': rate,
                                    'valid_from': now.isoformat(),
                                    'valid_to': (now + timedelta(days=1)).isoformat(),
                                    'payment_method': payment_method
                                })
                    
                    if all_rates['results']:
                        # Sort all results by valid_from to get latest rates
                        all_rates['results'].sort(key=lambda x: x.get('valid_from', ''), reverse=True)
                        return all_rates
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
                            'to': valid_to,
                            'payment_method': rate.get('payment_method', 'unknown')
                        })
                    except (ValueError, KeyError, AttributeError) as e:
                        continue  # Skip any rates with invalid data
                
                if rates_info:
                    # Sort by valid_from time
                    rates_info.sort(key=lambda x: x['from'], reverse=True)
                    
                    # Get the latest date
                    if rates_info:
                        latest_date = rates_info[0]['from'].date()
                        
                        # Filter rates for only the latest date
                        latest_rates = [rate for rate in rates_info if rate['from'].date() == latest_date]
                        
                        # Sort by time within the latest date
                        latest_rates.sort(key=lambda x: x['from'])
                        
                        print(f"Rates for {latest_date.strftime('%Y-%m-%d')}:")
                        for rate in latest_rates:
                            print(f"  Rate: {rate['rate']:.2f}p/kWh ({rate['payment_method']}) ({rate['from'].strftime('%H:%M')}-{rate['to'].strftime('%H:%M')})")
                else:
                    # Try to get standard unit rate
                    product_details = fetch_product_details(api_key, product['code'])
                    if product_details and 'single_register_electricity_tariffs' in product_details:
                        tariffs = product_details['single_register_electricity_tariffs']
                        rate_found = False
                        for tariff_code, tariff_details in tariffs.items():
                            # Get all available payment methods
                            payment_methods = [key for key in tariff_details.keys() if isinstance(tariff_details[key], dict)]
                            
                            for payment_method in payment_methods:
                                payment_details = tariff_details[payment_method]
                                if 'standard_unit_rate_inc_vat' in payment_details:
                                    rate = payment_details['standard_unit_rate_inc_vat']
                                    now = datetime.now(timezone.utc)
                                    print(f"Standard Unit Rate ({payment_method}): {rate:.2f}p/kWh (Valid from: {now.strftime('%Y-%m-%d %H:%M')})")
                                    rate_found = True
                                    break
                            if rate_found:
                                break
                        if not rate_found:
                            print("No rate information available")
                            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return

if __name__ == "__main__":
    main()
