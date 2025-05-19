def get_traffic_analysis(city):
    """Generate a traffic analysis chart based on time of day"""
    import pandas as pd
    import altair as alt
    import random
    from datetime import datetime
    
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
    random.seed(int(datetime.now().timestamp()) % 100)
    traffic = [max(0, min(1, t + (random.random() - 0.5) * 0.2)) for t in traffic_base]
    
    # Get current hour
    current_hour = datetime.now().hour
    
    # Create data frame
    data = pd.DataFrame({
        'Hour': hours,
        'Traffic': traffic,
        'TimeOfDay': [f"{h:02d}:00" for h in hours],
        'Current': [h == current_hour for h in hours]
    })
    
    # Create chart using Altair - FIX: Domain specification
    chart = alt.Chart(data).mark_line(
        color='blue',
        strokeWidth=3
    ).encode(
        x=alt.X('Hour:Q', axis=alt.Axis(title='Hour of Day', labelAngle=0, values=list(range(0, 24, 2)))),
        y=alt.Y('Traffic:Q', axis=alt.Axis(title='Traffic Intensity', format='%'), scale=alt.Scale(domain=[0, 1])),
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