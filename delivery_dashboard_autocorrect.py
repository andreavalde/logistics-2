
import streamlit as st
import difflib
import requests

# ------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ------------------------------
st.set_page_config(page_title="📦 Delivery Dashboard with Auto-Correction", layout="wide")
st.title("📦 Delivery Driver Dashboard")

# ------------------------------
# LISTA LOCAL DE CIUDADES COMUNES
# ------------------------------
COMMON_CITIES = [
    "Barcelona", "Madrid", "Valencia", "Sevilla", "Zaragoza", "Málaga", "Murcia",
    "Palma", "Bilbao", "Alicante", "Córdoba", "Valladolid", "Vigo", "Gijón",
    "Granada", "A Coruña", "Santander", "Oviedo", "Pamplona", "Logroño"
]

# ------------------------------
# OPCIONAL: CARGAR CIUDADES DESDE GITHUB (DESACTIVADO POR DEFECTO)
# ------------------------------
# @st.cache_data
# def load_city_list_from_github():
#     url = "https://raw.githubusercontent.com/tuusuario/turepo/main/cities.txt"
#     response = requests.get(url)
#     return [line.strip() for line in response.text.splitlines() if line.strip()]
# COMMON_CITIES = load_city_list_from_github()

# ------------------------------
# FUNCIÓN DE AUTOCORRECCIÓN
# ------------------------------
def autocorrect_city(input_city, city_list):
    """Devuelve la ciudad más cercana si hay errores de escritura."""
    matches = difflib.get_close_matches(input_city, city_list, n=1, cutoff=0.6)
    return matches[0] if matches else input_city

# ------------------------------
# ENTRADA DEL USUARIO
# ------------------------------
st.header("📍 Route Information")

input_city = st.text_input("Enter City Name", "")

if input_city:
    # Autocorrección
    corrected_city = autocorrect_city(input_city.strip().title(), COMMON_CITIES)

    # Mostrar sugerencia si hay corrección
    if corrected_city != input_city.strip().title():
        st.info(f"Did you mean **{corrected_city}**? Using corrected name.")

    city = corrected_city

    # Simulación de carga de datos
    st.success(f"Weather and news will be shown for: **{city}**")

    # Aquí puedes llamar a tus funciones reales:
    # get_weather(city, api_key)
    # get_news(city)
    # etc.

else:
    st.info("Please enter a city to continue.")

# ------------------------------
# FOOTER
# ------------------------------
st.markdown("---")
st.caption("Built with ❤️ using Streamlit")
