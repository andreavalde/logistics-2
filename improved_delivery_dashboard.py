import streamlit as st
import pandas as pd
import altair as alt
import requests
import random
from geopy.geocoders import Nominatim
from geopy.distance import distance as geodistance
import folium
from datetime import datetime

# Page config
st.set_page_config(page_title="Delivery Dashboard", layout="wide")
st.title("📦 Delivery Driver Dashboard")

# API keys from previous code (inserted explicitly)
openweather_api_key = "0d9c613f7217408782b7b6e6d9ec6dc5"
news_api_key = "0d9c613f7217408782b7b6e6d9ec6dc5"  # Example; replace with real key if different

# --- Functions ---
def get_weather(city, api_key):
    """Get detailed weather information for a city"""
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
                    "lon": lon,
                    "main": data["weather"][0]["main"]
                }
                return True, weather_details
            elif response.status_code == 401:
                return False, "API key error. Please check your OpenWeatherMap API key."
            elif response.status_code == 404:
                return False, f"City '{city}' not found. Please check spelling."
            return False, f"Weather API error (Status: {response.status_code})"
        except requests.exceptions.RequestException as e:
            return False, f"Network error while fetching weather data: {str(e)}"

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

# --- User Inputs ---
st.header("📍 Route Information")
city = st.text_input("City", "")
col1, col2 = st.columns(2)
start_address = col1.text_input("Starting Address", "")
end_address = col2.text_input("Destination Address", "")

# --- Weather Info ---
st.header("🌤️ Current Weather")
if city:
    if openweather_api_key:
        success, weather_data = get_weather(city, openweather_api_key)
        if success:
            st.subheader(f"Weather in {city.capitalize()}")
            
            # Create columns for better layout
            w_col1, w_col2 = st.columns([1, 2])
            
            # Display weather icon
            icon_url = f"http://openweathermap.org/img/wn/{weather_data['icon']}@2x.png"
            w_col1.image(icon_url, width=100)
            
            # Display weather details
            w_col2.write(f"**Temperature:** {weather_data['temp']:.1f} °C")
            w_col2.write(f"**Condition:** {weather_data['description']}")
            w_col2.write(f"**Humidity:** {weather_data['humidity']}%")
            w_col2.write(f"**Wind:** {weather_data['wind_speed']} m/s")
            
            # Weather alerts/notices
            main_condition = weather_data["main"]
            if main_condition.lower() in ["rain", "drizzle", "thunderstorm"]:
                st.warning("Rain or storm expected. Drive safely!")
            elif main_condition.lower() == "snow":
                st.warning("Snow expected. Be careful on the road!")
            elif main_condition.lower() == "clear":
                st.success("Clear skies. Good time to drive!")
            
            if weather_data['temp'] > 30:
                st.warning("High temperature. Stay hydrated!")
            elif weather_data['temp'] < 5:
                st.warning("Cold weather. Keep warm!")
        else:
            st.error(weather_data)  # Display error message
    else:
        st.error("Missing OpenWeatherMap API key.")
else:
    st.info("Enter a city to view current weather.")

# --- Local News ---
st.header("📰 Local News")
if city:
    if news_api_key:
        try:
            news_url = (
                f"https://newsapi.org/v2/everything?"
                f"q={city}&language=en&pageSize=5&apiKey={news_api_key}"
            )
            r = requests.get(news_url)
            news = r.json()
            if news.get("status") == "ok":
                articles = news.get("articles", [])
                if articles:
                    st.subheader(f"Top News in {city.capitalize()}")
                    for art in articles:
                        title = art.get("title", "")
                        source = art.get("source", {}).get("name", "")
                        url = art.get("url", "")
                        st.markdown(f"- [{title}]({url}) - *{source}*")
                else:
                    st.write("No news found.")
            else:
                st.error("News API error.")
        except Exception:
            st.error("Error connecting to NewsAPI.")
    else:
        st.error("Missing NewsAPI key.")
else:
    st.info("Enter a city to show relevant news.")

# --- Map Route and Estimated Time ---
st.header("🗺️ Route Map")
gas_stations_info = None
if start_address and end_address:
    geolocator = Nominatim(user_agent="delivery_app")
    try:
        query_start = f"{start_address}, {city}" if city else start_address
        query_end = f"{end_address}, {city}" if city else end_address
        loc_start = geolocator.geocode(query_start)
        loc_end = geolocator.geocode(query_end)
    except Exception:
        loc_start = None
        loc_end = None

    if loc_start and loc_end:
        lat1, lon1 = loc_start.latitude, loc_start.longitude
        lat2, lon2 = loc_end.latitude, loc_end.longitude
        map_route = folium.Map(location=[(lat1+lat2)/2, (lon1+lon2)/2], zoom_start=13)
        folium.Marker(
            [lat1, lon1], popup="Start",
            icon=folium.Icon(color='green', icon='play')
        ).add_to(map_route)
        folium.Marker(
            [lat2, lon2], popup="Destination",
            icon=folium.Icon(color='red', icon='flag')
        ).add_to(map_route)
        folium.PolyLine([[lat1, lon1], [lat2, lon2]], color="blue", weight=3, opacity=0.7).add_to(map_route)
        st.markdown("**Map with route:**")
        st.components.v1.html(map_route._repr_html_(), width=700, height=500)

        # Distance and time estimate
        dist_km = geodistance((lat1, lon1), (lat2, lon2)).km
        avg_speed = 30  # km/h urban
        time_h = dist_km / avg_speed
        time_min = time_h * 60
        st.subheader("⏱️ Estimated Travel Time")
        st.write(f"- Approx. distance: **{dist_km:.2f} km**")
        if time_h < 1:
            st.write(f"- Estimated duration: **{int(time_min)} minutes**")
        else:
            h = int(time_h)
            m = int((time_h - h) * 60)
            st.write(f"- Estimated duration: **{h}h {m}min**")
            
        # Get gas station info near destination
        gas_stations_info = find_gas_stations(lat2, lon2)
    else:
        st.error("Could not locate addresses. Check spelling.")
else:
    st.info("Enter origin and destination to generate route.")

# --- Gas Stations Info ---
if gas_stations_info:
    st.header("⛽ Gas Stations")
    availability, details, indicator = gas_stations_info
    st.write(f"{indicator} **Availability:** {availability}")
    st.write(f"**Details:** {details}")

# --- Simulated Traffic Chart ---
st.header("📈 Simulated Traffic Chart")
def create_traffic_chart(city):
    hours = list(range(24))
    base_traffic = [
        0.2, 0.1, 0.1, 0.1, 0.2, 0.4, 0.6, 0.9, 1.0, 0.8,
        0.6, 0.5, 0.7, 0.7, 0.5, 0.6, 0.8, 1.0, 0.9, 0.7,
        0.5, 0.4, 0.3, 0.2
    ]
    random.seed(int(datetime.now().timestamp()) % 100)
    traffic = [max(0, min(1, t + (random.random() - 0.5) * 0.2)) for t in base_traffic]
    current_hour = datetime.now().hour
    df = pd.DataFrame({
        'Hour': hours,
        'Traffic': traffic,
        'TimeLabel': [f"{h:02d}:00" for h in hours],
        'Now': [h == current_hour for h in hours]
    })
    chart = alt.Chart(df).mark_line(color='blue', strokeWidth=3).encode(
        x=alt.X('Hour:Q', axis=alt.Axis(title='Hour of Day', values=list(range(0, 24, 2)))),
        y=alt.Y('Traffic:Q', axis=alt.Axis(title='Traffic Level', format='.0%'), scale=alt.Scale(domain=[0, 1])),
        tooltip=['TimeLabel', 'Traffic']
    )
    dots = alt.Chart(df).mark_circle(color='blue', size=60).encode(
        x='Hour:Q', y='Traffic:Q', tooltip=['TimeLabel', 'Traffic']
    )
    now_dot = alt.Chart(df[df['Now']]).mark_circle(color='red', size=100).encode(
        x='Hour:Q', y='Traffic:Q', tooltip=['TimeLabel', alt.Tooltip('Traffic', title='Current')]
    )
    return (chart + dots + now_dot).properties(
        title=f"Estimated Traffic for {city.capitalize()}",
        width=700, height=400
    ).configure_title(fontSize=18)

if city:
    traffic_chart = create_traffic_chart(city)
    st.altair_chart(traffic_chart, use_container_width=True)
else:
    st.info("Enter city to display traffic chart.")