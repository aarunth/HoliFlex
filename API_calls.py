import requests

def fetch_tariffs(api_key):
    url = "https://api.octopus.energy/v1/products/"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

def fetch_tariff_details(api_key, href):
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(href, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch tariff details from {href}. Status code: {response.status_code}")
        return None

# Example usage
api_key = "sk_live_a1smd0EbeoaVtA1IThcVZM8O"
tariffs = fetch_tariffs(api_key)

if tariffs:
    for product in tariffs['results']:
        tariff_name = product['display_name']
        href = None
        
        # Find the link to the tariff details
        for link in product.get('links', []):
            if 'href' in link:
                href = link['href']
                break
        
        if href:
            # Fetch details for this tariff
            details = fetch_tariff_details(api_key, href)
            if details and 'sample_consumption' in details:
                sample_consumption = details['sample_consumption']
                dual_rate = sample_consumption.get('electricity_dual_rate', {})
                electricity_day = dual_rate.get('electricity_day')
                electricity_night = dual_rate.get('electricity_night')
                
                if electricity_day and electricity_night:
                    print(f"Tariff: {tariff_name}")
                    print(f"  Electricity Day Rate: {electricity_day}")
                    print(f"  Electricity Night Rate: {electricity_night}")
                else:
                    print(f"  Tariff: {tariff_name} does not have dual-rate information.")
