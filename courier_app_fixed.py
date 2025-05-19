import streamlit as st
import requests
from datetime import datetime, timedelta
import json
import pandas as pd
import pydeck as pdk
import time
import os
import numpy as np
import matplotlib.pyplot as plt
import altair as alt
from io import BytesIO

# Set page configuration
st.set_page_config(
    page_title="Courier Zone Briefing",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .info-box {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid #1E88E5;
    }
    .warning {
        border-left: 4px solid #FFC107;
    }
    .danger {
        border-left: 4px solid #F44336;
    }
    .success {
        border-left: 4px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Functions from original script
def get_weather(city, api_key):
    """Get weather information for a city"""
    with st.spinner(f"Fetching weather data for {city}..."):
        api_key = api_key.strip()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                weather = data["weather"][0]["description"].capitalize()
                temp = data["main"]["temp"]
                icon = data["weather"][0]["icon"]
                humidity = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"]
                
                # Get coordinates for map
                lat = data["coord"]["lat"]
                lon = data["coord"]["lon"]
                
                weather_details = {
                    "description": weather,
                    "temp": temp,
                    "icon": icon,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "lat": lat,
                    "lon": lon
                }
                
                return True, weather_details
            elif response.status_code == 401:
                return False, "API key error. Please check your OpenWeatherMap API key."
            elif response.status_code == 404:
                return False, f"City '{city}' not found. Please check spelling."
            
            return False, f"Weather API error (Status: {response.status_code})"
        
        except requests.exceptions.RequestException as e:
            return False, f"Network error while fetching weather data: {str(e)}"

def get_news(country_code, city, api_key):
    """Get news headlines for a location"""
    with st.spinner(f"Fetching local news for {city}, {country_code.upper()}..."):
        api_key = api_key.strip()
        
        # Format the city parameter correctly (spaces to +)
        formatted_city = city.replace(" ", "+")
        
        # Improved API call with better error handling
        url = f"https://newsapi.org/v2/top-headlines?country={country_code}&q={formatted_city}&apiKey={api_key}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                
                if not articles:
                    # Fallback to general news
                    url = f"https://newsapi.org/v2/top-headlines?country={country_code}&category=general&apiKey={api_key}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        articles = data.get("articles", [])
                    else:
                        st.warning("Failed to fetch fallback news. Using simulated data.")
                        # Provide simulated news when API fails
                        return True, get_simulated_news(city)
                
                relevant_articles = []
                for article in articles[:10]:
                    if article.get("title"):
                        title = article.get("title", "").lower()
                        if any(keyword in title for keyword in ["traffic", "road", "accident", "protest", "closure"]):
                            relevant_articles.append(article)
                
                display_articles = relevant_articles[:5] if relevant_articles else articles[:5]
                
                if display_articles:
                    news_items = []
                    for article in display_articles:
                        news_items.append({
                            "title": article.get("title", "No title available"),
                            "url": article.get("url", "#"),
                            "source": article.get("source", {}).get("name", "Unknown") if article.get("source") else "Unknown"
                        })
                    return True, news_items
                else:
                    return True, [{"title": "No significant news affecting deliveries at this time", "url": "#", "source": "System"}]
            
            elif response.status_code == 401:
                st.warning("API key error. Using simulated news data.")
                return True, get_simulated_news(city)
            elif response.status_code == 429:
                st.warning("Too many requests. Using simulated news data.")
                return True, get_simulated_news(city)
            else:
                # Fallback for any other error
                st.warning(f"Error fetching news (Status: {response.status_code}). Using simulated data.")
                return True, get_simulated_news(city)
        
        except Exception as e:
            st.warning(f"Error fetching news: {str(e)}. Using simulated data.")
            return True, get_simulated_news(city)

def get_simulated_news(city):
    """Generate simulated news when API fails"""
    return [
        {
            "title": f"Traffic delays reported on main avenue in {city} due to construction",
            "url": "#",
            "source": "Traffic Update"
        },
        {
            "title": f"New delivery routes established in {city} downtown area",
            "url": "#",
            "source": "Courier News"
        },
        {
            "title": f"Weather conditions affecting delivery times in {city} suburban areas",
            "url": "#",
            "source": "Weather Alert"
        },
        {
            "title": f"Local businesses report increased delivery demands in {city}",
            "url": "#",
            "source": "Business Times"
        }
    ]

def find_gas_stations(lat, lon):
    """Find gas stations near the specified location"""
    now = datetime.now().hour
    
    # Simple time-based patterns
    if 7 <= now <= 10:  # Morning commute
        return "High", f"5+ gas stations open within 3km radius", "🟢"
    elif 17 <= now <= 20:  # Evening commute
        return "Medium", f"3-4 gas stations open within 3km radius", "🟡"
    elif 22 <= now <= 6:  # Late night
        return "Low", f"Limited gas stations open for 24h service", "🔴"
    else:
        return "Medium", "Normal gas station operations in your area", "🟡"

def get_safety_tips(weather_data):
    """Generate safety tips based on weather conditions"""
    if not isinstance(weather_data, dict):
        return ["No specific weather-related safety concerns. Proceed normally."]
    
    tips = []
    temp = weather_data.get("temp", 20)
    description = weather_data.get("description", "").lower()
    
    if "rain" in description or "shower" in description:
        tips.append("Roads may be slippery. Maintain safe distance and reduce speed.")
    elif "snow" in description:
        tips.append("Snow conditions reported. Use winter equipment and drive cautiously.")
    elif "fog" in description:
        tips.append("Reduced visibility. Use fog lights and reduce speed.")
    elif "storm" in description or "thunder" in description:
        tips.append("Stormy conditions. Seek shelter if lightning intensifies.")
    
    if temp >= 30:
        tips.append("High temperature. Stay hydrated and avoid prolonged sun exposure.")
    elif temp <= 5:
        tips.append("Cold temperature. Wear appropriate clothing and watch for ice.")
        
    if not tips:
        tips.append("No specific weather-related safety concerns. Proceed normally.")
        
    return tips

def generate_map(lat, lon, zoom=12):
    """Generate an interactive 3D map for the location"""
    # Set the viewport location
    view_state = pdk.ViewState(
        longitude=lon,
        latitude=lat,
        zoom=zoom,
        min_zoom=5,
        max_zoom=15,
        pitch=40.5,
        bearing=-27.36
    )

    # Create layer for the center point
    center_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"position": [lon, lat], "color": [0, 0, 255], "radius": 100}],
        get_position="position",
        get_color="color",
        get_radius="radius",
        pickable=True
    )

    # Combined all of it and render a viewport
    r = pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=[center_layer],
        tooltip={"text": "Delivery Zone Center"},
    )
    
    return r

# New function to generate traffic analysis
def get_traffic_analysis(city):
    """Generate a traffic analysis chart based on time of day"""
    # Generate time points for a full day
    hours = list(range(24))
    
    # Define traffic patterns based on typical urban traffic
    # Morning rush (7-10), lunch (12-14), evening rush (16-19)
    traffic_base = [
        0.2, 0.1, 0.1, 0.1, 0.2, 0.4, 0.6, 0.9, 1.0, 0.8,  # 0-9
        0.6, 0.5, 0.7, 0.7, 0.5, 0.6, 0.8, 1.0, 0.9, 0.7,  # 10-19
        0.5, 0.4, 0.3, 0.2                                 # 20-23
    ]
    
    # Add some randomness
    np.random.seed(int(datetime.now().timestamp()) % 100)
    traffic = [max(0, min(1, t + (np.random.random() - 0.5) * 0.2)) for t in traffic_base]
    
    # Get current hour
    current_hour = datetime.now().hour
    
    # Create data frame
    data = pd.DataFrame({
        'Hour': hours,
        'Traffic': traffic,
        'TimeOfDay': [f"{h:02d}:00" for h in hours],
        'Current': [h == current_hour for h in hours]
    })
    
    # Create chart using Altair
    chart = alt.Chart(data).mark_line(
        color='blue',
        strokeWidth=3
    ).encode(
        x=alt.X('Hour:Q', axis=alt.Axis(title='Hour of Day', labelAngle=0, values=list(range(0, 24, 2)))),
        y=alt.Y('Traffic:Q', axis=alt.Axis(title='Traffic Intensity', format='%', domain=[0, 1])),
        tooltip=['TimeOfDay', 'Traffic']
    )
    
    # Add points
    points = alt.Chart(data).mark_circle(
        color='blue',
        size=100
    ).encode(
        x='Hour:Q',
        y='Traffic:Q',
        tooltip=['TimeOfDay', 'Traffic']
    )
    
    # Highlight current hour
    current_point = alt.Chart(data[data['Current']]).mark_circle(
        color='red',
        size=150
    ).encode(
        x='Hour:Q',
        y='Traffic:Q',
        tooltip=['TimeOfDay', alt.Tooltip('Traffic', title='Current Traffic')]
    )
    
    # Combine charts
    combined_chart = (chart + points + current_point).properties(
        title=f'Traffic Pattern Analysis for {city}',
        width=600,
        height=300
    ).configure_title(
        fontSize=20
    )
    
    return combined_chart, data

# Helper function to securely retrieve API keys
def get_api_keys():
    # Get API keys from environment variables first
    weather_key = os.getenv("OPENWEATHERMAP_API_KEY", "")
    news_key = os.getenv("NEWSAPI_API_KEY", "")
    
    # If not in environment, check for secrets in Streamlit
    if not weather_key:
        try:
            weather_key = st.secrets.get("OPENWEATHERMAP_API_KEY", "bc76588823fc2b0ff58485ed9196da3c")
        except:
            weather_key = "bc76588823fc2b0ff58485ed9196da3c"  # Fallback key
    
    if not news_key:
        try:
            news_key = st.secrets.get("NEWSAPI_API_KEY", "04b45dc5-16ea-4ae6-a879-1730368ef95b")
        except:
            news_key = "04b45dc5-16ea-4ae6-a879-1730368ef95b"  # Fallback key
    
    return weather_key, news_key

# Main app
def main():
    # Sidebar configuration
    st.sidebar.markdown("### 🚚 Configuration")
    
    # Get API keys securely (no UI indicators)
    weather_key, news_key = get_api_keys()
    
    # Location settings
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📍 Location")
    city = st.sidebar.text_input("City", value="Barcelona")
    country = st.sidebar.text_input("Country Code", value="es", max_chars=2)
    
    # Refresh interval
    st.sidebar.markdown("---")
    refresh_interval = st.sidebar.slider("Auto-refresh interval (minutes)", 0, 60, 15)
    
    # Show demo mode option
    st.sidebar.markdown("---")
    demo_mode = st.sidebar.checkbox("Use Demo Mode (simulated data)", value=False)
    
    # Main content
    st.markdown('<div class="main-header">🚚 COURIER ZONE BRIEFING</div>', unsafe_allow_html=True)
    
    # Current time
    current_time = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"<p style='text-align: center;'>Last updated: {current_time}</p>", unsafe_allow_html=True)
    
    # Initialize session state for auto-refresh
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
        st.session_state.refresh_counter = 0
    
    # Auto-refresh logic
    if refresh_interval > 0:
        time_since_refresh = (datetime.now() - st.session_state.last_refresh).total_seconds() / 60
        if time_since_refresh >= refresh_interval:
            st.session_state.last_refresh = datetime.now()
            st.session_state.refresh_counter += 1
            st.experimental_rerun()
        
        # Progress bar for next refresh
        progress = min(time_since_refresh / refresh_interval, 1.0)
        if progress < 1.0:
            st.progress(progress)
            next_refresh = refresh_interval - time_since_refresh
            st.caption(f"Next refresh in approximately {int(next_refresh)} minutes")
    
    # Generate data
    if demo_mode:
        # Use simulated data
        weather_success = True
        weather_data = {
            "description": "Partly cloudy",
            "temp": 22.5,
            "icon": "03d",
            "humidity": 65,
            "wind_speed": 3.5,
            "lat": 41.3851,
            "lon": 2.1734
        }
        news_success = True
        news_data = get_simulated_news(city)
    else:
        # Use real API data
        weather_success, weather_data = get_weather(city, weather_key)
        news_success, news_data = get_news(country, city, news_key)
    
    # Get gas station info instead of delivery load
    if weather_success and isinstance(weather_data, dict):
        stations_level, stations_details, stations_emoji = find_gas_stations(weather_data["lat"], weather_data["lon"])
    else:
        stations_level, stations_details, stations_emoji = "Unknown", "Weather data required to find nearby stations", "❓"
    
    # Create layout with columns
    col1, col2 = st.columns([2, 1])
    
    # Map in the first column
    with col1:
        st.markdown('<div class="section-header">📍 Zone Map</div>', unsafe_allow_html=True)
        
        if weather_success and isinstance(weather_data, dict):
            # Display interactive 3D map
            map_deck = generate_map(weather_data["lat"], weather_data["lon"])
            st.pydeck_chart(map_deck)
            
            # Display coordinates below map
            st.caption(f"Coordinates: {weather_data['lat']:.4f}, {weather_data['lon']:.4f}")
        else:
            st.error("Unable to load map: Weather data unavailable")
    
    # Stats in the second column
    with col2:
        # Weather section
        st.markdown('<div class="section-header">🌤️ Weather</div>', unsafe_allow_html=True)
        
        if weather_success and isinstance(weather_data, dict):
            weather_class = "info-box"
            if "rain" in weather_data["description"].lower() or "snow" in weather_data["description"].lower():
                weather_class += " warning"
            
            st.markdown(f"""
            <div class="{weather_class}">
                <h3>{weather_data["temp"]}°C, {weather_data["description"]}</h3>
                <p>Humidity: {weather_data["humidity"]}%</p>
                <p>Wind Speed: {weather_data["wind_speed"]} m/s</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(weather_data if isinstance(weather_data, str) else "Weather data unavailable")
        
        # Gas stations section (reemplazado de Delivery Load)
        st.markdown('<div class="section-header">⛽ Gas Stations Near Me</div>', unsafe_allow_html=True)
        
        stations_class = "info-box"
        if stations_level == "Low":
            stations_class += " danger"
        elif stations_level == "Medium":
            stations_class += " warning"
        else:
            stations_class += " success"
            
        st.markdown(f"""
        <div class="{stations_class}">
            <h3>{stations_emoji} {stations_level} Availability</h3>
            <p>{stations_details}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Traffic Analysis (new section)
    st.markdown('<div class="section-header">🚦 Traffic Analysis</div>', unsafe_allow_html=True)
    
    try:
        traffic_chart, traffic_data = get_traffic_analysis(city)
        
        # Display chart
        st.altair_chart(traffic_chart, use_container_width=True)
        
        # Get current traffic level
        current_hour = datetime.now().hour
        current_traffic = traffic_data[traffic_data['Hour'] == current_hour]['Traffic'].values[0]
        
        # Display current traffic status
        traffic_class = "info-box"
        if current_traffic > 0.7:
            traffic_class += " danger"
            traffic_status = "Heavy traffic"
            traffic_emoji = "🔴"
        elif current_traffic > 0.4:
            traffic_class += " warning"
            traffic_status = "Moderate traffic"
            traffic_emoji = "🟡"
        else:
            traffic_class += " success"
            traffic_status = "Light traffic"
            traffic_emoji = "🟢"
            
        st.markdown(f"""
        <div class="{traffic_class}">
            <h3>{traffic_emoji} Current Traffic Status: {traffic_status}</h3>
            <p>Traffic intensity: {current_traffic:.0%}</p>
            <p>Planning your routes accordingly is recommended.</p>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error generating traffic analysis: {str(e)}")
    
    # News section (full width)
    st.markdown('<div class="section-header">📰 Local News</div>', unsafe_allow_html=True)
    
    if news_success:
        for news_item in news_data:
            title = news_item.get("title", "")
            url = news_item.get("url", "#")
            source = news_item.get("source", "Unknown")
            
            st.markdown(f"""
            <div class="info-box">
                <h3>{title}</h3>
                <p>Source: {source}</p>
                <a href="{url}" target="_blank">Read more</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("News data unavailable")
    
    # Safety tips section
    st.markdown('<div class="section-header">🛡️ Safety Tips</div>', unsafe_allow_html=True)
    
    if weather_success:
        tips = get_safety_tips(weather_data)
        
        for tip in tips:
            tip_class = "info-box"
            if "caution" in tip.lower() or "reduce speed" in tip.lower():
                tip_class += " warning"
            elif "danger" in tip.lower() or "seek shelter" in tip.lower():
                tip_class += " danger"
                
            st.markdown(f"""
            <div class="{tip_class}">
                <p>• {tip}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Safety tips unavailable: Weather data not accessible")
    
    # Save data as JSON
    try:
        briefing_data = {
            "zone": city,
            "country": country,
            "timestamp": datetime.now().isoformat(),
            "weather": weather_data if weather_success else None,
            "news": news_data if news_success else None,
            "gas_stations": {
                "level": stations_level,
                "details": stations_details
            },
            "traffic": {
                "current_hour": datetime.now().hour,
                "status": traffic_status if 'traffic_status' in locals() else "Unknown",
                "intensity": float(current_traffic) if 'current_traffic' in locals() else 0.0
            }
        }
        
        if st.button("Save Briefing to JSON"):
            with open("last_briefing.json", "w") as f:
                json.dump(briefing_data, f, indent=2)
            st.success("Briefing data saved to 'last_briefing.json'")
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

# Asegurar que la aplicación se ejecuta
if __name__ == "__main__":
    main()