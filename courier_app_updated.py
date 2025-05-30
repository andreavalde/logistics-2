import streamlit as st
import requests
from datetime import datetime
import pytz
import time
import folium
from streamlit_folium import folium_static
import pandas as pd

# Set page config for a cleaner appearance
st.set_page_config(
    page_title="Courier Delivery Assistant",
    page_icon="🚚",
    layout="wide"
)

# API keys
OPENWEATHER_API_KEY = "bc76588823fc2b0ff58485ed9196da3c"
NEWS_API_KEY = "0d9c613f7217408782b7b6e6d9ec6dc5"
TOMTOM_API_KEY = "YHWXtARIBmfkKlifwJzG7A6398aSzT3s"  # Updated with your actual TomTom API key

# App title and description with styling
st.title("🚚 Courier Delivery Assistant")
st.markdown("""
    <style>
    .reportview-container .markdown-text-container {
        font-family: monospace;
    }
    .stApp {
        background-color: #f5f7fa;
    }
    .element-container:has(div[data-testid="stException"]) {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)
st.write("Get real-time route intelligence, traffic updates, and delivery information for your journeys.")

# Create tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["Route Planning", "Zone Information", "Resources"])

with tab1:
    st.header("Route Planning")
    
    # Location inputs
    col1, col2 = st.columns(2)
    with col1:
        current_location = st.text_input("Current Location:", "Barcelona City Center")
        st.checkbox("Use my current location", key="use_current_location")
    with col2:
        destination = st.text_input("Delivery Destination:", "Barcelona Airport")
    
    # Vehicle type
    vehicle_type = st.selectbox(
        "Vehicle Type:",
        options=["Standard Car/Van", "Electric Vehicle", "Truck", "Bicycle/Motorcycle"]
    )
    
    # Function to geocode addresses using TomTom Search API
    def geocode_address(address):
        url = f"https://api.tomtom.com/search/2/geocode/{address}.json?key={TOMTOM_API_KEY}"
        try:
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200 and data.get("results") and len(data["results"]) > 0:
                # Extract coordinates from the first result
                result = data["results"][0]
                position = result["position"]
                return position["lat"], position["lon"]
            else:
                st.error(f"Could not geocode address: {address}")
                # Default to central Barcelona
                return 41.3851, 2.1734
        except Exception as e:
            st.error(f"Error geocoding address: {str(e)}")
            return 41.3851, 2.1734
    
    # Function to get route and traffic data using TomTom Routing API
    def get_route_with_traffic(start_lat, start_lon, end_lat, end_lon, vehicle_type):
        # Map vehicle type to TomTom API vehicle parameter
        vehicle_map = {
            "Standard Car/Van": "car",
            "Electric Vehicle": "car",
            "Truck": "truck",
            "Bicycle/Motorcycle": "motorcycle"
        }
        vehicle = vehicle_map.get(vehicle_type, "car")
        
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{start_lat},{start_lon}:{end_lat},{end_lon}/json?key={TOMTOM_API_KEY}&traffic=true&vehicleHeading=90&vehicle={vehicle}"
        try:
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200 and data.get("routes") and len(data["routes"]) > 0:
                route_data = data["routes"][0]
                summary = route_data["summary"]
                
                # Extract route information 
                route = {
                    "distance": round(summary["lengthInMeters"] / 1000, 1),  # Convert to km
                    "duration": round(summary["travelTimeInSeconds"] / 60),  # Convert to minutes
                    "traffic_delay": round(summary.get("trafficDelayInSeconds", 0) / 60),  # Additional minutes due to traffic
                    "points": []
                }
                
                # Extract route points for drawing on map
                legs = route_data.get("legs", [])
                for leg in legs:
                    points = leg.get("points", [])
                    route["points"].extend([[point["latitude"], point["longitude"]] for point in points])
                
                # Get traffic incidents along the route
                traffic_incidents = []
                # Check if there are incidents reported
                if "guidance" in route_data and "instructions" in route_data["guidance"]:
                    for instruction in route_data["guidance"]["instructions"]:
                        if "incident" in instruction.get("message", "").lower():
                            incident = {
                                "type": "INCIDENT",
                                "description": instruction["message"],
                                "location": f"Near {instruction.get('roadNumbers', [''])[0] if instruction.get('roadNumbers') else ''}",
                                "delay": f"{round(instruction.get('timeToArrival', 0) / 60)} minutes",
                                "severity": "medium",
                                "coordinates": [instruction["point"]["latitude"], instruction["point"]["longitude"]]
                            }
                            traffic_incidents.append(incident)
                
                # If no incidents found in the guidance, create default traffic incident based on delay
                if not traffic_incidents and route["traffic_delay"] > 0:
                    # Choose a point roughly 1/3 along the route for the incident
                    incident_point_index = len(route["points"]) // 3
                    incident_point = route["points"][incident_point_index] if incident_point_index < len(route["points"]) else route["points"][0]
                    
                    traffic_incidents.append({
                        "type": "CONGESTION",
                        "description": "Heavy traffic detected",
                        "location": "Along route",
                        "delay": f"{route['traffic_delay']} minutes",
                        "severity": "medium" if route["traffic_delay"] > 5 else "low",
                        "coordinates": incident_point
                    })
                
                return route, traffic_incidents
            else:
                st.error(f"Error calculating route: {data.get('detailedError', {}).get('message', 'Unknown error')}")
                # Return dummy data for demonstration
                return {
                    "distance": 15.7,
                    "duration": 25,
                    "traffic_delay": 5,
                    "points": [
                        [start_lat, start_lon],
                        [end_lat, end_lon]
                    ]
                }, []
        except Exception as e:
            st.error(f"Error getting route: {str(e)}")
            # Return dummy data for demonstration
            return {
                "distance": 15.7,
                "duration": 25,
                "traffic_delay": 5,
                "points": [
                    [start_lat, start_lon],
                    [end_lat, end_lon]
                ]
            }, []
    
    # Function to find resources (fuel/charging) using TomTom Search API with categories
    def find_resources(center_lat, center_lon, resource_type, radius=5000):
        # Map resource type to TomTom category ID
        category = "7311" if resource_type == "fuel" else "7309"  # 7311 for petrol stations, 7309 for EV charging
        
        url = f"https://api.tomtom.com/search/2/poiSearch/{resource_type}.json?key={TOMTOM_API_KEY}&lat={center_lat}&lon={center_lon}&radius={radius}&categorySet={category}"
        try:
            response = requests.get(url)
            data = response.json()
            
            resources = []
            if response.status_code == 200 and data.get("results"):
                for result in data["results"][:5]:  # Limit to top 5 results
                    poi = result["poi"]
                    address = result.get("address", {})
                    position = result["position"]
                    
                    resource = {
                        "name": poi.get("name", "Unknown"),
                        "location": [position.get("lat"), position.get("lon")],
                        "distance": f"{round(result.get('dist', 0) / 1000, 1)} km from route"
                    }
                    
                    # Add resource-specific details
                    if resource_type == "fuel":
                        resource["price"] = "€1.45/L"  # Placeholder as TomTom doesn't provide pricing
                    else:  # EV charging
                        resource["power"] = f"{poi.get('classifications', [{}])[0].get('code', '50')} kW"
                        resource["available"] = "Yes"  # Placeholder as TomTom doesn't provide availability
                    
                    resources.append(resource)
            
            # If no results found, provide dummy data
            if not resources:
                if resource_type == "fuel":
                    resources = [
                        {"name": "Shell Station", "location": [center_lat + 0.01, center_lon + 0.01], "price": "€1.45/L", "distance": "0.5 km from route"},
                        {"name": "BP Gas", "location": [center_lat - 0.01, center_lon - 0.01], "price": "€1.42/L", "distance": "0.3 km from route"},
                    ]
                else:  # EV charging
                    resources = [
                        {"name": "Fast Charger Station", "location": [center_lat + 0.01, center_lon + 0.01], "power": "150 kW", "available": "Yes", "distance": "0.5 km from route"},
                        {"name": "Mall Parking Charger", "location": [center_lat - 0.01, center_lon - 0.01], "power": "50 kW", "available": "Yes", "distance": "0.3 km from route"},
                    ]
            
            return resources
        except Exception as e:
            st.error(f"Error finding resources: {str(e)}")
            # Return dummy data for demonstration
            if resource_type == "fuel":
                return [
                    {"name": "Shell Station", "location": [center_lat + 0.01, center_lon + 0.01], "price": "€1.45/L", "distance": "0.5 km from route"},
                    {"name": "BP Gas", "location": [center_lat - 0.01, center_lon - 0.01], "price": "€1.42/L", "distance": "0.3 km from route"},
                ]
            else:  # EV charging
                return [
                    {"name": "Fast Charger Station", "location": [center_lat + 0.01, center_lon + 0.01], "power": "150 kW", "available": "Yes", "distance": "0.5 km from route"},
                    {"name": "Mall Parking Charger", "location": [center_lat - 0.01, center_lon - 0.01], "power": "50 kW", "available": "Yes", "distance": "0.3 km from route"},
                ]
    
    # Function to find parking using TomTom Search API
    def find_parking(destination_lat, destination_lon, radius=1000):
        url = f"https://api.tomtom.com/search/2/poiSearch/parking.json?key={TOMTOM_API_KEY}&lat={destination_lat}&lon={destination_lon}&radius={radius}&categorySet=7600"  # 7600 is the category code for parking
        try:
            response = requests.get(url)
            data = response.json()
            
            parking = []
            if response.status_code == 200 and data.get("results"):
                for result in data["results"][:5]:  # Limit to top 5 results
                    poi = result["poi"]
                    position = result["position"]
                    
                    parking_spot = {
                        "name": poi.get("name", "Street Parking"),
                        "location": [position.get("lat"), position.get("lon")],
                        "available": "Multiple spots",  # Placeholder as TomTom doesn't provide real-time availability
                        "cost": "€3.00/hour"  # Placeholder as TomTom doesn't provide pricing
                    }
                    
                    parking.append(parking_spot)
            
            # If no results found, provide dummy data
            if not parking:
                parking = [
                    {"name": "Street Parking", "location": [destination_lat + 0.001, destination_lon + 0.001], "available": "3 spots", "cost": "€2.50/hour"},
                    {"name": "Public Garage", "location": [destination_lat - 0.001, destination_lon - 0.001], "available": "Multiple spots", "cost": "€3.00/hour"}
                ]
            
            return parking
        except Exception as e:
            st.error(f"Error finding parking: {str(e)}")
            # Return dummy data for demonstration
            return [
                {"name": "Street Parking", "location": [destination_lat + 0.001, destination_lon + 0.001], "available": "3 spots", "cost": "€2.50/hour"},
                {"name": "Public Garage", "location": [destination_lat - 0.001, destination_lon - 0.001], "available": "Multiple spots", "cost": "€3.00/hour"}
            ]
    
    if st.button("Plan Route", key="plan_route_btn", type="primary"):
        with st.spinner("Calculating optimal route..."):
            # Geocode the addresses
            start_lat, start_lon = geocode_address(current_location)
            end_lat, end_lon = geocode_address(destination)
            
            # Get route data and traffic incidents in one call
            route_data, traffic_incidents = get_route_with_traffic(start_lat, start_lon, end_lat, end_lon, vehicle_type)
            
            # Create a map
            m = folium.Map(location=[(start_lat + end_lat)/2, (start_lon + end_lon)/2], zoom_start=12)
            
            # Add markers for start and end
            folium.Marker([start_lat, start_lon], popup=current_location, icon=folium.Icon(color="green")).add_to(m)
            folium.Marker([end_lat, end_lon], popup=destination, icon=folium.Icon(color="red")).add_to(m)
            
            # Add the route line
            folium.PolyLine(route_data["points"], color="blue", weight=5, opacity=0.7).add_to(m)
            
            # Add traffic incidents
            for incident in traffic_incidents:
                icon_color = "red" if incident["type"] == "ACCIDENT" else "orange"
                folium.Marker(
                    incident["coordinates"], 
                    popup=f"{incident['type']}: {incident['description']} - Delay: {incident['delay']}", 
                    icon=folium.Icon(color=icon_color, icon="warning-sign")
                ).add_to(m)
            
            # Display the map
            st.subheader("Route Map")
            folium_static(m)
            
            # Display route summary with ETA
            st.subheader("Route Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Distance", f"{route_data['distance']} km")
            with col2:
                st.metric("ETA without traffic", f"{route_data['duration']} min")
            with col3:
                total_travel_time = route_data['duration'] + route_data['traffic_delay']
                st.metric("ETA with traffic", f"{total_travel_time} min", delta=f"+{route_data['traffic_delay']}")
            
            # Calculate actual arrival time
            now = datetime.now()
            arrival_time = now + pd.Timedelta(minutes=total_travel_time)
            st.info(f"📍 Estimated arrival at destination: {arrival_time.strftime('%H:%M')}")
            
            # Display traffic incidents
            if traffic_incidents:
                st.subheader("Traffic Alerts")
                for incident in traffic_incidents:
                    severity_color = "red" if incident["severity"] == "high" else "orange" if incident["severity"] == "medium" else "blue"
                    st.markdown(f"<div style='padding: 10px; border-left: 5px solid {severity_color}; background-color: #f0f0f0;'><b>{incident['type']}</b>: {incident['description']} at {incident['location']} - Expected delay: {incident['delay']}</div>", unsafe_allow_html=True)
            else:
                st.success("No traffic incidents reported on your route.")
            
            # Find resources based on vehicle type
            st.subheader("Nearby Resources")
            # Use the midpoint of the route to find resources
            mid_point_lat = (start_lat + end_lat) / 2
            mid_point_lon = (start_lon + end_lon) / 2
            
            if vehicle_type == "Electric Vehicle":
                resources = find_resources(mid_point_lat, mid_point_lon, "charging")
                if resources:
                    st.write("🔌 EV Charging Stations along your route:")
                    for resource in resources:
                        st.write(f"- {resource['name']} ({resource['power']}) - {resource['distance']} - Available: {resource['available']}")
            else:
                resources = find_resources(mid_point_lat, mid_point_lon, "fuel")
                if resources:
                    st.write("⛽ Fuel Stations along your route:")
                    for resource in resources:
                        st.write(f"- {resource['name']} ({resource['price']}) - {resource['distance']}")
            
            # Find parking
            parking_options = find_parking(end_lat, end_lon)
            st.write("🅿️ Parking options near your destination:")
            for option in parking_options:
                st.write(f"- {option['name']} - Available: {option['available']} - Cost: {option['cost']}")

with tab2:
    st.header("Zone Information")
    
    # User inputs
    col1, col2 = st.columns(2)
    with col1:
        zone_location = st.text_input("City or postal code:", "Barcelona", key="zone_location")
    with col2:
        country = st.selectbox(
            "Country:",
            options=["es", "us", "gb", "fr", "de", "it"],
            format_func=lambda x: {
                "es": "Spain", "us": "United States", "gb": "United Kingdom",
                "fr": "France", "de": "Germany", "it": "Italy"
            }.get(x, x.upper()),
            key="zone_country"
        )
    
    # Timezone mapping
    city_timezone = {
        "new york": "America/New_York",
        "barcelona": "Europe/Madrid",
        "madrid": "Europe/Madrid",
        "london": "Europe/London",
        "paris": "Europe/Paris",
        "rome": "Europe/Rome",
        "berlin": "Europe/Berlin",
    }
    
    def get_local_time(city):
        tz_name = city_timezone.get(city.lower(), "UTC")
        local_tz = pytz.timezone(tz_name)
        return datetime.now(local_tz).strftime("%H:%M")
    
    def get_weather(city):
        api_key = OPENWEATHER_API_KEY.strip()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        try:
            for attempt in range(2):
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    weather = data["weather"][0]["description"].capitalize()
                    temp = data["main"]["temp"]
                    return True, (f"{temp}°C, {weather}", temp)
                elif response.status_code == 401:
                    return False, ("API key error. Please check your OpenWeatherMap API key.", None)
                elif response.status_code == 404:
                    return False, (f"City '{city}' not found. Please check spelling.", None)
                time.sleep(1)
            return False, (f"Weather API error (Status: {response.status_code})", None)
        except requests.exceptions.RequestException as e:
            return False, (f"Network error while fetching weather data: {str(e)}", None)
    
    def get_news(country_code, city):
        api_key = NEWS_API_KEY.strip()
        url = f"https://newsapi.org/v2/top-headlines?country={country_code}&q={city}&apiKey={api_key}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                if not articles:
                    fallback_url = f"https://newsapi.org/v2/top-headlines?country={country_code}&category=general&apiKey={api_key}"
                    response = requests.get(fallback_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        articles = data.get("articles", [])
                relevant_keywords = ["traffic", "road", "accident", "protest", "event", "closure", "strike", "demonstration"]
                filtered_articles = [
                    article for article in articles[:10]
                    if any(keyword in article.get("title", "").lower() for keyword in relevant_keywords)
                ]
                display_articles = filtered_articles[:3] if filtered_articles else articles[:3]
                headlines = [article.get("title") for article in display_articles]
                return True, headlines if headlines else ["No significant news affecting deliveries at this time"]
            elif response.status_code == 401:
                return False, ["API key error. Please check your NewsAPI key."]
            else:
                return False, [f"News API error (Status: {response.status_code})"]
        except requests.exceptions.RequestException as e:
            return False, [f"Network error while fetching news data: {str(e)}"]
    
    def estimate_delivery_load(location):
        now = datetime.now().hour
        city_patterns = {
            "barcelona": {"morning_peak": (9, 11), "lunch_peak": (12, 15), "evening_peak": (18, 21)},
            "madrid": {"morning_peak": (8, 11), "lunch_peak": (13, 16), "evening_peak": (19, 22)},
        }
        default_pattern = {"morning_peak": (8, 11), "lunch_peak": (12, 15), "evening_peak": (18, 21)}
        pattern = city_patterns.get(location.lower(), default_pattern)
        if pattern["lunch_peak"][0] <= now <= pattern["lunch_peak"][1]:
            return "High", f"{10 + now - pattern['lunch_peak'][0]} deliveries scheduled between {pattern['lunch_peak'][0]} - {pattern['lunch_peak'][1]} PM"
        elif pattern["evening_peak"][0] <= now <= pattern["evening_peak"][1]:
            return "Medium", f"5-10 deliveries scheduled between {pattern['evening_peak'][0]-12} - {pattern['evening_peak'][1]-12} PM"
        elif pattern["morning_peak"][0] <= now <= pattern["morning_peak"][1]:
            return "Medium", f"5-8 deliveries scheduled between {pattern['morning_peak'][0]} - {pattern['morning_peak'][1]} AM"
        else:
            return "Low", "Less than 5 deliveries expected in the next hour"
    
    def provide_safety_tips(temp_value):
        if temp_value is None:
            return
        st.markdown("### 🛡️ Safety Tips")
        if temp_value > 30:
            st.warning("• High temperature. Stay hydrated and avoid prolonged sun exposure.")
        elif temp_value < 5:
            st.warning("• Cold temperature. Wear appropriate clothing and watch for ice.")
        else:
            st.success("• No specific weather-related safety concerns. Proceed normally.")
    
    if st.button("Generate Zone Briefing", key="generate_zone_btn"):
        with st.spinner("Generating briefing..."):
            weather_success, (weather_data, temp_val) = get_weather(zone_location)
            news_success, news_data = get_news(country, zone_location)
            load_level, load_details = estimate_delivery_load(zone_location)
    
            st.subheader(f"Zone: {zone_location.title()}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("### 🌤️ Weather")
                st.info(weather_data)
            with col2:
                st.markdown("### 📦 Delivery Load")
                if load_level == "High":
                    st.error(f"*{load_level}*\n{load_details}")
                elif load_level == "Medium":
                    st.warning(f"*{load_level}*\n{load_details}")
                else:
                    st.success(f"*{load_level}*\n{load_details}")
            with col3:
                st.markdown("### ⏰ Current Time")
                st.info(f"{get_local_time(zone_location)} local time")
    
            st.markdown("### 📰 Local News")
            if news_success:
                for i, headline in enumerate(news_data):
                    st.write(f"{i+1}. {headline}")
            else:
                st.error(news_data[0])
    
            provide_safety_tips(temp_val)

with tab3:
    st.header("Resources Finder")
    
    col1, col2 = st.columns(2)
    with col1:
        resource_location = st.text_input("Current Location:", "Barcelona City Center", key="resource_location")
    with col2:
        resource_type = st.selectbox(
            "Resource Type:",
            options=["Fuel Stations", "EV Charging", "Parking", "Rest Areas"]
        )
    
    search_radius = st.slider("Search Radius (km)", 1, 20, 5)
    
    def find_resources_nearby(location, resource_type, radius_km):
        # First geocode the location
        try:
            lat, lon = geocode_address(location)
            
            # Map resource type to TomTom category
            category_map = {
                "Fuel Stations": "7311",  # Petrol/gas stations
                "EV Charging": "7309",    # EV charging stations
                "Parking": "7600",        # Parking
                "Rest Areas": "7897"      # Rest areas
            }
            
            category = category_map.get(resource_type, "7311")
            radius_meters = radius_km * 1000
            
            # Call TomTom POI API
            url = f"https://api.tomtom.com/search/2/poiSearch/{resource_type}.json?key={TOMTOM_API_KEY}&lat={lat}&lon={lon}&radius={radius_meters}&categorySet={category}"
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200 and data.get("results"):
                results = data["results"]
                resource_locations = []
                resource_data = {"Name": [], "Distance": [], "Address": []}
                
                # Add resource-specific data columns
                if resource_type == "Fuel Stations":
                    resource_data["Price"] = []
                    resource_data["Amenities"] = []
                elif resource_type == "EV Charging":
                    resource_data["Power"] = []
                    resource_data["Available"] = []
                elif resource_type == "Parking":
                    resource_data["Available"] = []
                    resource_data["Cost"] = []
                else:  # Rest Areas
                    resource_data["Facilities"] = []
                    resource_data["Hours"] = []
                
                for result in results[:10]:  # Limit to top 10 results
                    poi = result["poi"]
                    position = result["position"]
                    address = result.get("address", {})
                    
                    # Add common data
                    resource_data["Name"].append(poi.get("name", "Unknown"))
                    resource_data["Distance"].append(f"{round(result.get('dist', 0) / 1000, 1)} km")
                    resource_data["Address"].append(address.get("freeformAddress", "Address unknown"))
                    
                    # Add type-specific data (simulated since TomTom doesn't provide all of this)
                    if resource_type == "Fuel Stations":
                        resource_data["Price"].append("€1.45/L")  # Placeholder
                        resource_data["Amenities"].append("Shop, Air" if "shop" in poi.get("name", "").lower() else "Basic")
                    elif resource_type == "EV Charging":
                        resource_data["Power"].append(f"{50} kW")  # Placeholder
                        resource_data["Available"].append("Yes")  # Placeholder
                    elif resource_type == "Parking":
                        resource_data["Available"].append("Multiple spots")  # Placeholder
                        resource_data["Cost"].append("€3.00/hour")  # Placeholder
                    else:  # Rest Areas
                        resource_data["Facilities"].append("Food, WC" if "service" in poi.get("name", "").lower() else "WC")
                        resource_data["Hours"].append("24h")  # Placeholder
                    
                    # Store location for map
                    resource_locations.append([position["lat"], position["lon"]])
                
                return resource_data, resource_locations, lat, lon
            else:
                st.error(f"Error finding {resource_type}: {data.get('detailedError', {}).get('message', 'No results found')}")
                return None, None, lat, lon
        
        except Exception as e:
            st.error(f"Error processing request: {str(e)}")
            return None, None, 41.3851, 2.1734  # Default to Barcelona center
    
    if st.button("Find Resources", key="find_resources_btn"):
        with st.spinner(f"Searching for {resource_type} within {search_radius} km of {resource_location}..."):
            data, locations, center_lat, center